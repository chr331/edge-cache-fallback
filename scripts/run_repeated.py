from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_repeated_trials  # noqa: E402
from edge_cache_sim.metrics import SUMMARY_COLUMNS  # noqa: E402
from edge_cache_sim.repeated import REPEATED_COLUMNS  # noqa: E402

ORIGIN_DELAYS = [40.0, 80.0, 120.0, 180.0, 240.0, 320.0]
ES_AVAILABILITIES = [0.45, 0.55, 0.65, 0.75, 0.82, 0.90]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated first-stage edge-cache fallback experiments."
    )
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--num-requests", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--skip-grid", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = SimulationConfig(num_requests=args.num_requests, seed=args.seed)

    repeated_rows: list[dict] = []
    trial_rows: list[dict] = []

    rows, trials = run_repeated_trials(base, args.trials, "baseline")
    repeated_rows.extend(rows)
    trial_rows.extend(trials)

    for origin_delay in ORIGIN_DELAYS:
        config = replace(
            base,
            scenario="origin_delay_repeated",
            origin_delay=origin_delay,
            seed=args.seed + int(origin_delay * 10),
        )
        rows, trials = run_repeated_trials(config, args.trials, "origin_delay", origin_delay)
        repeated_rows.extend(rows)
        trial_rows.extend(trials)

    for availability in ES_AVAILABILITIES:
        config = replace(
            base,
            scenario="es_availability_repeated",
            es_availability=availability,
            seed=args.seed + int(availability * 1000),
        )
        rows, trials = run_repeated_trials(
            config,
            args.trials,
            "es_availability",
            availability,
        )
        repeated_rows.extend(rows)
        trial_rows.extend(trials)

    grid_rows: list[dict] = []
    if not args.skip_grid:
        for origin_delay in ORIGIN_DELAYS:
            for availability in ES_AVAILABILITIES:
                config = replace(
                    base,
                    scenario="origin_delay_x_es_availability",
                    origin_delay=origin_delay,
                    es_availability=availability,
                    seed=args.seed + int(origin_delay * 10) + int(availability * 1000),
                )
                rows, _ = run_repeated_trials(
                    config,
                    args.trials,
                    "origin_delay_x_es_availability",
                )
                grid_rows.extend(rows)

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    _write_csv(results_dir / "repeated_summary.csv", repeated_rows, REPEATED_COLUMNS)

    if grid_rows:
        _write_csv(results_dir / "grid_summary.csv", grid_rows, REPEATED_COLUMNS)

    trial_columns = SUMMARY_COLUMNS + ["trial_index", "trial_seed", "sweep_name", "sweep_value"]
    _write_csv(results_dir / "repeated_trials.csv", trial_rows, trial_columns)

    print(_format_table(repeated_rows, REPEATED_COLUMNS))
    print(f"\nWrote {results_dir / 'repeated_summary.csv'}")
    print(f"Wrote {results_dir / 'repeated_trials.csv'}")
    if grid_rows:
        print(f"Wrote {results_dir / 'grid_summary.csv'}")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _format_table(rows: list[dict], columns: list[str]) -> str:
    table = [[str(row.get(column, "")) for column in columns] for row in rows]
    widths = [
        max(len(column), *(len(row[index]) for row in table))
        for index, column in enumerate(columns)
    ]
    lines = [" ".join(column.ljust(widths[index]) for index, column in enumerate(columns))]
    for row in table:
        lines.append(" ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


if __name__ == "__main__":
    main()
