# Ad Creative Performance Pipeline

**The deliverable is the pipeline, not the analysis.** This project generates
openly synthetic ad-creative performance data with deliberately realistic
failure modes (late-arriving rows, restated numbers, duplicates, a schema
change mid-stream, nulls, a clicks-exceed-impressions platform bug, and a
day the platform never delivers) and demonstrates a dbt-core + DuckDB
pipeline that ingests it reliably. No advertising "findings" are claimed —
the numbers are plumbing-test water, not insight.

Status: **Phase 2 done** (marts + dbt tests). Phases 3–4 (CI + hosted docs,
thin dashboard) not started. See `spec-ad-creative-pipeline.md` for the
full phase plan, and `agent-log/TODO.md` (Roadmap project 1) in
`EileenIp.github.io`.

## Running it end to end

```bash
pip install -r requirements.txt
python -m src.generator --clean       # writes data/raw/
python -m src.loader                  # lands drops into data/processed/warehouse.duckdb
cp data/raw/ground_truth/true_daily_creative.csv dbt/seeds/
cd dbt
dbt seed --profiles-dir .
dbt build --profiles-dir . --full-refresh   # first run; drop --full-refresh after
```
`data/` and `dbt/seeds/*.csv` are entirely gitignored (regenerated, not
committed) — a fresh clone needs those commands before there's anything to
query. Phase 3 will fold the seed-copy step into CI so the reconciliation
test always runs against a live-generated ground truth, not a stale copy.

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

## Phase 1 — what's built

`src/loader.py` lands every drop file into a DuckDB raw table verbatim
(duplicates and superseded restatements included — the raw layer's job is
to preserve exactly what was delivered). It's idempotent (a load log inside
the warehouse tracks which files are already in, so reruns never
double-insert) and quarantines any file whose columns don't match either
known schema instead of crashing.

`dbt/models/staging/stg_creative_performance.sql` types the raw rows and
deduplicates with a stated rule — latest delivery wins, tie-broken
deterministically within a single file — as an incremental model with a
7-day lookback (why 7, not 3: see the spec's session log). Verified against
the Phase 0 ground truth: staging reconciles to the true numbers exactly
except for rows that were genuinely unrecoverable — the missing day itself,
plus a handful of late-arriving rows from the three days before it that
happened to be scheduled for delivery on that date and so vanished with it.
That's a real finding about the missing-day defect, not a pipeline bug: a
platform outage on day N doesn't just cost day N, it costs whatever was
queued to arrive late on day N from the days before.

Tests: `tests/test_loader.py` covers both schema variants loading
correctly, unrecognized schemas being quarantined (not crashing the run),
and idempotent reruns not double-counting rows.

## Phase 2 — what's built

Marts: `dim_creative` (one row per creative) and `fct_creative_daily` (one
row per event_date × creative_id) with every metric defined once — CTR,
CPC, CPA, conversion rate, spend share (as a fraction of that campaign's
same-day spend) — each guarded against zero/null denominators, since the
generator nulls fields and produces zero-impression rows on purpose.

**Ranking: CTR alone**, Eileen's call for simplicity over CPA or a blended
score, restricted to creatives clearing a 1,000-daily-impression floor (my
call, grounded in the data — see `src/config.py` `MIN_IMPRESSIONS_FLOOR`)
so a handful of impressions can't "win." Ranked within (campaign, day).
Known limitation: `percent_rank` on small same-day campaign groups (e.g.
n=8) buckets coarsely, so the actual flagged share runs closer to 12–18%
than an exact 10% — worth a line in the eventual write-up, not a bug.

**dbt tests (10, `dbt build` / `dbt test`):** uniqueness + not-null on
keys; referential integrity (`fct_creative_daily.creative_id` →
`dim_creative`); `assert_clicks_lte_impressions` (severity `warn` — this
one is *supposed* to find rows, ~76-78 of them, since the clicks-bug
defect is never corrected upstream); `assert_reconciliation_within_lookback`
(the ground-truth check, scoped to the lookback window).

Getting the reconciliation test green surfaced a real modeling question:
not every defect is supposed to self-heal. Late arrivals, restatements,
and cross-file duplicates do — the platform eventually delivers a clean
version and dedup/lookback converges on it. Nulls, the clicks-bug, and a
same-*file* duplicate/near-duplicate (no separate correction ever
arrives, and for same-file near-duplicates there's no signal for which
copy is "truer") don't, and shouldn't be forced to — a pipeline that made
those match ground truth would be inventing numbers. `stg_creative_performance`
now exposes `had_same_drop_duplicate` so that ambiguity is visible instead
of silently resolved. First-pass version of this test failed on exactly
that distinction (7 rows, one clean bug), which is the kind of thing worth
being able to explain in an interview.
