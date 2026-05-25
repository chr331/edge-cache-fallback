"""Formal first-stage scenario definitions."""

from __future__ import annotations

from dataclasses import replace

from .config import SimulationConfig

SCENARIO_ORDER = ("steady", "low_reliability_neighbor", "origin_congestion")


def formal_scenarios(base: SimulationConfig) -> list[SimulationConfig]:
    return [
        replace(
            base,
            scenario="steady",
            es_availability=0.82,
            neighbor_es_availability=0.82,
            origin_delay=180.0,
            seed=base.seed,
        ),
        replace(
            base,
            scenario="low_reliability_neighbor",
            es_availability=0.82,
            neighbor_es_availability=0.25,
            origin_delay=180.0,
            seed=base.seed + 10_000,
        ),
        replace(
            base,
            scenario="origin_congestion",
            es_availability=0.82,
            neighbor_es_availability=0.82,
            origin_delay=320.0,
            seed=base.seed + 20_000,
        ),
    ]
