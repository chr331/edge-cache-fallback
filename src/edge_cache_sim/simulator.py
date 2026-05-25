"""Monte Carlo simulator for B0/B1/B2 fallback policies."""

from __future__ import annotations

from math import comb

import numpy as np

from .config import SimulationConfig
from .metrics import summarize_runs

POLICY_ORDER = ("B0", "B1", "B2")


def run_scenario(config: SimulationConfig) -> tuple[list[dict], list[dict]]:
    raw_rows: list[dict] = []
    summary_rows: list[dict] = []

    for offset, policy in enumerate(POLICY_ORDER):
        policy_rows = run_policy(policy, config, seed=config.seed + offset)
        raw_rows.extend(policy_rows)
        summary_rows.append(summarize_runs(policy_rows, config))

    return summary_rows, raw_rows


def run_policy(policy: str, config: SimulationConfig, seed: int | None = None) -> list[dict]:
    if policy not in POLICY_ORDER:
        raise ValueError(f"Unsupported policy: {policy}")

    rng = np.random.default_rng(config.seed if seed is None else seed)
    requests = _zipf_requests(config, rng)
    rows = []

    for index, content_id in enumerate(requests):
        local_chunks = rng.binomial(config.local_es_count, config.local_es_availability)
        local_success = local_chunks >= config.k

        if local_success:
            response_time = _with_jitter(config.local_recovery_delay, rng)
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=int(content_id),
                    response_time=response_time,
                    origin_used=False,
                    neighbor_attempted=False,
                    neighbor_failed=False,
                    completion="local",
                )
            )
            continue

        if policy == "B0":
            rows.append(
                _origin_row(config, policy, index, int(content_id), rng, "origin_after_local")
            )
            continue

        if policy == "B2" and not _should_try_neighbor(config):
            rows.append(
                _origin_row(config, policy, index, int(content_id), rng, "b2_origin_choice")
            )
            continue

        neighbor_chunks = rng.binomial(
            config.neighbor_group_size,
            config.effective_neighbor_es_availability,
        )
        neighbor_success = neighbor_chunks >= config.k

        if neighbor_success:
            response_time = _with_jitter(
                config.local_probe_delay + config.neighbor_recovery_delay,
                rng,
            )
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=int(content_id),
                    response_time=response_time,
                    origin_used=False,
                    neighbor_attempted=True,
                    neighbor_failed=False,
                    completion="neighbor",
                )
            )
        else:
            response_time = _with_jitter(
                config.local_probe_delay + config.neighbor_probe_delay + config.origin_delay,
                rng,
            )
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=int(content_id),
                    response_time=response_time,
                    origin_used=True,
                    neighbor_attempted=True,
                    neighbor_failed=True,
                    completion="origin_after_neighbor",
                )
            )

    return rows


def _zipf_requests(config: SimulationConfig, rng: np.random.Generator) -> np.ndarray:
    ranks = np.arange(1, config.num_contents + 1)
    weights = ranks.astype(float) ** (-config.zipf_alpha)
    probabilities = weights / weights.sum()
    return rng.choice(ranks, size=config.num_requests, p=probabilities)


def _should_try_neighbor(config: SimulationConfig) -> bool:
    success_probability = _recovery_probability(
        node_count=config.neighbor_group_size,
        availability=config.effective_neighbor_es_availability,
        k=config.k,
    )
    expected_neighbor_delay = (
        success_probability * config.neighbor_recovery_delay
        + (1.0 - success_probability) * (config.neighbor_probe_delay + config.origin_delay)
    )
    return expected_neighbor_delay <= config.origin_delay


def _recovery_probability(node_count: int, availability: float, k: int) -> float:
    return sum(
        comb(node_count, chunks)
        * (availability**chunks)
        * ((1.0 - availability) ** (node_count - chunks))
        for chunks in range(k, node_count + 1)
    )


def _origin_row(
    config: SimulationConfig,
    policy: str,
    request_id: int,
    content_id: int,
    rng: np.random.Generator,
    completion: str,
) -> dict:
    response_time = _with_jitter(config.local_probe_delay + config.origin_delay, rng)
    return _row(
        config=config,
        policy=policy,
        request_id=request_id,
        content_id=content_id,
        response_time=response_time,
        origin_used=True,
        neighbor_attempted=False,
        neighbor_failed=False,
        completion=completion,
    )


def _row(
    config: SimulationConfig,
    policy: str,
    request_id: int,
    content_id: int,
    response_time: float,
    origin_used: bool,
    neighbor_attempted: bool,
    neighbor_failed: bool,
    completion: str,
) -> dict:
    return {
        "scenario": config.scenario,
        "policy": policy,
        "request_id": request_id,
        "content_id": content_id,
        "response_time": round(float(response_time), 3),
        "origin_used": origin_used,
        "neighbor_attempted": neighbor_attempted,
        "neighbor_failed": neighbor_failed,
        "completion": completion,
        "zipf_alpha": config.zipf_alpha,
        "es_availability": config.es_availability,
        "local_es_availability": config.local_es_availability,
        "neighbor_es_availability": config.effective_neighbor_es_availability,
        "origin_delay": config.origin_delay,
        "local_es_count": config.local_es_count,
        "neighbor_group_size": config.neighbor_group_size,
        "k": config.k,
    }


def _with_jitter(base_delay: float, rng: np.random.Generator) -> float:
    """Add a small positive-skew delay so per-request latency is less deterministic."""
    return max(1.0, base_delay + rng.gamma(shape=2.0, scale=2.5))
