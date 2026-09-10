# Project spec — Ad Creative Performance Pipeline

**For:** Eileen Ip · portfolio project
**Theme:** Marketing (data-engineering showcase — the set's only pipeline project, aimed at BI Developer / Data Engineer applications)
**Agent:** one builder, Sonnet, in Claude Code. Same working rules as the churn spec: stop at every **EILEEN DECIDES**, never invent a number, never write `NOTES.md`, read spec + `NOTES.md` + last commit at session start, commit per phase.

---

## The business question

> Media buyers find out which creatives are winning a week late. Can a pipeline surface top performers same-day, reliably, even when the upstream data misbehaves?

The placeholder card promised "creative-level tagging so buyers see top performers same-day." The honest version: **the deliverable is the pipeline, not the analysis.** What's being demonstrated is transforms, tests, incremental loading, and graceful failure — the skills a BI Developer interview probes. The dashboard at the end is thin by design.

## The data honesty position — settle this first

Real creative-level ad performance data is proprietary; platforms don't publish it (the Facebook Ad Library exposes ads but not their performance). So this project uses **openly synthetic data with deliberately realistic failure modes** — and the README says so in its first paragraph.

That's defensible here, uniquely among your projects, because the skill on display is engineering, not insight: a pipeline's quality is proven by how it handles hostile input, and generating that hostile input on purpose is standard practice (it's how data teams test their own pipelines). What is **not** acceptable: presenting the CTR numbers as findings about advertising. No "lifting CTR 18%." The numbers are plumbing-test water.

**EILEEN DECIDES at Checkpoint 0:** confirm you're comfortable shipping an openly-synthetic engineering project alongside the others, given the portfolio already has one synthetic project. My case for yes: it's the only honest way to show pipeline skills, and the framing ("hostile-input testbed") makes the synthetic-ness a feature. But it's your portfolio.

---

## Stack

**dbt-core + DuckDB, orchestrated by GitHub Actions.** Free, local, runs in CI, and dbt is the lingua franca of the modern BI stack — it appears in a large share of BI Developer job ads. The placeholder said dbt + BigQuery; DuckDB swaps in to avoid cloud cost with zero loss of demonstrated skill (dbt models are near-portable, and the README can say exactly that — knowing *why* it's portable is itself interview material).

## Phase 0 — The generator (the hostile upstream)

**AGENT:** build `generator.py` producing daily drops of creative-level rows: `date, campaign_id, adset_id, creative_id, creative_format, placement, impressions, clicks, spend, conversions` — with realistic scale (hundreds of creatives, tens of campaigns, 90+ days) and **injected, configurable defects**:

- Late-arriving data: a slice of each day's rows arrives 1–3 days later in a subsequent drop
- Restated rows: yesterday's numbers re-delivered with corrections (the platform "trued up")
- Duplicates, exact and near (same row, different file)
- Schema drift on a chosen date: a column renamed, a new column appearing
- Nulls and zero-impression rows; occasional clicks > impressions (a real platform bug pattern)
- A missing day

Every defect logged by the generator to a ground-truth manifest, so pipeline behaviour can be verified against known corruption.

**Checkpoint 0** (the data-honesty decision above, plus review of the defect list — **EILEEN DECIDES** if any defects to add from ads-domain reading).

## Phase 1 — Ingestion & staging

**AGENT:** loader that picks up daily drops idempotently (re-running never double-loads — state tracked in a load manifest), quarantines schema-violating files rather than crashing, and logs row counts in/out per run. dbt staging models: typing, dedup with a stated rule (latest restatement wins), late-data handling via incremental models with a lookback window.

**EILEEN DECIDES:** the lookback window for late/restated data (3 days? 7?). It's a cost-vs-correctness trade: longer windows reprocess more. State the trade in `NOTES.md` — this is the single most common real-world incremental-model decision and a near-certain interview question for DE roles.

## Phase 2 — Transform & metric layer

**AGENT:** dbt marts: `fct_creative_daily`, `dim_creative`, and a metrics model computing CTR, CPC, CPA, conversion rate, spend share — each metric defined once, in one place. **Top-decile flagging**: daily ranking of creatives within campaign by the chosen metric, with a minimum-volume floor so a 12-impression creative can't "win."

**EILEEN DECIDES:** the ranking metric and the volume floor, with reasoning. (CTR alone rewards clickbait; CPA needs conversion volume; a blended rule needs weights — all defensible, pick and defend.)

**dbt tests, not optional:** uniqueness and not-null on keys; accepted ranges (clicks ≤ impressions — which *fails by design* on the injected bug days, and the pipeline's handling of that failure is showcase material); referential integrity; a reconciliation test that daily totals match the generator's ground-truth manifest within the stated lookback.

**Checkpoint 2.**

## Phase 3 — Orchestration & CI

**AGENT:** GitHub Actions workflow running the daily cycle on a schedule and on PR: generate drop → load → `dbt build` (models + tests) → publish artefacts. Failed tests fail the run visibly. A status badge in the README. `dbt docs generate` published to GitHub Pages so the lineage graph is publicly browsable — **that lineage graph is the project's hero image.**

## Phase 4 — The thin dashboard + deliverables

**AGENT:** small self-contained HTML page reading the pipeline's output: today's top-decile creatives per campaign, data-freshness indicator (latest complete day vs today), and a defect log ("3 files quarantined this week"). Deliberately modest — the pipeline is the product.

Then the four-output pattern from the churn spec, adjusted: the deck and report are pitched at a *technical-adjacent* audience (a BI lead, not a marketer) — how the pipeline guarantees same-day numbers and what it does when upstream breaks.

**EILEEN WRITES:** "what didn't work," limitations (synthetic upstream; single-platform schema; what changes with real Meta/Google exports — column mapping, auth, rate limits), and the honest scaling answer (where DuckDB stops and BigQuery starts — approximate numbers, reasoned).

---

## Readiness gate notes

- **Visualisation-only?** No — the opposite risk: it could look *analysis-free*. The framing line for every surface: "the analysis is thin because the product is the reliability."
- **Overused data?** N/A — generated. The differentiator is the defect injection + ground-truth reconciliation, which almost no portfolio pipeline projects do.
- **Business context?** Cleared — same-day creative decisions are a real buying-team pain, and stale reporting is the default state of marketing data.
- **Tutorial clone?** dbt tutorials exist (jaffle-shop). The defences: hostile-input generator, restatement handling, CI with by-design failures, reconciliation to ground truth. None of those are in the tutorials.

## Screening audit

Churn spec Appendix C before shipping. At-risk rows: **Industry relevance** (keep the marketing framing loud — this is for BI/DE roles *in marketing contexts*) and **Depth** (the depth here is engineering depth; the README must make that reframe explicitly so a screener doesn't mark it "no analysis").

## Cost discipline

Estimate A$15–25. dbt/CI debugging is where agents loop — if a workflow fails twice for the same reason, stop the session and bring the log here. Stop and reassess past A$35.

## Definition of done

- [ ] Generator with ≥7 defect types and a ground-truth manifest
- [ ] Idempotent loader with quarantine; incremental models with a defended lookback
- [ ] dbt tests green (except the by-design failures, which are documented as such)
- [ ] CI running the daily cycle; lineage docs live on GitHub Pages
- [ ] Thin dashboard with freshness + defect log
- [ ] README first paragraph states synthetic data plainly; no advertising "findings" claimed
- [ ] Four deliverables; `NOTES.md`; "what didn't work" by Eileen
- [ ] Rehearsed answers: why this lookback, why latest-restatement-wins, why DuckDB and where it stops, what a real Meta export changes

---

## Session log

- 2026-09-10 — Checkpoint 0 passed (go): Eileen confirmed comfortable shipping this as an openly-synthetic engineering project. Phase 0 complete: `src/generator.py` + `src/config.py` produce 484 creatives / 25 campaigns over a 95-day window, seed 42. Outputs `data/raw/ground_truth/true_daily_creative.csv` (25,892 true rows) and 96 `data/raw/drops/drop_*.csv` files with 8 injected defect types (late arrival, restatement, exact/near duplicate, null, clicks-exceed-impressions, one missing day, one schema drift at day 50), all logged to `data/raw/manifest/ground_truth_manifest.jsonl`. Verified: clicks>impressions count in the drops matches the manifest's logged count exactly (78); the missing day has no drop file; pre/post-drift files carry the correct schema. `data/raw/` is gitignored (regenerated, not committed). Committed. Open question for Eileen before Phase 1: does the defect list need anything added from ads-domain experience? Next: Phase 1 (idempotent loader + dbt staging models) once that's answered.
