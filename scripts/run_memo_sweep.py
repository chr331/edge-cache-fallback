from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_repeated_trials  # noqa: E402
from edge_cache_sim.memo_sweep import (  # noqa: E402
    MEMO_NEIGHBOR_ES_AVAILABILITIES,
    MEMO_ORIGIN_DELAYS,
    MEMO_SWEEP_NAME,
    memo_sweep_configs,
)
from edge_cache_sim.repeated import REPEATED_COLUMNS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the memo-specific sensitivity grid for the phase 1 heatmap."
    )
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--num-requests", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260525)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = SimulationConfig(num_requests=args.num_requests, seed=args.seed)

    rows: list[dict] = []
    for config in memo_sweep_configs(base):
        summary_rows, _ = run_repeated_trials(config, args.trials, MEMO_SWEEP_NAME)
        rows.extend(summary_rows)

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "memo_heatmap_summary.csv"
    _write_csv(output_path, rows, REPEATED_COLUMNS)

    print(f"Wrote {output_path}")
    print(
        "Coverage: "
        f"neighbor_es_availability={list(MEMO_NEIGHBOR_ES_AVAILABILITIES)}, "
        f"origin_delay={list(MEMO_ORIGIN_DELAYS)}"
    )


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
