"""Research-plan and diagnostic first-stage scenario definitions."""

from __future__ import annotations

from dataclasses import replace

from .config import SimulationConfig

SCENARIO_ORDER = (
    "steady",
    "low_reliability_neighbor",
    "origin_congestion",
    "decision_boundary_neighbor",
)


def formal_scenarios(base: SimulationConfig) -> list[SimulationConfig]:
    """Return the three research-plan scenarios plus one decision-boundary diagnostic."""
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
        replace(
            base,
            scenario="decision_boundary_neighbor",
            es_availability=0.82,
            neighbor_es_availability=0.20,
            origin_delay=80.0,
            seed=base.seed + 30_000,
        ),
    ]
