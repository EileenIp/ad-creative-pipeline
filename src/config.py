"""All generator parameters in one place. Change values here, not in generator.py."""

from datetime import date

# --- Reproducibility ---
SEED = 42

# --- Scale ---
START_DATE = date(2026, 1, 1)
N_DAYS = 95  # 90+ per spec

N_CAMPAIGNS = 25
ADSETS_PER_CAMPAIGN = (2, 5)      # inclusive random range
CREATIVES_PER_ADSET = (3, 8)      # inclusive random range

CREATIVE_FORMATS = ["video", "static_image", "carousel", "collection"]
PLACEMENTS = ["feed", "stories", "reels", "audience_network", "in_stream"]

# CPM (cost per 1000 impressions, in dollars) varies by placement — reels/stories
# command a premium in real platforms, audience_network is cheapest.
PLACEMENT_CPM = {
    "feed": 8.0,
    "stories": 9.5,
    "reels": 10.5,
    "audience_network": 4.0,
    "in_stream": 7.0,
}

# --- Creative lifecycle ---
# Each creative launches on a random day and runs for a random number of days
# within the window (not every creative is live for the whole 95 days).
CREATIVE_MIN_LIFESPAN_DAYS = 14
CREATIVE_MAX_LIFESPAN_DAYS = 95

# --- True performance distributions ---
# Base daily impressions per active creative (before day-of-week noise).
IMPRESSIONS_MEAN_LOG = 8.5   # lognormal, ~ a few thousand impressions/day median
IMPRESSIONS_SIGMA_LOG = 1.1

# Base CTR per creative drawn from a Beta distribution (creative "quality").
CTR_ALPHA = 2.0
CTR_BETA = 140.0  # mean ~1.4%, realistic paid-social CTR range

# Base CVR (conversions per click) drawn from a Beta distribution.
CVR_ALPHA = 3.0
CVR_BETA = 60.0  # mean ~5%

# Day-of-week multiplier (Mon=0 .. Sun=6) — weekend dip is typical for B2C ads.
DOW_MULTIPLIER = [1.05, 1.05, 1.0, 1.0, 1.05, 0.85, 0.8]

# --- Defect injection rates (fraction of eligible rows/events) ---
LATE_ARRIVAL_OFFSET_PROBS = {0: 0.90, 1: 0.06, 2: 0.03, 3: 0.01}  # days late
RESTATEMENT_RATE = 0.05          # fraction of (date, creative) rows restated later
RESTATEMENT_DELAY_DAYS = (1, 2)  # inclusive random range for correction delay
DUPLICATE_EXACT_RATE = 0.004     # fraction of rows in a drop exactly duplicated
DUPLICATE_NEAR_RATE = 0.004      # fraction of rows duplicated with a jittered metric
NULL_RATE = 0.01                 # fraction of rows with one field nulled
CLICKS_EXCEED_IMPRESSIONS_RATE = 0.003

# Schema drift: from this day index onward, 'spend' is renamed to 'cost' and a
# new 'video_completion_rate' column appears (populated only for video format).
SCHEMA_DRIFT_DAY_INDEX = 50

# Missing day: this day index is never delivered in any drop (permanent gap,
# not a late arrival — the platform simply lost it).
MISSING_DAY_INDEX = 70

# --- Output (generator) ---
OUTPUT_ROOT = "data/raw"
DROPS_DIR = "drops"
GROUND_TRUTH_DIR = "ground_truth"
MANIFEST_DIR = "manifest"

# --- Loader / warehouse ---
DB_PATH = "data/processed/warehouse.duckdb"
QUARANTINE_DIR = "data/quarantine"

# --- Marts: top-decile ranking ---
# Ranking metric: CTR alone (Eileen's call, 2026-09-10 -- simplicity over a
# blended score). A creative can't win on a handful of impressions, so
# ranking is restricted to creatives clearing this daily impressions floor.
# 1,000 sits close to the observed p10 of daily impressions per creative,
# so it excludes roughly the noisiest bottom decile without gutting the
# eligible population (91% of creative-days still qualify). See the spec's
# session log for the full reasoning.
MIN_IMPRESSIONS_FLOOR = 1000

# --- Staging model ---
# How many days behind the latest loaded event date to reprocess on each
# incremental run, to catch late-arriving and restated rows. Chosen to cover
# the generator's worst case: late arrival (up to 3 days) plus a restatement
# correction on top of that (up to 2 more days) = 5 days, with a 2-day
# margin. See spec-ad-creative-pipeline.md session log, 2026-09-10.
LOOKBACK_DAYS = 7
