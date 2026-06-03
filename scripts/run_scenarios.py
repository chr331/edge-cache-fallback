from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import (  # noqa: E402
    SCENARIO_ORDER,
    SimulationConfig,
    formal_scenarios,
    run_repeated_trials,
)
from edge_cache_sim.simulator import POLICY_ORDER  # noqa: E402
from edge_cache_sim.metrics import SUMMARY_COLUMNS  # noqa: E402
from edge_cache_sim.repeated import REPEATED_COLUMNS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated trials for the three formal phase-1 scenarios."
    )
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--num-requests", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--output-dir", default="results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = SimulationConfig(num_requests=args.num_requests, seed=args.seed)

    summary_rows: list[dict] = []
    trial_rows: list[dict] = []
    for config in formal_scenarios(base):
        rows, trials = run_repeated_trials(
            config,
            trials=args.trials,
            sweep_name="formal_scenario",
            sweep_value=config.scenario,
        )
        summary_rows.extend(rows)
        trial_rows.extend(trials)

    summary_rows = _order_rows(summary_rows)
    trial_rows = _order_rows(trial_rows)

    results_dir = _resolve_output_dir(args.output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(results_dir / "scenario_summary.csv", summary_rows, REPEATED_COLUMNS)

    trial_columns = SUMMARY_COLUMNS + ["trial_index", "trial_seed", "sweep_name", "sweep_value"]
    _write_csv(results_dir / "scenario_trials.csv", trial_rows, trial_columns)

    print(_format_table(summary_rows, REPEATED_COLUMNS))
    print(f"\nWrote {results_dir / 'scenario_summary.csv'}")
    print(f"Wrote {results_dir / 'scenario_trials.csv'}")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


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


def _order_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            SCENARIO_ORDER.index(row["scenario"])
            if row["scenario"] in SCENARIO_ORDER
            else len(SCENARIO_ORDER),
            POLICY_ORDER.index(row["policy"])
            if row["policy"] in POLICY_ORDER
            else len(POLICY_ORDER),
            int(row.get("trial_index", 0)),
        ),
    )


if __name__ == "__main__":
    main()
