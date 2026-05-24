"""Metric helpers for aggregate simulation outputs."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


SUMMARY_COLUMNS = [
    "scenario",
    "policy",
    "mean_response_time",
    "p95_response_time",
    "origin_free_rate",
    "neighbor_failure_rate",
    "zipf_alpha",
    "es_availability",
    "origin_delay",
    "local_es_count",
    "neighbor_group_size",
    "k",
]


def summarize_runs(rows: Iterable[dict], config) -> dict:
    frame = pd.DataFrame(rows)
    neighbor_attempts = frame["neighbor_attempted"].sum()
    neighbor_failures = frame["neighbor_failed"].sum()

    return {
        "scenario": config.scenario,
        "policy": frame["policy"].iloc[0],
        "mean_response_time": round(float(frame["response_time"].mean()), 3),
        "p95_response_time": round(float(np.percentile(frame["response_time"], 95)), 3),
        "origin_free_rate": round(float(1.0 - frame["origin_used"].mean()), 4),
        "neighbor_failure_rate": round(
            float(neighbor_failures / neighbor_attempts) if neighbor_attempts else 0.0,
            4,
        ),
        "zipf_alpha": config.zipf_alpha,
        "es_availability": config.es_availability,
        "origin_delay": config.origin_delay,
        "local_es_count": config.local_es_count,
        "neighbor_group_size": config.neighbor_group_size,
        "k": config.k,
    }
