from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write an experiment manifest JSON file.")
    parser.add_argument("--output-dir", default="results/phase1_b2_zipf")
    parser.add_argument("--phase", default="phase1_b2_zipf")
    parser.add_argument("--command", action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "phase": args.phase,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_branch": _git(["branch", "--show-current"]),
        "git_head": _git(["rev-parse", "HEAD"]),
        "git_status_short": _git(["status", "--short"]).splitlines(),
        "commands": args.command,
        "model_defaults": asdict(SimulationConfig()),
        "output_files": _output_files(output_dir),
        "notes": [
            "Phase 1.1 is still a Monte Carlo simulation, not a queueing or real congestion model.",
            "The origin_congestion key means origin-delay increase in this first-stage repository.",
            "PNG/TIFF files are generated for visual QA; SVG/PDF are the main figure artifacts.",
        ],
    }

    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {manifest_path}")


def _output_files(output_dir: Path) -> list[str]:
    return sorted(
        str(path.relative_to(output_dir)).replace("\\", "/")
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    )


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return ""
    return result.stdout.strip()


def _resolve_output_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
