# Ad Creative Performance Pipeline

**The deliverable is the pipeline, not the analysis.** This project generates
openly synthetic ad-creative performance data with deliberately realistic
failure modes (late-arriving rows, restated numbers, duplicates, a schema
change mid-stream, nulls, a clicks-exceed-impressions platform bug, and a
day the platform never delivers) and demonstrates a dbt-core + DuckDB
pipeline that ingests it reliably. No advertising "findings" are claimed —
the numbers are plumbing-test water, not insight.

Status: **Phase 0 done** (the hostile-data generator). Phases 1–4 (ingestion,
dbt transforms/tests, CI + hosted docs, thin dashboard) not started. See
`spec-ad-creative-pipeline.md` for the full phase plan, and
`agent-log/TODO.md` (Roadmap project 1) in `EileenIp.github.io`.

## Phase 0 — what's built

`src/generator.py` (config in `src/config.py`) produces, from a fixed seed:

- 484 creatives across 25 campaigns, 90–390 day lifespans within a 95-day
  window
- `data/raw/ground_truth/true_daily_creative.csv` — the correct numbers,
  never corrupted
- `data/raw/drops/drop_YYYY-MM-DD.csv` — 96 files, one per delivery date,
  each representing what the platform actually handed over that day
- `data/raw/manifest/ground_truth_manifest.jsonl` — every injected defect,
  logged with the affected keys and (for restatements) both the wrong and
  corrected values, so the pipeline's handling of each one can be checked
  against a known answer rather than eyeballed
- 8 defect types: late arrival, restatement, exact duplicate, near
  duplicate, null value, clicks-exceed-impressions, one missing day, one
  schema drift (`spend` → `cost` renamed, `video_completion_rate` column
  added, from day 50 onward)

Run it: `python -m src.generator --clean` from the project root (needs
`requirements.txt` installed). `data/raw/` is gitignored — it's
regenerated, not committed.

**Open for review before Phase 1:** does this defect list need anything
added from ads-domain experience, or is it enough to build the loader
against?
