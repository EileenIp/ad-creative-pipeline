"""
Idempotent loader: lands every row from data/raw/drops/*.csv into a raw
DuckDB table, verbatim — duplicates, restatements and all. Deduplication and
correction-handling are the staging layer's job (dbt `stg_creative_performance`),
not this script's: the raw layer's contract is "preserves exactly what the
platform delivered," which is what makes the ground-truth manifest checkable
against it later.

Files that don't match either known schema (pre- or post-schema-drift) are
quarantined, not crashed on. Re-running is safe — a load log inside the
warehouse tracks which files have already been handled, loaded or
quarantined, and a filename already in the log is skipped.

Run: `python -m src.loader` from the project root.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from datetime import datetime, timezone

import duckdb
import pandas as pd

from src import config as cfg

PRE_DRIFT_COLUMNS = [
    "date", "campaign_id", "adset_id", "creative_id", "creative_format",
    "placement", "impressions", "clicks", "spend", "conversions",
]
POST_DRIFT_COLUMNS = [
    "date", "campaign_id", "adset_id", "creative_id", "creative_format",
    "placement", "impressions", "clicks", "cost", "conversions",
    "video_completion_rate",
]

CANONICAL_COLUMNS = [
    "date", "campaign_id", "adset_id", "creative_id", "creative_format",
    "placement", "impressions", "clicks", "spend", "conversions",
    "video_completion_rate",
]

DROP_FILE_RE = re.compile(r"drop_(\d{4}-\d{2}-\d{2})\.csv$")

RAW_SCHEMA = "raw"
RAW_TABLE = "creative_performance"
LOAD_LOG_TABLE = "_load_log"


def ensure_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{RAW_TABLE} (
            date DATE,
            campaign_id VARCHAR,
            adset_id VARCHAR,
            creative_id VARCHAR,
            creative_format VARCHAR,
            placement VARCHAR,
            impressions DOUBLE,
            clicks DOUBLE,
            spend DOUBLE,
            conversions DOUBLE,
            video_completion_rate DOUBLE,
            _source_file VARCHAR,
            _drop_date DATE,
            _row_in_file INTEGER,
            _loaded_at TIMESTAMP
        )
    """)
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{LOAD_LOG_TABLE} (
            file_name VARCHAR PRIMARY KEY,
            status VARCHAR,
            row_count INTEGER,
            loaded_at TIMESTAMP,
            reason VARCHAR
        )
    """)


def already_seen(con: duckdb.DuckDBPyConnection, file_name: str) -> bool:
    row = con.execute(
        f"SELECT 1 FROM {RAW_SCHEMA}.{LOAD_LOG_TABLE} WHERE file_name = ?", [file_name]
    ).fetchone()
    return row is not None


def log_result(con: duckdb.DuckDBPyConnection, file_name: str, status: str,
                row_count: int, reason: str = "") -> None:
    con.execute(
        f"INSERT INTO {RAW_SCHEMA}.{LOAD_LOG_TABLE} VALUES (?, ?, ?, ?, ?)",
        [file_name, status, row_count, datetime.now(timezone.utc), reason],
    )


def quarantine(path: str, quarantine_dir: str, reason: str) -> None:
    os.makedirs(quarantine_dir, exist_ok=True)
    shutil.copy2(path, os.path.join(quarantine_dir, os.path.basename(path)))
    print(f"  QUARANTINED {os.path.basename(path)}: {reason}")


def normalize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Map either known schema onto the canonical raw-table column set."""
    df = df.copy()
    if "cost" in df.columns:
        df = df.rename(columns={"cost": "spend"})
    if "video_completion_rate" not in df.columns:
        df["video_completion_rate"] = pd.NA
    return df[CANONICAL_COLUMNS]


def load_file(con: duckdb.DuckDBPyConnection, path: str, drop_date: str, quarantine_dir: str) -> dict:
    file_name = os.path.basename(path)
    header = pd.read_csv(path, nrows=0).columns.tolist()

    if header == PRE_DRIFT_COLUMNS or header == POST_DRIFT_COLUMNS:
        df = pd.read_csv(path)
        df = normalize(df, header)
        df["_source_file"] = file_name
        df["_drop_date"] = drop_date
        df["_row_in_file"] = range(len(df))
        df["_loaded_at"] = datetime.now(timezone.utc)

        con.register("df_load", df)
        con.execute(f"INSERT INTO {RAW_SCHEMA}.{RAW_TABLE} SELECT * FROM df_load")
        con.unregister("df_load")

        log_result(con, file_name, "loaded", len(df))
        return {"file": file_name, "status": "loaded", "rows": len(df)}
    else:
        reason = f"unrecognized columns: {header}"
        quarantine(path, quarantine_dir, reason)
        log_result(con, file_name, "quarantined", 0, reason)
        return {"file": file_name, "status": "quarantined", "rows": 0}


def run(drops_dir: str = None, db_path: str = None, quarantine_dir: str = None) -> dict:
    drops_dir = drops_dir or os.path.join(cfg.OUTPUT_ROOT, cfg.DROPS_DIR)
    db_path = db_path or cfg.DB_PATH
    quarantine_dir = quarantine_dir or cfg.QUARANTINE_DIR
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    con = duckdb.connect(db_path)
    ensure_tables(con)

    results = {"loaded": 0, "quarantined": 0, "skipped": 0, "rows_loaded": 0, "files": []}

    files = sorted(f for f in os.listdir(drops_dir) if f.endswith(".csv"))
    for file_name in files:
        if already_seen(con, file_name):
            results["skipped"] += 1
            continue

        match = DROP_FILE_RE.match(file_name)
        drop_date = match.group(1) if match else None

        path = os.path.join(drops_dir, file_name)
        outcome = load_file(con, path, drop_date, quarantine_dir)
        results["files"].append(outcome)
        if outcome["status"] == "loaded":
            results["loaded"] += 1
            results["rows_loaded"] += outcome["rows"]
        else:
            results["quarantined"] += 1

    con.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drops-dir", default=None)
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--quarantine-dir", default=None)
    args = parser.parse_args()

    results = run(args.drops_dir, args.db_path, args.quarantine_dir)
    print(f"Loaded {results['loaded']} file(s), {results['rows_loaded']} row(s). "
          f"Quarantined {results['quarantined']}. Skipped (already loaded) {results['skipped']}.")


if __name__ == "__main__":
    main()
