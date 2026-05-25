"""Metric helpers for aggregate simulation outputs."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


SUMMARY_COLUMNS = [
    "scenario",
    "policy",
    "mean_response_time",
    "p95_response_time",
    "origin_free_rate",
    "neighbor_failure_rate",
    "zipf_alpha",
    "es_availability",
    "local_es_availability",
    "neighbor_es_availability",
    "origin_delay",
    "local_es_count",
    "neighbor_group_size",
    "k",
]


def summarize_runs(rows: Iterable[dict], config) -> dict:
    rows = list(rows)
    response_times = np.array([row["response_time"] for row in rows], dtype=float)
    neighbor_attempts = sum(1 for row in rows if row["neighbor_attempted"])
    neighbor_failures = sum(1 for row in rows if row["neighbor_failed"])
    origin_uses = sum(1 for row in rows if row["origin_used"])

    return {
        "scenario": config.scenario,
        "policy": rows[0]["policy"],
        "mean_response_time": round(float(response_times.mean()), 3),
        "p95_response_time": round(float(np.percentile(response_times, 95)), 3),
        "origin_free_rate": round(float(1.0 - origin_uses / len(rows)), 4),
        "neighbor_failure_rate": round(
            float(neighbor_failures / neighbor_attempts) if neighbor_attempts else 0.0,
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
    }
