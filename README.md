# Ad Creative Performance Pipeline

[![Daily pipeline](https://github.com/EileenIp/ad-creative-pipeline/actions/workflows/pipeline.yml/badge.svg)](https://github.com/EileenIp/ad-creative-pipeline/actions/workflows/pipeline.yml)

**The deliverable is the pipeline, not the analysis.** This project generates
openly synthetic ad-creative performance data with deliberately realistic
failure modes (late-arriving rows, restated numbers, duplicates, a schema
change mid-stream, nulls, a clicks-exceed-impressions platform bug, and a
day the platform never delivers) and demonstrates a dbt-core + DuckDB
pipeline that ingests it reliably. No advertising "findings" are claimed —
the numbers are plumbing-test water, not insight.

**[Browse the lineage graph and full model docs →](https://eileenip.github.io/ad-creative-pipeline/)**
**[Browse the thin dashboard →](https://eileenip.github.io/ad-creative-pipeline/dashboard/)**

Status: **All four phases done**, plus the four-output deliverable
pattern: `deliverables/same-day-reliability-report.docx`,
`deliverables/same-day-reliability-deck.pptx`, the thin dashboard, and
the [website case study](https://eileenip.github.io/ad-creative-pipeline/)
(replacing the old placeholder card in `EileenIp.github.io`). See
`spec-ad-creative-pipeline.md` for the full phase plan, and
`agent-log/TODO.md` (Roadmap project 1) in `EileenIp.github.io`.

## Running it end to end

```bash
pip install -r requirements.txt
python -m src.generator --clean       # writes data/raw/
python -m src.loader                  # lands drops into data/processed/warehouse.duckdb
mkdir -p dbt/seeds
cp data/raw/ground_truth/true_daily_creative.csv dbt/seeds/
cd dbt
dbt seed --profiles-dir .
dbt build --profiles-dir . --full-refresh   # first run; drop --full-refresh after
cd ..
python -m src.export_dashboard_data   # writes dashboard/data.json
python -m http.server 5502 --directory dashboard   # then open http://localhost:5502
```
`data/`, `dbt/seeds/*.csv`, and `dashboard/data.json` are entirely
gitignored (regenerated, not committed) — a fresh clone needs those
commands before there's anything to query or view. `.github/workflows/pipeline.yml`
runs this same sequence in CI and publishes both the docs and the
dashboard to GitHub Pages.

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

## Phase 3 — what's built

`.github/workflows/pipeline.yml` runs on every push to `master`, every PR,
a daily schedule, and manual dispatch: install deps → generate the hostile
dataset fresh → load → seed the ground truth → `dbt build` (models + all
10 tests) → `dbt docs generate --static` → publish to GitHub Pages.

**Design call, not an oversight:** every run regenerates and rebuilds from
a clean state rather than reusing a warehouse persisted across runs. The
generator is a fixed, seeded dataset, not a live upstream, so a cached
warehouse wouldn't add anything real here — and a from-scratch build on
every run catches a broken loader or dbt change immediately instead of
letting stale cache mask it. The incremental/lookback logic itself is
exercised and verified locally, not in CI — see the spec's session log.

The dbt docs job uses `--static`, which bundles the manifest, catalog and
lineage graph into one self-contained HTML file — no separate `target/`
directory with relative-path assets to get right on Pages. **The lineage
graph is the project's hero image**: `raw.creative_performance` →
`stg_creative_performance` → `dim_creative` / `fct_creative_daily`,
publicly browsable, not a screenshot.

**One-time manual step, not done by the agent:** GitHub Pages needed
"Settings → Pages → Build and deployment → Source: GitHub Actions" enabled
once — a repo-settings change outside the Claude Code auto-mode permission
scope, so Eileen did it herself. (The first attempt silently didn't save;
caught by checking `gh api repos/.../pages` directly rather than trusting
the settings UI — worth knowing this endpoint exists next time something
in GitHub's web UI looks right but isn't taking effect.) Confirmed live
and working, not just green-checkmarked: both the docs and the dashboard
(Phase 4) were checked in-browser at their real published URLs.

The `dbt/seeds/` directory itself was a real bug the first CI run caught
that local testing never would have: it never existed on a fresh
checkout (git doesn't track empty directories, and the one file that
lived there is gitignored), so the plain `cp` step failed and silently
skipped `dbt seed` + `dbt build` entirely. Fixed with a tracked
`.gitkeep` plus a defensive `mkdir -p`.

## Phase 4 — what's built

`src/export_dashboard_data.py` queries the live warehouse and writes
`dashboard/data.json`; `dashboard/index.html` is a small, dependency-free
HTML/CSS/vanilla-JS page that fetches it and renders three things, exactly
as scoped — no more:

- **Freshness**, as two numbers, not one: the *latest finalized day*
  (outside the lookback window — guaranteed not to change again) and the
  *latest available day* (inside it — provisional, still revisable). The
  gap between them is the lookback window itself, made visible rather than
  hidden in a config file.
- **A defect log** — every injected defect type from the last generator
  run, plus files loaded/quarantined.
- **Top-decile creatives for the latest finalized day**, by campaign — the
  same `fct_creative_daily.is_top_decile_creative` flag from Phase 2, not
  a separate calculation.

**"Today" is the pipeline's own latest delivery date, not the real
calendar date** — stated on the page itself, in the same banner as the
synthetic-data disclosure. This dataset has a fixed calendar
(`src/config.py` `START_DATE`); framing freshness against wall-clock time
would make a perfectly healthy pipeline look permanently stale, which is
exactly the kind of overstatement `EileenIp.github.io/agent-log/CLAUDE.md`
rules out.

Wired into the same CI job as the docs (`.github/workflows/pipeline.yml`):
generated fresh every run and published to Pages alongside the lineage
docs, at `/dashboard/` — not a local-only artifact. Checked on an actual
mobile viewport during the build: the results table initially overflowed
the page instead of scrolling within itself (a real bug, not a style
nitpick — the same class of thing flagged in the site's own "check mobile
rendering" TODO), fixed with a scoped `overflow-x: auto` wrapper before
committing.

## Deliverables

`deliverables/same-day-reliability-report.docx` and
`deliverables/same-day-reliability-deck.pptx` (built from
`app/build_report.js` / `app/build_deck.js` — `npm install` then `npm run
build:report` / `npm run build:deck`), pitched at a BI-lead audience: how
the pipeline guarantees same-day numbers and what it does when upstream
breaks. Plus the thin dashboard above and the
[website case study](https://eileenip.github.io/ad-creative-pipeline/),
which replaces the old placeholder card in `EileenIp.github.io`.

At Eileen's explicit request, the agent wrote the "what didn't work" /
limitations content too, rather than leaving it blank — normally reserved
for Eileen's own words, since the point is being able to defend it live.
Everything in it is grounded in real, verified facts from this build (the
three engineering bugs, the reconciliation test's own fix), plus two
items requiring real domain judgment — the Meta/Google Ads export delta
and the DuckDB-to-BigQuery scaling answer — answered with genuine,
qualitative technical reasoning rather than invented precise numbers.
**Read these before using them in an interview** — they're written to be
true and defensible, not to replace having actually thought it through.
