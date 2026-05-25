"""Memo-focused sensitivity sweep definitions."""

from __future__ import annotations

from dataclasses import replace

from .config import SimulationConfig

MEMO_LOCAL_ES_AVAILABILITY = 0.82
MEMO_NEIGHBOR_ES_AVAILABILITIES = (0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82)
MEMO_ORIGIN_DELAYS = (80.0, 120.0, 180.0, 240.0, 320.0)
MEMO_SWEEP_NAME = "memo_neighbor_availability_x_origin_delay"


def memo_sweep_configs(base: SimulationConfig) -> list[SimulationConfig]:
    """Return the memo sensitivity grid aligned with the formal scenarios."""
    configs: list[SimulationConfig] = []
    for origin_delay in MEMO_ORIGIN_DELAYS:
        for neighbor_availability in MEMO_NEIGHBOR_ES_AVAILABILITIES:
            configs.append(
                replace(
                    base,
                    scenario=MEMO_SWEEP_NAME,
                    es_availability=MEMO_LOCAL_ES_AVAILABILITY,
                    neighbor_es_availability=neighbor_availability,
                    origin_delay=origin_delay,
                    seed=(
                        base.seed
                        + int(origin_delay * 10)
                        + int(neighbor_availability * 1000)
                    ),
                )
            )
    return configs
