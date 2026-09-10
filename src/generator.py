"""
Hostile upstream simulator for the Ad Creative Performance Pipeline.

Generates two things:
  1. `ground_truth/true_daily_creative.csv` — the correct, final numbers per
     (date, creative), as if the ad platform never made a mistake.
  2. `drops/drop_YYYY-MM-DD.csv` — one file per calendar day, representing
     what the platform actually handed the pipeline that day. These files
     are corrupted on purpose: late-arriving rows, restated rows, exact and
     near duplicates, a schema change partway through, nulls, a physics-
     violating clicks>impressions bug, and one day that never shows up at
     all.

Every corruption is logged to `manifest/ground_truth_manifest.jsonl` so the
downstream pipeline's handling of each defect can be checked against a known
answer, not eyeballed.

Run: `python -m src.generator` from the project root. All parameters live in
`src/config.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import timedelta

import numpy as np
import pandas as pd

from src import config as cfg


# ---------------------------------------------------------------------------
# Entities: the campaign / adset / creative hierarchy and each creative's
# fixed "quality" parameters and lifecycle window.
# ---------------------------------------------------------------------------

def build_entities(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    creative_seq = 0
    for c in range(cfg.N_CAMPAIGNS):
        campaign_id = f"cmp_{c + 1:04d}"
        n_adsets = rng.integers(cfg.ADSETS_PER_CAMPAIGN[0], cfg.ADSETS_PER_CAMPAIGN[1] + 1)
        for a in range(n_adsets):
            adset_id = f"{campaign_id}_adset_{a + 1:02d}"
            n_creatives = rng.integers(cfg.CREATIVES_PER_ADSET[0], cfg.CREATIVES_PER_ADSET[1] + 1)
            for _ in range(n_creatives):
                creative_seq += 1
                creative_id = f"cr_{creative_seq:06d}"

                lifespan = int(rng.integers(cfg.CREATIVE_MIN_LIFESPAN_DAYS, cfg.CREATIVE_MAX_LIFESPAN_DAYS + 1))
                latest_launch = max(cfg.N_DAYS - lifespan, 0)
                launch_day = int(rng.integers(0, latest_launch + 1))
                end_day = min(launch_day + lifespan - 1, cfg.N_DAYS - 1)

                rows.append({
                    "campaign_id": campaign_id,
                    "adset_id": adset_id,
                    "creative_id": creative_id,
                    "creative_format": rng.choice(cfg.CREATIVE_FORMATS),
                    "placement": rng.choice(cfg.PLACEMENTS),
                    "launch_day": launch_day,
                    "end_day": end_day,
                    "base_impressions_mean": rng.lognormal(cfg.IMPRESSIONS_MEAN_LOG, cfg.IMPRESSIONS_SIGMA_LOG),
                    "base_ctr": rng.beta(cfg.CTR_ALPHA, cfg.CTR_BETA),
                    "base_cvr": rng.beta(cfg.CVR_ALPHA, cfg.CVR_BETA),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# True daily performance — the correct numbers, before any corruption.
# ---------------------------------------------------------------------------

def build_true_daily(entities: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for e in entities.itertuples(index=False):
        for day_idx in range(e.launch_day, e.end_day + 1):
            event_date = cfg.START_DATE + timedelta(days=day_idx)
            dow_mult = cfg.DOW_MULTIPLIER[event_date.weekday()]

            # ~3% of active-creative-days have a pacing gap: zero impressions.
            if rng.random() < 0.03:
                impressions = 0
            else:
                noise = rng.lognormal(0, 0.35)
                impressions = int(round(e.base_impressions_mean * dow_mult * noise))

            ctr = min(e.base_ctr * rng.lognormal(0, 0.15), 1.0)
            clicks = int(rng.binomial(impressions, ctr)) if impressions > 0 else 0

            cvr = min(e.base_cvr * rng.lognormal(0, 0.15), 1.0)
            conversions = int(rng.binomial(clicks, cvr)) if clicks > 0 else 0

            cpm = cfg.PLACEMENT_CPM[e.placement]
            spend = round(impressions / 1000 * cpm * rng.lognormal(0, 0.1), 2)

            rows.append({
                "date": event_date.isoformat(),
                "day_idx": day_idx,
                "campaign_id": e.campaign_id,
                "adset_id": e.adset_id,
                "creative_id": e.creative_id,
                "creative_format": e.creative_format,
                "placement": e.placement,
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "conversions": conversions,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Delivery simulation: assign each true row a delivery (drop) date, and
# decide which rows get restated later with a wrong-then-corrected pair.
# ---------------------------------------------------------------------------

def assign_delivery_and_restatements(true_daily: pd.DataFrame, rng: np.random.Generator):
    manifest = []
    n = len(true_daily)

    offsets = np.array(list(cfg.LATE_ARRIVAL_OFFSET_PROBS.keys()))
    probs = np.array(list(cfg.LATE_ARRIVAL_OFFSET_PROBS.values()))
    delay_choices = rng.choice(offsets, size=n, p=probs)

    delivered_rows = []
    for row, delay in zip(true_daily.itertuples(index=False), delay_choices):
        delivery_day_idx = row.day_idx + int(delay)
        if delay > 0:
            manifest.append({
                "defect_type": "late_arrival",
                "event_date": row.date,
                "drop_date": (cfg.START_DATE + timedelta(days=delivery_day_idx)).isoformat(),
                "campaign_id": row.campaign_id,
                "adset_id": row.adset_id,
                "creative_id": row.creative_id,
                "detail": {"delayed_by_days": int(delay)},
            })

        is_restated = rng.random() < cfg.RESTATEMENT_RATE
        if is_restated:
            # The first delivery carries a wrong value...
            wrong_factor = rng.uniform(0.5, 1.5)
            wrong_impressions = max(int(round(row.impressions * wrong_factor)), 0)
            wrong_clicks = min(int(round(row.clicks * wrong_factor)), wrong_impressions)
            wrong_spend = round(row.spend * wrong_factor, 2)
            wrong_conversions = min(int(round(row.conversions * wrong_factor)), wrong_clicks)

            delivered_rows.append({
                **row._asdict(),
                "delivery_day_idx": delivery_day_idx,
                "impressions": wrong_impressions,
                "clicks": wrong_clicks,
                "spend": wrong_spend,
                "conversions": wrong_conversions,
            })

            # ...and a corrected row lands `delay_days` later with the true numbers.
            correction_delay = int(rng.integers(cfg.RESTATEMENT_DELAY_DAYS[0], cfg.RESTATEMENT_DELAY_DAYS[1] + 1))
            correction_day_idx = delivery_day_idx + correction_delay
            delivered_rows.append({
                **row._asdict(),
                "delivery_day_idx": correction_day_idx,
            })

            manifest.append({
                "defect_type": "restatement",
                "event_date": row.date,
                "drop_date": (cfg.START_DATE + timedelta(days=correction_day_idx)).isoformat(),
                "campaign_id": row.campaign_id,
                "adset_id": row.adset_id,
                "creative_id": row.creative_id,
                "detail": {
                    "original_drop_date": (cfg.START_DATE + timedelta(days=delivery_day_idx)).isoformat(),
                    "wrong_values": {
                        "impressions": wrong_impressions, "clicks": wrong_clicks,
                        "spend": wrong_spend, "conversions": wrong_conversions,
                    },
                    "corrected_values": {
                        "impressions": row.impressions, "clicks": row.clicks,
                        "spend": row.spend, "conversions": row.conversions,
                    },
                },
            })
        else:
            delivered_rows.append({**row._asdict(), "delivery_day_idx": delivery_day_idx})

    delivered = pd.DataFrame(delivered_rows)
    return delivered, manifest


# ---------------------------------------------------------------------------
# File-level defects, applied per drop: duplicates, nulls, the
# clicks-exceed-impressions bug, and schema drift.
# ---------------------------------------------------------------------------

def inject_file_defects(drop_df: pd.DataFrame, drop_date_str: str, rng: np.random.Generator):
    manifest = []
    df = drop_df.copy().reset_index(drop=True)

    # Exact duplicates: append an identical copy of a sampled row.
    n_exact = int(round(len(df) * cfg.DUPLICATE_EXACT_RATE))
    if n_exact > 0:
        sample = df.sample(n=n_exact, random_state=rng.integers(0, 2**31 - 1))
        df = pd.concat([df, sample], ignore_index=True)
        for r in sample.itertuples(index=False):
            manifest.append({
                "defect_type": "duplicate_exact", "event_date": r.date, "drop_date": drop_date_str,
                "campaign_id": r.campaign_id, "adset_id": r.adset_id, "creative_id": r.creative_id,
                "detail": {},
            })

    # Near duplicates: append a copy with impressions jittered +/-2-8%.
    n_near = int(round(len(df) * cfg.DUPLICATE_NEAR_RATE))
    if n_near > 0:
        sample = df.sample(n=n_near, random_state=rng.integers(0, 2**31 - 1)).copy()
        jitter = rng.uniform(0.92, 1.08, size=len(sample))
        sample["impressions"] = (sample["impressions"] * jitter).round().astype(int)
        df = pd.concat([df, sample], ignore_index=True)
        for r in sample.itertuples(index=False):
            manifest.append({
                "defect_type": "duplicate_near", "event_date": r.date, "drop_date": drop_date_str,
                "campaign_id": r.campaign_id, "adset_id": r.adset_id, "creative_id": r.creative_id,
                "detail": {"jittered_field": "impressions"},
            })

    # Nulls: blank out one metric field on a sample of rows.
    n_null = int(round(len(df) * cfg.NULL_RATE))
    nullable_fields = ["impressions", "clicks", "spend", "conversions"]
    if n_null > 0:
        idx = rng.choice(df.index, size=n_null, replace=False)
        for i in idx:
            field = rng.choice(nullable_fields)
            manifest.append({
                "defect_type": "null_value", "event_date": df.at[i, "date"], "drop_date": drop_date_str,
                "campaign_id": df.at[i, "campaign_id"], "adset_id": df.at[i, "adset_id"],
                "creative_id": df.at[i, "creative_id"], "detail": {"field": field},
            })
            df.at[i, field] = np.nan

    # Clicks > impressions: a platform bug pattern, on rows that survived nulling.
    n_bug = int(round(len(df) * cfg.CLICKS_EXCEED_IMPRESSIONS_RATE))
    if n_bug > 0:
        eligible = df[df["impressions"].notna() & (df["impressions"] > 0)]
        if len(eligible) > 0:
            idx = rng.choice(eligible.index, size=min(n_bug, len(eligible)), replace=False)
            for i in idx:
                bumped = int(df.at[i, "impressions"] + rng.integers(1, max(int(df.at[i, "impressions"] * 0.2), 2)))
                manifest.append({
                    "defect_type": "clicks_exceed_impressions", "event_date": df.at[i, "date"],
                    "drop_date": drop_date_str, "campaign_id": df.at[i, "campaign_id"],
                    "adset_id": df.at[i, "adset_id"], "creative_id": df.at[i, "creative_id"],
                    "detail": {"impressions": int(df.at[i, "impressions"]), "clicks_set_to": bumped},
                })
                df.at[i, "clicks"] = bumped

    return df, manifest


def apply_schema_drift(df: pd.DataFrame) -> pd.DataFrame:
    """From the drift day onward, 'spend' becomes 'cost' and a new
    'video_completion_rate' column appears (video creatives only)."""
    df = df.rename(columns={"spend": "cost"})
    rng = np.random.default_rng(cfg.SEED + 999)  # independent stream, still reproducible
    vcr = np.where(
        df["creative_format"] == "video",
        rng.beta(3, 4, size=len(df)).round(3),
        np.nan,
    )
    df["video_completion_rate"] = vcr
    return df


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "date", "campaign_id", "adset_id", "creative_id", "creative_format",
    "placement", "impressions", "clicks", "spend", "conversions",
]


def generate(out_root: str, seed: int = cfg.SEED) -> dict:
    rng = np.random.default_rng(seed)

    entities = build_entities(rng)
    true_daily = build_true_daily(entities, rng)
    delivered, delivery_manifest = assign_delivery_and_restatements(true_daily, rng)

    drops_dir = os.path.join(out_root, cfg.DROPS_DIR)
    truth_dir = os.path.join(out_root, cfg.GROUND_TRUTH_DIR)
    manifest_dir = os.path.join(out_root, cfg.MANIFEST_DIR)
    for d in (drops_dir, truth_dir, manifest_dir):
        os.makedirs(d, exist_ok=True)

    full_manifest = list(delivery_manifest)

    missing_day_date = (cfg.START_DATE + timedelta(days=cfg.MISSING_DAY_INDEX)).isoformat()
    full_manifest.append({
        "defect_type": "missing_day", "event_date": missing_day_date, "drop_date": missing_day_date,
        "campaign_id": None, "adset_id": None, "creative_id": None,
        "detail": {"note": "Platform never delivered any file for this date. Not a late arrival — "
                            "no drop, ever, covers it."},
    })

    drift_date = (cfg.START_DATE + timedelta(days=cfg.SCHEMA_DRIFT_DAY_INDEX)).isoformat()
    full_manifest.append({
        "defect_type": "schema_drift", "event_date": drift_date, "drop_date": drift_date,
        "campaign_id": None, "adset_id": None, "creative_id": None,
        "detail": {"note": "'spend' renamed to 'cost'; new 'video_completion_rate' column added "
                            "(populated for video format only). Applies to this drop and every "
                            "drop after it."},
    })

    n_files_written = 0
    for day_idx, group in delivered.groupby("delivery_day_idx"):
        if day_idx == cfg.MISSING_DAY_INDEX:
            continue  # the platform lost this day entirely — no file at all

        drop_date = cfg.START_DATE + timedelta(days=int(day_idx))
        drop_date_str = drop_date.isoformat()

        drop_df = group[OUTPUT_COLUMNS].copy()
        drop_df, file_defects = inject_file_defects(drop_df, drop_date_str, rng)
        full_manifest.extend(file_defects)

        if day_idx >= cfg.SCHEMA_DRIFT_DAY_INDEX:
            drop_df = apply_schema_drift(drop_df)

        drop_df = drop_df.sample(frac=1, random_state=rng.integers(0, 2**31 - 1)).reset_index(drop=True)
        out_path = os.path.join(drops_dir, f"drop_{drop_date_str}.csv")
        drop_df.to_csv(out_path, index=False)
        n_files_written += 1

    true_daily_out = true_daily[["date", "campaign_id", "adset_id", "creative_id", "creative_format",
                                  "placement", "impressions", "clicks", "spend", "conversions"]]
    true_daily_out.to_csv(os.path.join(truth_dir, "true_daily_creative.csv"), index=False)

    manifest_path = os.path.join(manifest_dir, "ground_truth_manifest.jsonl")
    with open(manifest_path, "w", encoding="utf-8") as f:
        for entry in full_manifest:
            f.write(json.dumps(entry) + "\n")

    counts = {}
    for entry in full_manifest:
        counts[entry["defect_type"]] = counts.get(entry["defect_type"], 0) + 1

    summary = {
        "seed": seed,
        "n_campaigns": cfg.N_CAMPAIGNS,
        "n_creatives": entities["creative_id"].nunique(),
        "n_true_rows": len(true_daily),
        "n_drop_files_written": n_files_written,
        "n_days_configured": cfg.N_DAYS,
        "missing_day": missing_day_date,
        "schema_drift_date": drift_date,
        "defect_counts": counts,
    }
    with open(os.path.join(manifest_dir, "manifest_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=cfg.OUTPUT_ROOT, help="Output root directory")
    parser.add_argument("--seed", type=int, default=cfg.SEED)
    parser.add_argument("--clean", action="store_true", help="Delete --out before generating")
    args = parser.parse_args()

    if args.clean and os.path.exists(args.out):
        shutil.rmtree(args.out)

    summary = generate(args.out, seed=args.seed)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
