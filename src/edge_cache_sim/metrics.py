"""Metric helpers for aggregate simulation outputs."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


SUMMARY_COLUMNS = [
    "scenario",
    "policy",
    "mean_response_time",
    "p95_response_time",
    "fallback_mean_response_time",
    "fallback_p95_response_time",
    "origin_free_rate",
    "local_failure_rate",
    "neighbor_attempt_rate",
    "neighbor_skip_rate",
    "neighbor_failure_rate",
    "b2_neighbor_choice_rate",
    "zipf_alpha",
    "es_availability",
    "local_es_availability",
    "neighbor_es_availability",
    "origin_delay",
    "local_es_count",
    "neighbor_group_size",
    "k",
    "neighbor_cache_hot_prob",
    "neighbor_cache_cold_prob",
    "neighbor_cache_rank_gamma",
]


def summarize_runs(rows: Iterable[dict], config) -> dict:
    rows = list(rows)
    response_times = np.array([row["response_time"] for row in rows], dtype=float)
    fallback_rows = [row for row in rows if int(row["missing_chunks"]) > 0]
    fallback_response_times = np.array(
        [row["response_time"] for row in fallback_rows],
        dtype=float,
    )
    neighbor_attempts = sum(1 for row in rows if row["neighbor_attempted"])
    neighbor_failures = sum(1 for row in rows if row["neighbor_failed"])
    origin_uses = sum(1 for row in rows if row["origin_used"])
    local_failures = sum(1 for row in rows if int(row["missing_chunks"]) > 0)
    b2_decisions = [
        row
        for row in rows
        if row["policy"] == "B2" and int(row["missing_chunks"]) > 0
    ]
    b2_neighbor_choices = sum(1 for row in b2_decisions if row["b2_neighbor_selected"])

    return {
        "scenario": config.scenario,
        "policy": rows[0]["policy"],
        "mean_response_time": round(float(response_times.mean()), 3),
        "p95_response_time": round(float(np.percentile(response_times, 95)), 3),
        "fallback_mean_response_time": round(
            float(fallback_response_times.mean()) if len(fallback_response_times) else 0.0,
            3,
        ),
        "fallback_p95_response_time": round(
            float(np.percentile(fallback_response_times, 95))
            if len(fallback_response_times)
            else 0.0,
            3,
        ),
        "origin_free_rate": round(float(1.0 - origin_uses / len(rows)), 4),
        "local_failure_rate": round(float(local_failures / len(rows)), 4),
        "neighbor_attempt_rate": round(float(neighbor_attempts / len(rows)), 4),
        "neighbor_skip_rate": round(
            float((local_failures - neighbor_attempts) / local_failures)
            if local_failures
            else 0.0,
            4,
        ),
        "neighbor_failure_rate": round(
            float(neighbor_failures / neighbor_attempts) if neighbor_attempts else 0.0,
            4,
        ),
        "b2_neighbor_choice_rate": round(
            float(b2_neighbor_choices / len(b2_decisions)) if b2_decisions else 0.0,
            4,
        ),
        "zipf_alpha": config.zipf_alpha,
        "es_availability": config.es_availability,
        "local_es_availability": config.local_es_availability,
        "neighbor_es_availability": config.effective_neighbor_es_availability,
        "origin_delay": config.origin_delay,
        "local_es_count": config.local_es_count,
        "neighbor_group_size": config.neighbor_group_size,
        "k": config.k,
        "neighbor_cache_hot_prob": config.neighbor_cache_hot_prob,
        "neighbor_cache_cold_prob": config.neighbor_cache_cold_prob,
        "neighbor_cache_rank_gamma": config.neighbor_cache_rank_gamma,
    }
