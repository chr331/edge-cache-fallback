from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import PercentFormatter

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

mpl.rcParams.update(
    {
        "pdf.fonttype": 42,
        "font.size": 7.5,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.75,
        "axes.edgecolor": "#262626",
        "axes.labelcolor": "#262626",
        "xtick.color": "#262626",
        "ytick.color": "#262626",
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

ROOT = Path(__file__).resolve().parents[1]

POLICY_ORDER = ["B0", "B1", "B2"]
SCENARIO_ORDER = ["steady", "low_reliability_neighbor", "origin_congestion"]
SCENARIO_LABELS = {
    "steady": "Steady",
    "low_reliability_neighbor": "Low-reliability\nneighbor",
    "origin_congestion": "Origin delay\nincrease",
}
POLICY_COLORS = {
    "B0": "#4C78A8",
    "B1": "#F58518",
    "B2": "#54A24B",
}
ADVANTAGE_CMAP = LinearSegmentedColormap.from_list(
    "b2_advantage",
    ["#B64342", "#F7F7F7", "#2E9E44"],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build publication-style figures from Phase 1 result CSV files."
    )
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--figures-dir", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_dir = _resolve_path(args.results_dir)
    figure_dir = (
        _resolve_path(args.figures_dir)
        if args.figures_dir
        else results_dir / "figures"
    )
    figure_dir.mkdir(parents=True, exist_ok=True)

    scenario_rows = _read_csv_optional(results_dir / "scenario_summary.csv")
    if scenario_rows:
        _plot_scenario_metric(
            scenario_rows,
            metric="mean_response_time",
            ylabel="Mean response time (ms)",
            title="Mean response time across formal scenarios",
            filename="fig_phase1_b2zipf_scenario_mean_response_time",
            figure_dir=figure_dir,
        )
        _plot_scenario_metric(
            scenario_rows,
            metric="p95_response_time",
            ylabel="p95 response time (ms)",
            title="Tail response time across formal scenarios",
            filename="fig_phase1_b2zipf_scenario_p95_response_time",
            figure_dir=figure_dir,
        )
        _plot_low_reliability_rates(scenario_rows, figure_dir)

    neighbor_origin_rows = _first_existing_csv(
        results_dir,
        [
            "neighbor_origin_grid_summary.csv",
            "memo_heatmap_summary.csv",
            "grid_summary.csv",
        ],
    )
    if neighbor_origin_rows:
        _plot_b2_advantage_heatmap(
            neighbor_origin_rows,
            x_column="origin_delay",
            y_column="neighbor_es_availability",
            xlabel="Origin delay (ms)",
            ylabel="Neighbor ES availability",
            title="B2 advantage across origin cost and neighbor reliability",
            filename="fig_phase1_b2zipf_neighbor_origin_heatmap",
            figure_dir=figure_dir,
        )

    zipf_rows = _read_csv_optional(results_dir / "zipf_sensitivity_summary.csv")
    if zipf_rows:
        _plot_b2_advantage_heatmap(
            zipf_rows,
            x_column="neighbor_cache_rank_gamma",
            y_column="zipf_alpha",
            xlabel="Neighbor cache rank gamma",
            ylabel="Zipf alpha",
            title="B2 advantage under Zipf/cache sensitivity",
            filename="fig_phase1_b2zipf_zipf_cache_heatmap",
            figure_dir=figure_dir,
        )

    rank_rows = _read_csv_optional(results_dir / "rank_bucket_summary.csv")
    if rank_rows:
        _plot_rank_bucket_choice(rank_rows, figure_dir)

    print(f"Wrote figures to {figure_dir}")


def _plot_scenario_metric(
    rows: list[dict[str, str]],
    *,
    metric: str,
    ylabel: str,
    title: str,
    filename: str,
    figure_dir: Path,
) -> None:
    scenario_rows = [
        row
        for row in rows
        if row.get("sweep_name") == "formal_scenario"
        and row.get("scenario") in SCENARIO_ORDER
    ]
    by_key = {(row["scenario"], row["policy"]): row for row in scenario_rows}
    missing = [
        f"{scenario}/{policy}"
        for scenario in SCENARIO_ORDER
        for policy in POLICY_ORDER
        if (scenario, policy) not in by_key
    ]
    if missing:
        raise ValueError(f"Missing scenario rows: {', '.join(missing)}")

    fig, ax = plt.subplots(figsize=(5.25, 2.85), constrained_layout=True)
    x = np.arange(len(SCENARIO_ORDER))
    width = 0.23

    for policy_index, policy in enumerate(POLICY_ORDER):
        offset = (policy_index - 1) * width
        values = np.array(
            [_metric_value(by_key[(scenario, policy)], metric) for scenario in SCENARIO_ORDER]
        )
        lows = np.array(
            [
                _metric_ci_value(by_key[(scenario, policy)], metric, "low", values[index])
                for index, scenario in enumerate(SCENARIO_ORDER)
            ]
        )
        highs = np.array(
            [
                _metric_ci_value(by_key[(scenario, policy)], metric, "high", values[index])
                for index, scenario in enumerate(SCENARIO_ORDER)
            ]
        )
        yerr = np.vstack([values - lows, highs - values])
        ax.bar(
            x + offset,
            values,
            width=width,
            yerr=yerr,
            color=POLICY_COLORS[policy],
            edgecolor="#262626",
            linewidth=0.55,
            error_kw={"elinewidth": 0.7, "capthick": 0.7, "capsize": 2.5},
            label=policy,
        )

    ax.set_xticks(x, [SCENARIO_LABELS[scenario] for scenario in SCENARIO_ORDER])
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.legend(title="Policy", ncols=3, loc="upper left")
    ax.set_axisbelow(True)

    _save_figure(fig, figure_dir, filename)


def _plot_low_reliability_rates(rows: list[dict[str, str]], figure_dir: Path) -> None:
    scenario_rows = [
        row
        for row in rows
        if row.get("scenario") == "low_reliability_neighbor"
        and row.get("sweep_name") == "formal_scenario"
    ]
    by_policy = {row["policy"]: row for row in scenario_rows}
    metrics = [
        ("origin_free_rate", "Origin-free\ncompletion"),
        ("neighbor_attempt_rate", "Neighbor\nattempt"),
        ("neighbor_failure_rate", "Neighbor\nfailure"),
    ]

    fig, ax = plt.subplots(figsize=(4.35, 2.75), constrained_layout=True)
    x = np.arange(len(metrics))
    width = 0.23

    for policy_index, policy in enumerate(POLICY_ORDER):
        if policy not in by_policy:
            raise ValueError(f"Missing low-reliability row for {policy}")
        row = by_policy[policy]
        offset = (policy_index - 1) * width
        values = np.array([_metric_value(row, metric) for metric, _ in metrics])
        lows = np.array(
            [
                _metric_ci_value(row, metric, "low", values[index])
                for index, (metric, _) in enumerate(metrics)
            ]
        )
        highs = np.array(
            [
                _metric_ci_value(row, metric, "high", values[index])
                for index, (metric, _) in enumerate(metrics)
            ]
        )
        yerr = np.vstack([values - lows, highs - values])
        ax.bar(
            x + offset,
            values,
            width=width,
            yerr=yerr,
            color=POLICY_COLORS[policy],
            edgecolor="#262626",
            linewidth=0.55,
            error_kw={"elinewidth": 0.7, "capthick": 0.7, "capsize": 2.5},
            label=policy,
        )

    ax.set_xticks(x, [label for _, label in metrics])
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    ax.set_ylabel("Rate")
    ax.set_title("Low-reliability neighbor outcomes", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.legend(title="Policy", ncols=3, loc="upper left")
    ax.set_axisbelow(True)

    _save_figure(fig, figure_dir, "fig_phase1_b2zipf_low_neighbor_rates")


def _plot_b2_advantage_heatmap(
    rows: list[dict[str, str]],
    *,
    x_column: str,
    y_column: str,
    xlabel: str,
    ylabel: str,
    title: str,
    filename: str,
    figure_dir: Path,
) -> None:
    b2_rows = [
        row
        for row in rows
        if row.get("policy") == "B2" and row.get("b2_advantage_vs_b1_mean") not in {"", None}
    ]
    if not b2_rows:
        raise ValueError(f"No B2 rows available for {filename}")

    x_values = sorted({_float(row[x_column]) for row in b2_rows})
    y_values = sorted({_float(row[y_column]) for row in b2_rows})
    matrix = np.full((len(y_values), len(x_values)), np.nan)
    for row in b2_rows:
        y_index = y_values.index(_float(row[y_column]))
        x_index = x_values.index(_float(row[x_column]))
        matrix[y_index, x_index] = _float(row["b2_advantage_vs_b1_mean"])

    max_abs = float(np.nanmax(np.abs(matrix)))
    max_abs = max(max_abs, 1.0)
    norm = TwoSlopeNorm(vcenter=0.0, vmin=-max_abs, vmax=max_abs)

    fig, ax = plt.subplots(figsize=(4.85, 3.15), constrained_layout=True)
    image = ax.imshow(matrix, cmap=ADVANTAGE_CMAP, norm=norm, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(len(x_values)), [_format_axis_value(value) for value in x_values])
    ax.set_yticks(np.arange(len(y_values)), [_format_axis_value(value) for value in y_values])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold")

    for y_index, _ in enumerate(y_values):
        for x_index, _ in enumerate(x_values):
            value = matrix[y_index, x_index]
            text_color = "white" if abs(value) > max_abs * 0.55 else "#262626"
            ax.text(
                x_index,
                y_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=6.5,
                color=text_color,
            )

    cbar = fig.colorbar(image, ax=ax, shrink=0.88)
    cbar.set_label("B1 mean - B2 mean (ms)")
    ax.text(
        0.0,
        -0.27,
        "Positive values mean B2 is faster than B1.",
        transform=ax.transAxes,
        fontsize=6.8,
        color="#4D4D4D",
    )

    _save_figure(fig, figure_dir, filename)


def _plot_rank_bucket_choice(rows: list[dict[str, str]], figure_dir: Path) -> None:
    rows = sorted(rows, key=lambda row: int(float(row["rank_bucket_order"])))
    labels = [row["rank_bucket_label"] for row in rows]
    values = np.array([_float(row["b2_neighbor_choice_rate_mean"]) for row in rows])
    lows = np.array([_float(row["b2_neighbor_choice_rate_ci95_low"]) for row in rows])
    highs = np.array([_float(row["b2_neighbor_choice_rate_ci95_high"]) for row in rows])
    yerr = np.vstack([values - lows, highs - values])

    fig, ax = plt.subplots(figsize=(3.9, 2.65), constrained_layout=True)
    x = np.arange(len(rows))
    ax.bar(
        x,
        values,
        yerr=yerr,
        color="#54A24B",
        edgecolor="#262626",
        linewidth=0.55,
        error_kw={"elinewidth": 0.7, "capthick": 0.7, "capsize": 2.5},
    )
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    ax.set_ylabel("B2 neighbor choice rate")
    ax.set_title("B2 chooses neighbors mainly for hot content", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.set_axisbelow(True)

    _save_figure(fig, figure_dir, "fig_phase1_b2zipf_rank_bucket_choice")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_csv_optional(path: Path) -> list[dict[str, str]]:
    return _read_csv(path) if path.exists() else []


def _first_existing_csv(results_dir: Path, filenames: list[str]) -> list[dict[str, str]]:
    for filename in filenames:
        path = results_dir / filename
        if path.exists():
            return _read_csv(path)
    return []


def _metric_value(row: dict[str, str], metric: str) -> float:
    return _float(row.get(f"{metric}_mean", row.get(metric, "0")))


def _metric_ci_value(row: dict[str, str], metric: str, side: str, fallback: float) -> float:
    key = f"{metric}_ci95_{side}"
    return _float(row[key]) if key in row and row[key] != "" else fallback


def _float(value: str | float | int) -> float:
    return float(value)


def _format_axis_value(value: float) -> str:
    if abs(value) >= 10:
        return f"{value:.0f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _save_figure(fig: plt.Figure, figure_dir: Path, filename: str) -> None:
    base = figure_dir / filename
    fig.savefig(f"{base}.svg", bbox_inches="tight")
    fig.savefig(f"{base}.pdf", bbox_inches="tight")
    fig.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{base}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
