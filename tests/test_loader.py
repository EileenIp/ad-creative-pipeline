import os

import duckdb
import pandas as pd

from src import loader

PRE_DRIFT_ROW = {
    "date": "2026-01-01", "campaign_id": "cmp_0001", "adset_id": "a1", "creative_id": "c1",
    "creative_format": "video", "placement": "feed",
    "impressions": 100, "clicks": 5, "spend": 2.5, "conversions": 1,
}
POST_DRIFT_ROW = {
    "date": "2026-03-01", "campaign_id": "cmp_0001", "adset_id": "a1", "creative_id": "c1",
    "creative_format": "video", "placement": "feed",
    "impressions": 200, "clicks": 8, "cost": 4.0, "conversions": 2, "video_completion_rate": 0.6,
}


def _write_drop(drops_dir, file_name, row):
    pd.DataFrame([row]).to_csv(os.path.join(drops_dir, file_name), index=False)


def test_loads_pre_and_post_drift_schemas(tmp_path):
    drops_dir = tmp_path / "drops"
    drops_dir.mkdir()
    _write_drop(drops_dir, "drop_2026-01-01.csv", PRE_DRIFT_ROW)
    _write_drop(drops_dir, "drop_2026-03-01.csv", POST_DRIFT_ROW)

    db_path = str(tmp_path / "wh.duckdb")
    quarantine_dir = str(tmp_path / "quarantine")

    results = loader.run(str(drops_dir), db_path, quarantine_dir)

    assert results["loaded"] == 2
    assert results["quarantined"] == 0
    assert results["rows_loaded"] == 2

    con = duckdb.connect(db_path)
    rows = con.execute(
        "SELECT date, spend, video_completion_rate FROM raw.creative_performance ORDER BY date"
    ).fetchall()
    con.close()

    # Pre-drift row: 'spend' as-is, no completion rate.
    assert rows[0][1] == 2.5
    assert rows[0][2] is None
    # Post-drift row: 'cost' normalized onto 'spend', completion rate carried through.
    assert rows[1][1] == 4.0
    assert rows[1][2] == 0.6


def test_quarantines_unrecognized_schema(tmp_path):
    drops_dir = tmp_path / "drops"
    drops_dir.mkdir()
    _write_drop(drops_dir, "drop_2026-01-01.csv", PRE_DRIFT_ROW)
    pd.DataFrame([{"date": "2026-01-02", "foo": "bar", "baz": 123}]).to_csv(
        drops_dir / "drop_2026-01-02.csv", index=False
    )

    db_path = str(tmp_path / "wh.duckdb")
    quarantine_dir = str(tmp_path / "quarantine")

    results = loader.run(str(drops_dir), db_path, quarantine_dir)

    assert results["loaded"] == 1
    assert results["quarantined"] == 1
    assert os.path.exists(os.path.join(quarantine_dir, "drop_2026-01-02.csv"))

    con = duckdb.connect(db_path)
    n = con.execute("SELECT count(*) FROM raw.creative_performance").fetchone()[0]
    con.close()
    assert n == 1  # the malformed file never made it into the raw table


def test_rerun_is_idempotent(tmp_path):
    drops_dir = tmp_path / "drops"
    drops_dir.mkdir()
    _write_drop(drops_dir, "drop_2026-01-01.csv", PRE_DRIFT_ROW)

    db_path = str(tmp_path / "wh.duckdb")
    quarantine_dir = str(tmp_path / "quarantine")

    first = loader.run(str(drops_dir), db_path, quarantine_dir)
    second = loader.run(str(drops_dir), db_path, quarantine_dir)

    assert first["loaded"] == 1
    assert second["loaded"] == 0
    assert second["skipped"] == 1

    con = duckdb.connect(db_path)
    n = con.execute("SELECT count(*) FROM raw.creative_performance").fetchone()[0]
    con.close()
    assert n == 1  # not 2 -- the second run must not double-insert
