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

    for policy in POLICY_ORDER:
        policy_rows = run_policy(policy, config, seed=config.seed)
        raw_rows.extend(policy_rows)
        summary_rows.append(summarize_runs(policy_rows, config))

    return summary_rows, raw_rows


def run_policy(policy: str, config: SimulationConfig, seed: int | None = None) -> list[dict]:
    if policy not in POLICY_ORDER:
        raise ValueError(f"Unsupported policy: {policy}")

    base_seed = config.seed if seed is None else seed
    request_rng = np.random.default_rng(base_seed)
    local_rng = np.random.default_rng(base_seed + 1)
    neighbor_rng = np.random.default_rng(base_seed + 2)
    jitter_rng = np.random.default_rng(base_seed + 3)
    requests = _zipf_requests(config, request_rng)
    local_chunk_samples = local_rng.binomial(
        config.local_es_count,
        config.local_es_availability,
        size=config.num_requests,
    )
    jitter_samples = jitter_rng.gamma(shape=2.0, scale=2.5, size=config.num_requests)
    rows = []

    for index, content_id in enumerate(requests):
        content_rank = int(content_id)
        local_chunks = int(local_chunk_samples[index])
        missing_chunks = max(config.k - local_chunks, 0)
        cache_probability = neighbor_cache_probability(content_rank, config)
        chunk_probability = neighbor_chunk_probability(content_rank, config)
        neighbor_chunks = int(neighbor_rng.binomial(config.neighbor_group_size, chunk_probability))
        jitter = float(jitter_samples[index])

        if missing_chunks == 0:
            response_time = _with_jitter(config.local_recovery_delay, jitter)
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=content_rank,
                    local_chunks=local_chunks,
                    missing_chunks=missing_chunks,
                    neighbor_cache_probability=cache_probability,
                    neighbor_chunk_probability=chunk_probability,
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
                _origin_row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=content_rank,
                    local_chunks=local_chunks,
                    missing_chunks=missing_chunks,
                    neighbor_cache_probability=cache_probability,
                    neighbor_chunk_probability=chunk_probability,
                    jitter=jitter,
                    completion="origin_after_local",
                )
            )
            continue

        b2_success_probability = None
        b2_expected_neighbor_delay = None
        b2_neighbor_selected = False
        if policy == "B2":
            b2_success_probability = neighbor_recovery_probability(
                config=config,
                missing_chunks=missing_chunks,
                content_rank=content_rank,
            )
            b2_expected_neighbor_delay = expected_neighbor_delay(
                config=config,
                success_probability=b2_success_probability,
            )
            b2_neighbor_selected = should_try_neighbor(
                config=config,
                missing_chunks=missing_chunks,
                content_rank=content_rank,
            )

        if policy == "B2" and not b2_neighbor_selected:
            rows.append(
                _origin_row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=content_rank,
                    local_chunks=local_chunks,
                    missing_chunks=missing_chunks,
                    neighbor_cache_probability=cache_probability,
                    neighbor_chunk_probability=chunk_probability,
                    jitter=jitter,
                    completion="b2_origin_choice",
                    b2_neighbor_success_probability=b2_success_probability,
                    b2_expected_neighbor_delay=b2_expected_neighbor_delay,
                    b2_neighbor_selected=False,
                )
            )
            continue

        neighbor_success = neighbor_chunks >= missing_chunks

        if neighbor_success:
            response_time = _with_jitter(
                config.local_probe_delay + config.neighbor_recovery_delay,
                jitter,
            )
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=content_rank,
                    local_chunks=local_chunks,
                    missing_chunks=missing_chunks,
                    neighbor_cache_probability=cache_probability,
                    neighbor_chunk_probability=chunk_probability,
                    response_time=response_time,
                    origin_used=False,
                    neighbor_attempted=True,
                    neighbor_failed=False,
                    completion="neighbor",
                    b2_neighbor_success_probability=b2_success_probability,
                    b2_expected_neighbor_delay=b2_expected_neighbor_delay,
                    b2_neighbor_selected=b2_neighbor_selected,
                )
            )
        else:
            response_time = _with_jitter(
                config.local_probe_delay + config.neighbor_probe_delay + config.origin_delay,
                jitter,
            )
            rows.append(
                _row(
                    config=config,
                    policy=policy,
                    request_id=index,
                    content_id=content_rank,
                    local_chunks=local_chunks,
                    missing_chunks=missing_chunks,
                    neighbor_cache_probability=cache_probability,
                    neighbor_chunk_probability=chunk_probability,
                    response_time=response_time,
                    origin_used=True,
                    neighbor_attempted=True,
                    neighbor_failed=True,
                    completion="origin_after_neighbor",
                    b2_neighbor_success_probability=b2_success_probability,
                    b2_expected_neighbor_delay=b2_expected_neighbor_delay,
                    b2_neighbor_selected=b2_neighbor_selected,
                )
            )

    return rows


def zipf_rank_probabilities(num_contents: int, zipf_alpha: float) -> np.ndarray:
    ranks = np.arange(1, num_contents + 1)
    weights = ranks.astype(float) ** (-zipf_alpha)
    return weights / weights.sum()


def neighbor_cache_probability(content_rank: int, config: SimulationConfig) -> float:
    rank = max(1, int(content_rank))
    exponent = -config.zipf_alpha * config.neighbor_cache_rank_gamma
    probability = config.neighbor_cache_cold_prob + (
        config.neighbor_cache_hot_prob - config.neighbor_cache_cold_prob
    ) * (rank**exponent)
    return _clip_probability(probability)


def neighbor_chunk_probability(content_rank: int, config: SimulationConfig) -> float:
    return _clip_probability(
        config.effective_neighbor_es_availability
        * neighbor_cache_probability(content_rank, config)
    )


def neighbor_recovery_probability(
    config: SimulationConfig,
    missing_chunks: int,
    content_rank: int,
) -> float:
    if missing_chunks <= 0:
        return 1.0
    if missing_chunks > config.neighbor_group_size:
        return 0.0
    return _recovery_probability(
        node_count=config.neighbor_group_size,
        availability=neighbor_chunk_probability(content_rank, config),
        k=missing_chunks,
    )


def expected_neighbor_delay(config: SimulationConfig, success_probability: float) -> float:
    return (
        success_probability * config.neighbor_recovery_delay
        + (1.0 - success_probability) * (config.neighbor_probe_delay + config.origin_delay)
    )


def should_try_neighbor(
    config: SimulationConfig,
    missing_chunks: int | None = None,
    content_rank: int = 1,
) -> bool:
    if missing_chunks is None:
        missing_chunks = config.k
    success_probability = neighbor_recovery_probability(config, missing_chunks, content_rank)
    return expected_neighbor_delay(config, success_probability) <= config.origin_delay


def _zipf_requests(config: SimulationConfig, rng: np.random.Generator) -> np.ndarray:
    ranks = np.arange(1, config.num_contents + 1)
    probabilities = zipf_rank_probabilities(config.num_contents, config.zipf_alpha)
    return rng.choice(ranks, size=config.num_requests, p=probabilities)


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
    local_chunks: int,
    missing_chunks: int,
    neighbor_cache_probability: float,
    neighbor_chunk_probability: float,
    jitter: float,
    completion: str,
    b2_neighbor_success_probability: float | None = None,
    b2_expected_neighbor_delay: float | None = None,
    b2_neighbor_selected: bool = False,
) -> dict:
    response_time = _with_jitter(config.local_probe_delay + config.origin_delay, jitter)
    return _row(
        config=config,
        policy=policy,
        request_id=request_id,
        content_id=content_id,
        local_chunks=local_chunks,
        missing_chunks=missing_chunks,
        neighbor_cache_probability=neighbor_cache_probability,
        neighbor_chunk_probability=neighbor_chunk_probability,
        response_time=response_time,
        origin_used=True,
        neighbor_attempted=False,
        neighbor_failed=False,
        completion=completion,
        b2_neighbor_success_probability=b2_neighbor_success_probability,
        b2_expected_neighbor_delay=b2_expected_neighbor_delay,
        b2_neighbor_selected=b2_neighbor_selected,
    )


def _row(
    config: SimulationConfig,
    policy: str,
    request_id: int,
    content_id: int,
    local_chunks: int,
    missing_chunks: int,
    neighbor_cache_probability: float,
    neighbor_chunk_probability: float,
    response_time: float,
    origin_used: bool,
    neighbor_attempted: bool,
    neighbor_failed: bool,
    completion: str,
    b2_neighbor_success_probability: float | None = None,
    b2_expected_neighbor_delay: float | None = None,
    b2_neighbor_selected: bool = False,
) -> dict:
    return {
        "scenario": config.scenario,
        "policy": policy,
        "request_id": request_id,
        "content_id": content_id,
        "content_rank": content_id,
        "local_chunks": local_chunks,
        "missing_chunks": missing_chunks,
        "neighbor_cache_probability": round(float(neighbor_cache_probability), 6),
        "neighbor_chunk_probability": round(float(neighbor_chunk_probability), 6),
        "b2_neighbor_success_probability": (
            round(float(b2_neighbor_success_probability), 6)
            if b2_neighbor_success_probability is not None
            else ""
        ),
        "b2_expected_neighbor_delay": (
            round(float(b2_expected_neighbor_delay), 6)
            if b2_expected_neighbor_delay is not None
            else ""
        ),
        "b2_neighbor_selected": b2_neighbor_selected,
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
        "local_probe_delay": config.local_probe_delay,
        "neighbor_probe_delay": config.neighbor_probe_delay,
        "local_recovery_delay": config.local_recovery_delay,
        "neighbor_recovery_delay": config.neighbor_recovery_delay,
        "neighbor_cache_hot_prob": config.neighbor_cache_hot_prob,
        "neighbor_cache_cold_prob": config.neighbor_cache_cold_prob,
        "neighbor_cache_rank_gamma": config.neighbor_cache_rank_gamma,
        "seed": config.seed,
    }


def _clip_probability(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _with_jitter(base_delay: float, jitter: float) -> float:
    """Add a small positive-skew delay so per-request latency is less deterministic."""
    return max(1.0, base_delay + jitter)
