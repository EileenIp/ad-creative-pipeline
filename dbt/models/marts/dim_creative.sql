{{ config(materialized='table') }}

-- One row per creative_id. Attributes are fixed at creative creation in
-- reality, so any_value() is safe here -- these aren't expected to vary
-- across a creative's rows, and if they ever did, that would itself be a
-- data quality problem worth surfacing, not silently resolving.

select
    creative_id,
    any_value(campaign_id)     as campaign_id,
    any_value(adset_id)        as adset_id,
    any_value(creative_format) as creative_format,
    any_value(placement)       as placement,
    min(event_date)            as first_seen_date,
    max(event_date)            as last_seen_date
from {{ ref('stg_creative_performance') }}
group by creative_id
