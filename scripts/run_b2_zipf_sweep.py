from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_policy, run_repeated_trials  # noqa: E402
from edge_cache_sim.memo_sweep import (  # noqa: E402
    MEMO_NEIGHBOR_ES_AVAILABILITIES,
    MEMO_ORIGIN_DELAYS,
)
from edge_cache_sim.repeated import REPEATED_COLUMNS  # noqa: E402

ZIPF_ALPHAS = (0.6, 0.8, 1.0, 1.1, 1.3, 1.5)
CACHE_RANK_GAMMAS = (0.3, 0.6, 1.0, 1.4, 2.0)
ZIPF_SWEEP_ORIGIN_DELAY = 80.0
ZIPF_SWEEP_NEIGHBOR_AVAILABILITY = 0.55
RANK_BUCKET_ORIGIN_DELAY = 80.0
RANK_BUCKET_NEIGHBOR_AVAILABILITY = 0.55

RANK_BUCKETS = (
    ("hot", "hot (top 5%)", 0.05),
    ("mid", "mid (5-20%)", 0.20),
    ("cold", "cold (20-100%)", 1.00),
)

RANK_BUCKET_TRIAL_COLUMNS = [
    "scenario",
    "trial_index",
    "trial_seed",
    "rank_bucket",
    "rank_bucket_label",
    "rank_bucket_order",
    "request_count",
    "local_failure_count",
    "neighbor_attempt_count",
    "neighbor_failure_count",
    "origin_use_count",
    "b2_neighbor_choice_count",
    "b2_neighbor_choice_rate",
    "origin_free_rate",
    "neighbor_failure_rate",
    "mean_response_time",
    "origin_delay",
    "neighbor_es_availability",
    "zipf_alpha",
    "neighbor_cache_hot_prob",
    "neighbor_cache_cold_prob",
    "neighbor_cache_rank_gamma",
]

RANK_BUCKET_METRICS = [
    "request_count",
    "local_failure_count",
    "neighbor_attempt_count",
    "neighbor_failure_count",
    "origin_use_count",
    "b2_neighbor_choice_count",
    "b2_neighbor_choice_rate",
    "origin_free_rate",
    "neighbor_failure_rate",
    "mean_response_time",
]

RANK_BUCKET_SUMMARY_COLUMNS = [
    "scenario",
    "rank_bucket",
    "rank_bucket_label",
    "rank_bucket_order",
    "trial_count",
    "origin_delay",
    "neighbor_es_availability",
    "zipf_alpha",
    "neighbor_cache_hot_prob",
    "neighbor_cache_cold_prob",
    "neighbor_cache_rank_gamma",
]

for _metric in RANK_BUCKET_METRICS:
    RANK_BUCKET_SUMMARY_COLUMNS.extend(
        [
            f"{_metric}_mean",
            f"{_metric}_std",
            f"{_metric}_stderr",
            f"{_metric}_ci95_low",
            f"{_metric}_ci95_high",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 1.1 B2 Zipf-aware sensitivity experiments."
    )
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--num-requests", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--output-dir", default="results/phase1_b2_zipf")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = SimulationConfig(num_requests=args.num_requests, seed=args.seed)

    neighbor_origin_rows = _neighbor_origin_grid(base, args.trials, args.seed)
    zipf_rows = _zipf_sensitivity_grid(base, args.trials, args.seed)
    rank_summary_rows, rank_trial_rows = _rank_bucket_rows(base, args.trials, args.seed)

    _write_csv(
        output_dir / "neighbor_origin_grid_summary.csv",
        neighbor_origin_rows,
        REPEATED_COLUMNS,
    )
    _write_csv(
        output_dir / "zipf_sensitivity_summary.csv",
        zipf_rows,
        REPEATED_COLUMNS,
    )
    _write_csv(
        output_dir / "rank_bucket_summary.csv",
        rank_summary_rows,
        RANK_BUCKET_SUMMARY_COLUMNS,
    )
    _write_csv(
        output_dir / "rank_bucket_trials.csv",
        rank_trial_rows,
        RANK_BUCKET_TRIAL_COLUMNS,
    )

    print(f"Wrote {output_dir / 'neighbor_origin_grid_summary.csv'}")
    print(f"Wrote {output_dir / 'zipf_sensitivity_summary.csv'}")
    print(f"Wrote {output_dir / 'rank_bucket_summary.csv'}")
    print(f"Wrote {output_dir / 'rank_bucket_trials.csv'}")


def _neighbor_origin_grid(
    base: SimulationConfig,
    trials: int,
    seed: int,
) -> list[dict]:
    rows: list[dict] = []
    for origin_delay in MEMO_ORIGIN_DELAYS:
        for neighbor_availability in MEMO_NEIGHBOR_ES_AVAILABILITIES:
            config = replace(
                base,
                scenario="neighbor_availability_x_origin_delay",
                es_availability=0.82,
                neighbor_es_availability=neighbor_availability,
                origin_delay=origin_delay,
                seed=seed + int(origin_delay * 10) + int(neighbor_availability * 1000),
            )
            summary_rows, _ = run_repeated_trials(
                config,
                trials,
                "neighbor_availability_x_origin_delay",
            )
            rows.extend(summary_rows)
    return rows


def _zipf_sensitivity_grid(
    base: SimulationConfig,
    trials: int,
    seed: int,
) -> list[dict]:
    rows: list[dict] = []
    for zipf_alpha in ZIPF_ALPHAS:
        for gamma in CACHE_RANK_GAMMAS:
            config = replace(
                base,
                scenario="zipf_alpha_x_cache_gamma",
                es_availability=0.82,
                neighbor_es_availability=ZIPF_SWEEP_NEIGHBOR_AVAILABILITY,
                origin_delay=ZIPF_SWEEP_ORIGIN_DELAY,
                zipf_alpha=zipf_alpha,
                neighbor_cache_rank_gamma=gamma,
                seed=seed + int(zipf_alpha * 10_000) + int(gamma * 1000),
            )
            summary_rows, _ = run_repeated_trials(
                config,
                trials,
                "zipf_alpha_x_cache_gamma",
                f"alpha={zipf_alpha};gamma={gamma}",
            )
            rows.extend(summary_rows)
    return rows


def _rank_bucket_rows(
    base: SimulationConfig,
    trials: int,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    trial_rows: list[dict] = []
    for trial_index in range(trials):
        trial_seed = seed + 900_000 + trial_index
        config = replace(
            base,
            scenario="rank_bucket_b2_decision",
            es_availability=0.82,
            neighbor_es_availability=RANK_BUCKET_NEIGHBOR_AVAILABILITY,
            origin_delay=RANK_BUCKET_ORIGIN_DELAY,
            seed=trial_seed,
        )
        rows = run_policy("B2", config, seed=trial_seed)
        trial_rows.extend(_summarize_rank_buckets(rows, config, trial_index, trial_seed))

    return _aggregate_rank_bucket_rows(trial_rows), trial_rows


def _summarize_rank_buckets(
    rows: list[dict],
    config: SimulationConfig,
    trial_index: int,
    trial_seed: int,
) -> list[dict]:
    output: list[dict] = []
    for bucket_index, (bucket, label, _) in enumerate(RANK_BUCKETS):
        bucket_rows = [
            row
            for row in rows
            if _rank_bucket(int(row["content_rank"]), config.num_contents)[0] == bucket
        ]
        request_count = len(bucket_rows)
        local_failure_count = sum(1 for row in bucket_rows if int(row["missing_chunks"]) > 0)
        neighbor_attempt_count = sum(1 for row in bucket_rows if row["neighbor_attempted"])
        neighbor_failure_count = sum(1 for row in bucket_rows if row["neighbor_failed"])
        origin_use_count = sum(1 for row in bucket_rows if row["origin_used"])
        b2_neighbor_choice_count = sum(
            1 for row in bucket_rows if row["b2_neighbor_selected"]
        )
        response_times = [float(row["response_time"]) for row in bucket_rows]
        output.append(
            {
                "scenario": config.scenario,
                "trial_index": trial_index,
                "trial_seed": trial_seed,
                "rank_bucket": bucket,
                "rank_bucket_label": label,
                "rank_bucket_order": bucket_index,
                "request_count": request_count,
                "local_failure_count": local_failure_count,
                "neighbor_attempt_count": neighbor_attempt_count,
                "neighbor_failure_count": neighbor_failure_count,
                "origin_use_count": origin_use_count,
                "b2_neighbor_choice_count": b2_neighbor_choice_count,
                "b2_neighbor_choice_rate": round(
                    b2_neighbor_choice_count / local_failure_count
                    if local_failure_count
                    else 0.0,
                    6,
                ),
                "origin_free_rate": round(
                    1.0 - origin_use_count / request_count if request_count else 0.0,
                    6,
                ),
                "neighbor_failure_rate": round(
                    neighbor_failure_count / neighbor_attempt_count
                    if neighbor_attempt_count
                    else 0.0,
                    6,
                ),
                "mean_response_time": round(
                    sum(response_times) / request_count if request_count else 0.0,
                    6,
                ),
                "origin_delay": config.origin_delay,
                "neighbor_es_availability": config.effective_neighbor_es_availability,
                "zipf_alpha": config.zipf_alpha,
                "neighbor_cache_hot_prob": config.neighbor_cache_hot_prob,
                "neighbor_cache_cold_prob": config.neighbor_cache_cold_prob,
                "neighbor_cache_rank_gamma": config.neighbor_cache_rank_gamma,
            }
        )
    return output


def _aggregate_rank_bucket_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    group_columns = [
        "scenario",
        "rank_bucket",
        "rank_bucket_label",
        "rank_bucket_order",
        "origin_delay",
        "neighbor_es_availability",
        "zipf_alpha",
        "neighbor_cache_hot_prob",
        "neighbor_cache_cold_prob",
        "neighbor_cache_rank_gamma",
    ]
    for row in rows:
        key = tuple(row[column] for column in group_columns)
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict] = []
    for group_values, group_rows in grouped.items():
        output = dict(zip(group_columns, group_values))
        output["trial_count"] = len({row["trial_index"] for row in group_rows})
        for metric in RANK_BUCKET_METRICS:
            values = [float(row[metric]) for row in group_rows]
            mean_value = sum(values) / len(values)
            std_value = _sample_std(values, mean_value) if len(values) > 1 else 0.0
            stderr = std_value / sqrt(len(values)) if len(values) > 1 else 0.0
            ci_delta = 1.96 * stderr
            output[f"{metric}_mean"] = round(mean_value, 6)
            output[f"{metric}_std"] = round(std_value, 6)
            output[f"{metric}_stderr"] = round(stderr, 6)
            output[f"{metric}_ci95_low"] = round(mean_value - ci_delta, 6)
            output[f"{metric}_ci95_high"] = round(mean_value + ci_delta, 6)
        summary_rows.append(output)
    return sorted(summary_rows, key=lambda row: int(row["rank_bucket_order"]))


def _rank_bucket(content_rank: int, num_contents: int) -> tuple[str, str, float]:
    rank_fraction = content_rank / num_contents
    for bucket in RANK_BUCKETS:
        if rank_fraction <= bucket[2]:
            return bucket
    return RANK_BUCKETS[-1]


def _sample_std(values: list[float], mean_value: float) -> float:
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return sqrt(variance)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
