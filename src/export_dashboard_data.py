"""
Exports a small JSON snapshot of the warehouse for the thin dashboard
(dashboard/index.html). Deliberately modest, matching the dashboard itself:
freshness, a defect log, and yesterday's-equivalent top-decile creatives --
not an analytics tool. The pipeline is the product; this just proves it
produced something a BI lead could actually look at.

Run: `python -m src.export_dashboard_data` from the project root.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import duckdb

from src import config as cfg


def build_snapshot(db_path: str) -> dict:
    con = duckdb.connect(db_path, read_only=True)

    # "Today," as far as this pipeline knows, is the most recent date any
    # drop file claims to have been delivered on -- not wall-clock time.
    # This is synthetic, fixed-calendar demo data (see README); framing
    # "today" against the real date would make a perfectly fresh pipeline
    # look permanently stale.
    today = con.execute("select max(_drop_date) from raw.creative_performance").fetchone()[0]

    latest_available_day = con.execute(
        "select max(event_date) from main.fct_creative_daily"
    ).fetchone()[0]

    lookback_days = cfg.LOOKBACK_DAYS
    latest_finalized_day = con.execute(
        "select cast(cast(? as date) - interval (?) day as date)", [today, lookback_days]
    ).fetchone()[0]

    quarantined = con.execute(
        "select count(*) from raw._load_log where status = 'quarantined'"
    ).fetchone()[0]
    loaded_files = con.execute(
        "select count(*) from raw._load_log where status = 'loaded'"
    ).fetchone()[0]

    manifest_summary_path = os.path.join(
        cfg.OUTPUT_ROOT, cfg.MANIFEST_DIR, "manifest_summary.json"
    )
    defect_counts = {}
    if os.path.exists(manifest_summary_path):
        with open(manifest_summary_path, encoding="utf-8") as f:
            defect_counts = json.load(f).get("defect_counts", {})

    top_decile = con.execute(
        """
        select campaign_id, creative_id, creative_format, placement,
               impressions, clicks, round(ctr, 4) as ctr
        from main.fct_creative_daily
        where event_date = ? and is_top_decile_creative
        order by campaign_id, ctr desc
        """,
        [latest_finalized_day],
    ).fetchdf().to_dict(orient="records")

    con.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today": str(today),
        "latest_available_day": str(latest_available_day),
        "latest_finalized_day": str(latest_finalized_day),
        "lookback_days": lookback_days,
        "loaded_files": loaded_files,
        "quarantined_files": quarantined,
        "defect_counts": defect_counts,
        "top_decile_by_campaign": top_decile,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=cfg.DB_PATH)
    parser.add_argument("--out", default="dashboard/data.json")
    args = parser.parse_args()

    snapshot = build_snapshot(args.db_path)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)

    print(f"Wrote {args.out}: today={snapshot['today']}, "
          f"latest_finalized_day={snapshot['latest_finalized_day']}, "
          f"{len(snapshot['top_decile_by_campaign'])} top-decile rows, "
          f"{snapshot['quarantined_files']} quarantined file(s).")


if __name__ == "__main__":
    main()
