from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_scenario  # noqa: E402
from edge_cache_sim.metrics import SUMMARY_COLUMNS  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run edge-cache fallback experiments.")
    parser.add_argument("--scenario", default="baseline")
    parser.add_argument("--num-requests", type=int, default=10_000)
    parser.add_argument("--zipf-alpha", type=float, default=1.1)
    parser.add_argument("--es-availability", type=float, default=0.82)
    parser.add_argument("--neighbor-es-availability", type=float, default=None)
    parser.add_argument("--origin-delay", type=float, default=180.0)
    parser.add_argument("--local-es-count", type=int, default=3)
    parser.add_argument("--neighbor-group-size", type=int, default=5)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--write-raw", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        scenario=args.scenario,
        num_requests=args.num_requests,
        zipf_alpha=args.zipf_alpha,
        es_availability=args.es_availability,
        neighbor_es_availability=args.neighbor_es_availability,
        origin_delay=args.origin_delay,
        local_es_count=args.local_es_count,
        neighbor_group_size=args.neighbor_group_size,
        k=args.k,
        seed=args.seed,
    )

    summary_rows, raw_rows = run_scenario(config)
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    _write_csv(results_dir / "summary.csv", summary_rows, SUMMARY_COLUMNS)

    if args.write_raw:
        _write_csv(results_dir / "raw_requests.csv", raw_rows, raw_rows[0].keys())

    print(_format_table(summary_rows, SUMMARY_COLUMNS))
    print(f"\nWrote {results_dir / 'summary.csv'}")
    if args.write_raw:
        print(f"Wrote {results_dir / 'raw_requests.csv'}")


def _write_csv(path: Path, rows: list[dict], fieldnames) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def _format_table(rows: list[dict], columns: list[str]) -> str:
    table = [[str(row[column]) for column in columns] for row in rows]
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
