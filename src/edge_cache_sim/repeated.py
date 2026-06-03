"""Repeated-trial helpers for first-stage simulation analysis."""

from __future__ import annotations

from dataclasses import replace
from math import sqrt
from typing import Iterable

from .config import SimulationConfig
from .simulator import POLICY_ORDER, run_scenario

TRIAL_METRICS = [
    "mean_response_time",
    "p95_response_time",
    "origin_free_rate",
    "local_failure_rate",
    "neighbor_attempt_rate",
    "neighbor_failure_rate",
    "b2_neighbor_choice_rate",
]

REPEATED_COLUMNS = [
    "scenario",
    "policy",
    "trial_count",
    "sweep_name",
    "sweep_value",
    "origin_delay",
    "es_availability",
    "local_es_availability",
    "neighbor_es_availability",
    "zipf_alpha",
    "local_es_count",
    "neighbor_group_size",
    "k",
    "neighbor_cache_hot_prob",
    "neighbor_cache_cold_prob",
    "neighbor_cache_rank_gamma",
]

for _metric in TRIAL_METRICS:
    REPEATED_COLUMNS.extend(
        [
            f"{_metric}_mean",
            f"{_metric}_std",
            f"{_metric}_stderr",
            f"{_metric}_ci95_low",
            f"{_metric}_ci95_high",
        ]
    )

REPEATED_COLUMNS.append("b2_advantage_vs_b1_mean")


def run_repeated_trials(
    config: SimulationConfig,
    trials: int,
    sweep_name: str,
    sweep_value: float | str = "",
) -> tuple[list[dict], list[dict]]:
    if trials < 1:
        raise ValueError("trials must be at least 1")

    trial_rows: list[dict] = []
    for trial_index in range(trials):
        trial_seed = config.seed + trial_index
        trial_config = replace(config, seed=trial_seed)
        summary_rows, _ = run_scenario(trial_config)
        for row in summary_rows:
            row = dict(row)
            row["trial_index"] = trial_index
            row["trial_seed"] = trial_seed
            row["sweep_name"] = sweep_name
            row["sweep_value"] = sweep_value
            trial_rows.append(row)

    return aggregate_trial_rows(trial_rows), trial_rows


def aggregate_trial_rows(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    if not rows:
        return []

    group_columns = [
        "scenario",
        "policy",
        "sweep_name",
        "sweep_value",
        "origin_delay",
        "es_availability",
        "local_es_availability",
        "neighbor_es_availability",
        "zipf_alpha",
        "local_es_count",
        "neighbor_group_size",
        "k",
        "neighbor_cache_hot_prob",
        "neighbor_cache_cold_prob",
        "neighbor_cache_rank_gamma",
    ]

    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = tuple(row[column] for column in group_columns)
        grouped.setdefault(key, []).append(row)

    aggregated: list[dict] = []
    for group_values, group_rows in grouped.items():
        row = dict(zip(group_columns, group_values))
        row["trial_count"] = len({group_row["trial_index"] for group_row in group_rows})
        for metric in TRIAL_METRICS:
            values = [float(group_row[metric]) for group_row in group_rows]
            mean_value = sum(values) / len(values)
            std_value = _sample_std(values, mean_value) if len(values) > 1 else 0.0
            stderr = std_value / sqrt(len(values)) if len(values) > 1 else 0.0
            ci_delta = 1.96 * stderr
            row[f"{metric}_mean"] = round(mean_value, 6)
            row[f"{metric}_std"] = round(std_value, 6)
            row[f"{metric}_stderr"] = round(stderr, 6)
            row[f"{metric}_ci95_low"] = round(mean_value - ci_delta, 6)
            row[f"{metric}_ci95_high"] = round(mean_value + ci_delta, 6)
        aggregated.append(row)

    return _with_b2_advantage(aggregated)


def _with_b2_advantage(rows: list[dict]) -> list[dict]:
    key_columns = [
        "scenario",
        "sweep_name",
        "sweep_value",
        "origin_delay",
        "es_availability",
        "local_es_availability",
        "neighbor_es_availability",
        "zipf_alpha",
        "local_es_count",
        "neighbor_group_size",
        "k",
        "neighbor_cache_hot_prob",
        "neighbor_cache_cold_prob",
        "neighbor_cache_rank_gamma",
    ]
    if not rows:
        return rows

    advantages: dict[tuple, float] = {}
    grouped: dict[tuple, dict[str, dict]] = {}
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        grouped.setdefault(key, {})[row["policy"]] = row

    for key, policy_rows in grouped.items():
        if "B1" in policy_rows and "B2" in policy_rows:
            b1_mean = float(policy_rows["B1"]["mean_response_time_mean"])
            b2_mean = float(policy_rows["B2"]["mean_response_time_mean"])
            advantages[key] = round(b1_mean - b2_mean, 6)

    output: list[dict] = []
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        row = dict(row)
        row["b2_advantage_vs_b1_mean"] = (
            advantages.get(key, "") if row["policy"] == "B2" else ""
        )
        output.append(row)

    return sorted(
        output,
        key=lambda row: (
            str(row["scenario"]),
            str(row["sweep_name"]),
            str(row["sweep_value"]),
            _numeric_sort_value(row["origin_delay"]),
            _numeric_sort_value(row["es_availability"]),
            _numeric_sort_value(row["neighbor_es_availability"]),
            _policy_sort_key(row["policy"]),
        ),
    )


def _sample_std(values: list[float], mean_value: float) -> float:
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return sqrt(variance)


def _numeric_sort_value(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _policy_sort_key(policy: str) -> int:
    return POLICY_ORDER.index(policy) if policy in POLICY_ORDER else len(POLICY_ORDER)
