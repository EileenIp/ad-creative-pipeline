{{ config(materialized='table') }}

-- Grain: one row per (event_date, creative_id). Every performance metric is
-- defined exactly once here -- CTR, CPC, CPA, conversion rate, spend share
-- -- so nothing downstream recomputes them differently. Every ratio is
-- guarded with nullif() against a zero or null denominator: the generator
-- injects zero-impression days and nulled fields on purpose, and a metric
-- should read as "unknown," not divide-by-zero or a silent zero.
--
-- spend_share is spend as a fraction of that campaign's total spend on
-- that day -- a stated assumption, not the only valid denominator (adset-
-- level share would be equally defensible; campaign was chosen because
-- that's also the ranking scope below).
--
-- Top-decile flagging: within each (campaign_id, event_date), creatives are
-- ranked by CTR alone -- chosen for simplicity over CPA or a blended score
-- (Eileen's call, 2026-09-10) -- but only among creatives clearing a
-- 1,000-daily-impression floor (src/config.py MIN_IMPRESSIONS_FLOOR). Below
-- the floor, a creative isn't ranked at all, so a handful of impressions
-- can't "win" by accident.
--
-- Materialized as a full table rebuild every run rather than incremental --
-- the lookback/dedup logic that actually needs incrementality lives one
-- layer down, in stg_creative_performance. At this data volume a full
-- rebuild here is simpler and just as fast.

with base as (

    select
        event_date,
        campaign_id,
        adset_id,
        creative_id,
        creative_format,
        placement,
        impressions,
        clicks,
        spend,
        conversions,
        video_completion_rate,
        had_same_drop_duplicate
    from {{ ref('stg_creative_performance') }}

),

metrics as (

    select
        *,
        clicks / nullif(impressions, 0)      as ctr,
        spend / nullif(clicks, 0)             as cpc,
        spend / nullif(conversions, 0)        as cpa,
        conversions / nullif(clicks, 0)       as conversion_rate,
        spend / nullif(sum(spend) over (partition by campaign_id, event_date), 0) as spend_share,
        impressions >= {{ var('min_impressions_floor') }} as meets_volume_floor
    from base

),

ranked as (

    select
        *,
        case when meets_volume_floor then
            percent_rank() over (
                partition by campaign_id, event_date, meets_volume_floor
                order by ctr desc
            )
        end as ctr_percentile_in_campaign_day
    from metrics

)

select
    md5(event_date::varchar || '-' || creative_id) as creative_daily_id,
    event_date,
    campaign_id,
    adset_id,
    creative_id,
    creative_format,
    placement,
    impressions,
    clicks,
    spend,
    conversions,
    video_completion_rate,
    had_same_drop_duplicate,
    ctr,
    cpc,
    cpa,
    conversion_rate,
    spend_share,
    meets_volume_floor,
    ctr_percentile_in_campaign_day,
    coalesce(ctr_percentile_in_campaign_day <= 0.1, false) as is_top_decile_creative
from ranked
