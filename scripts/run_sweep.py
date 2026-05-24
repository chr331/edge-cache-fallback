from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_scenario  # noqa: E402
from edge_cache_sim.metrics import SUMMARY_COLUMNS  # noqa: E402

ORIGIN_DELAYS = [40.0, 80.0, 120.0, 180.0, 240.0, 320.0]
ES_AVAILABILITIES = [0.45, 0.55, 0.65, 0.75, 0.82, 0.90]


def main() -> None:
    base = SimulationConfig()
    rows: list[dict] = []

    for origin_delay in ORIGIN_DELAYS:
        config = replace(
            base,
            scenario="origin_delay_sweep",
            origin_delay=origin_delay,
            seed=base.seed + int(origin_delay),
        )
        rows.extend(_run(config, "origin_delay", origin_delay))

    for es_availability in ES_AVAILABILITIES:
        config = replace(
            base,
            scenario="es_availability_sweep",
            es_availability=es_availability,
            seed=base.seed + int(es_availability * 1000),
        )
        rows.extend(_run(config, "es_availability", es_availability))

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    frame = pd.DataFrame(rows)
    column_order = SUMMARY_COLUMNS + ["sweep_name", "sweep_value", "b2_advantage_vs_b1"]
    frame = frame[column_order]
    frame.to_csv(results_dir / "sweep_summary.csv", index=False)

    print(frame.to_string(index=False))
    print(f"\nWrote {results_dir / 'sweep_summary.csv'}")


def _run(config: SimulationConfig, sweep_name: str, sweep_value: float) -> list[dict]:
    summary_rows, _ = run_scenario(config)
    frame = pd.DataFrame(summary_rows)
    b1_mean = float(frame.loc[frame["policy"] == "B1", "mean_response_time"].iloc[0])
    b2_mean = float(frame.loc[frame["policy"] == "B2", "mean_response_time"].iloc[0])
    b2_advantage = round(b1_mean - b2_mean, 3)

    rows = []
    for row in summary_rows:
        row = dict(row)
        row["sweep_name"] = sweep_name
        row["sweep_value"] = sweep_value
        row["b2_advantage_vs_b1"] = b2_advantage if row["policy"] == "B2" else ""
        rows.append(row)
    return rows


if __name__ == "__main__":
    main()
