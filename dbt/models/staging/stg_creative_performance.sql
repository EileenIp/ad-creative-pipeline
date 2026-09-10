{{
  config(
    materialized='incremental',
    unique_key=['event_date', 'campaign_id', 'adset_id', 'creative_id'],
    incremental_strategy='delete+insert'
  )
}}

-- Typing, schema-drift normalization (raw already aliases cost -> spend and
-- backfills video_completion_rate — see src/loader.py), and de-duplication
-- with a stated rule: latest delivery wins.
--
-- Late-arriving and restated rows are handled by reprocessing a lookback
-- window on every run rather than only ever appending: on an incremental
-- run we re-derive every event date within `lookback_days` of the latest
-- date already in this table, and `delete+insert` replaces whatever was
-- there before for that window. Anything older is treated as finalized.
-- Why 7 days, not 3: see spec-ad-creative-pipeline.md session log,
-- 2026-09-10 -- it covers the generator's worst-case corruption lag
-- (late arrival up to 3 days, plus a restatement correction up to 2 days
-- on top of that = 5 days) with a 2-day margin.

with raw as (

    select
        cast(date as date)          as event_date,
        campaign_id,
        adset_id,
        creative_id,
        creative_format,
        placement,
        cast(impressions as bigint) as impressions,
        cast(clicks as bigint)      as clicks,
        cast(spend as double)       as spend,
        cast(conversions as bigint) as conversions,
        video_completion_rate,
        _drop_date,
        _source_file,
        _row_in_file
    from {{ source('raw', 'creative_performance') }}

    {% if is_incremental() %}
    where cast(date as date) >= (
        select max(event_date) - interval '{{ var("lookback_days") }}' day
        from {{ this }}
    )
    {% endif %}

),

-- Same (event_date, campaign_id, adset_id, creative_id) can appear more
-- than once inside the reprocessed window: a late arrival superseding an
-- earlier attempt, a restatement correction, or a straight duplicate row
-- within one file. The most recently delivered drop wins; within the same
-- drop, _row_in_file breaks the tie deterministically (there is no signal
-- in the data for which of two same-key, same-file rows is "truer" -- for
-- near-duplicates this last part is an arbitrary but reproducible choice,
-- not a judgement about data quality).
ranked as (

    select
        *,
        row_number() over (
            partition by event_date, campaign_id, adset_id, creative_id
            order by _drop_date desc, _row_in_file desc
        ) as rn
    from raw

)

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
    _drop_date as loaded_from_drop_date,
    _source_file as loaded_from_file
from ranked
where rn = 1
