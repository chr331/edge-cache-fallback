"""Configuration defaults for the first-stage Monte Carlo simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    scenario: str = "baseline"
    num_contents: int = 500
    num_requests: int = 10_000
    zipf_alpha: float = 1.1
    es_availability: float = 0.82
    origin_delay: float = 180.0
    local_es_count: int = 3
    neighbor_group_size: int = 5
    k: int = 3
    local_probe_delay: float = 12.0
    neighbor_probe_delay: float = 28.0
    local_recovery_delay: float = 18.0
    neighbor_recovery_delay: float = 48.0
    seed: int = 20260525
