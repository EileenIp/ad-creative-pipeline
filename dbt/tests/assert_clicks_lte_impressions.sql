{{ config(severity='warn') }}

-- By design, this finds rows: the generator injects a clicks-exceed-
-- impressions bug (a real platform bug pattern) on ~0.3% of rows to prove
-- the pipeline surfaces impossible numbers instead of silently accepting
-- them. Expect roughly 78 rows on the current seed (see
-- data/raw/manifest/manifest_summary.json). severity='warn' so this
-- doesn't red-X every CI run for a defect that's supposed to be there --
-- but a big jump in the count run-over-run means something upstream
-- changed, and is worth looking at.

select *
from {{ ref('fct_creative_daily') }}
where clicks > impressions
