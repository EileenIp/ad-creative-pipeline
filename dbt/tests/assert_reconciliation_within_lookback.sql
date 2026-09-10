-- Reconciliation against the generator's ground truth, scoped to the
-- lookback window: the incremental staging model only ever reprocesses
-- event dates within lookback_days of the latest loaded date, so that's
-- the only window where "matches ground truth" is a fair expectation.
--
-- Not every injected defect is supposed to self-heal here. Late arrivals,
-- restatements and exact duplicates delivered across *different* files do
-- -- the platform eventually delivers a correct, unambiguous version, and
-- dedup/lookback should converge on it. Three defect types deliberately
-- do NOT, and are excluded from the value comparison below rather than
-- silently "reconciled" away:
--   - nulled fields and the clicks-exceed-impressions bug -- the generator
--     never issues a correction for either, so matching ground truth would
--     mean inventing a number (assert_clicks_lte_impressions.sql is what
--     surfaces the latter instead);
--   - a same-file duplicate/near-duplicate (stg_creative_performance's
--     had_same_drop_duplicate) -- when two candidate rows for one key
--     arrive in the *same* file, there is no signal for which is "truer,"
--     so the surviving value is an arbitrary, documented tiebreak, not a
--     wrong answer to be fixed.
-- A row missing from fct_creative_daily entirely, corrupted or not, still
-- fails this test: that would be real, unexplained data loss.
--
-- Older, out-of-window dates are out of scope here too: the missing-day
-- defect (src/config.py MISSING_DAY_INDEX) creates a real, permanent,
-- documented gap further back in history (see the spec's session log and
-- README), which a per-run test isn't the right place to keep re-flagging.
--
-- Needs `dbt seed` run first against a seed copied from
-- data/raw/ground_truth/true_daily_creative.csv (see README).

with cutoff as (
    select max(event_date) - interval '{{ var("lookback_days") }}' day as cutoff_date
    from {{ ref('fct_creative_daily') }}
),

expected as (
    select
        cast(date as date) as event_date,
        creative_id,
        impressions,
        clicks,
        round(spend, 2) as spend,
        conversions
    from {{ ref('true_daily_creative') }}, cutoff
    where cast(date as date) >= cutoff.cutoff_date
),

actual_all as (
    select
        event_date,
        creative_id,
        impressions,
        clicks,
        round(spend, 2) as spend,
        conversions,
        (impressions is null or clicks is null or spend is null or conversions is null
            or clicks > impressions or had_same_drop_duplicate) as known_uncorrected_defect
    from {{ ref('fct_creative_daily') }}, cutoff
    where event_date >= cutoff.cutoff_date
),

missing_entirely as (
    -- An expected row absent from fct_creative_daily altogether -- not
    -- even as a null/bug row. A real gap.
    select e.event_date, e.creative_id, 'missing_from_fct' as issue
    from expected e
    left join actual_all a using (event_date, creative_id)
    where a.event_date is null
),

value_mismatch as (
    -- Present, free of the two known-uncorrected defect types, but still
    -- doesn't match ground truth -- a genuine reconciliation gap.
    select a.event_date, a.creative_id, 'value_mismatch' as issue
    from actual_all a
    inner join expected e using (event_date, creative_id)
    where not a.known_uncorrected_defect
      and (a.impressions is distinct from e.impressions
        or a.clicks      is distinct from e.clicks
        or a.spend       is distinct from e.spend
        or a.conversions is distinct from e.conversions)
)

select * from missing_entirely
union all
select * from value_mismatch
