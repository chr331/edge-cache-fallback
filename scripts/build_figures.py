from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

mpl.rcParams.update(
    {
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "axes.edgecolor": "#272727",
        "axes.labelcolor": "#272727",
        "xtick.color": "#272727",
        "ytick.color": "#272727",
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURE_DIR = RESULTS_DIR / "figures"

POLICY_ORDER = ["B0", "B1", "B2"]
POLICY_COLORS = {
    "B0": "#484878",
    "B1": "#7884B4",
    "B2": "#E4CCD8",
}
POLICY_MARKERS = {
    "B0": "o",
    "B1": "s",
    "B2": "^",
}
ADVANTAGE_CMAP = LinearSegmentedColormap.from_list(
    "b2_advantage",
    ["#B64342", "#F7F7F7", "#2E9E44"],
)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    repeated_rows = _read_csv(RESULTS_DIR / "repeated_summary.csv")
    grid_rows = _read_csv(RESULTS_DIR / "grid_summary.csv")

    _plot_baseline_bar(
        repeated_rows,
        metric="mean_response_time",
        ylabel="Mean response time (ms)",
        title="Baseline mean response time",
        filename="fig_phase1_baseline_mean_response_time",
    )
    _plot_baseline_bar(
        repeated_rows,
        metric="p95_response_time",
        ylabel="p95 response time (ms)",
        title="Baseline tail response time",
        filename="fig_phase1_baseline_p95_response_time",
    )
    _plot_sweep(
        repeated_rows,
        sweep_name="origin_delay",
        x_column="origin_delay",
        xlabel="Origin delay (ms)",
        title="Policy sensitivity to origin delay",
        filename="fig_phase1_origin_delay_sweep",
    )
    _plot_sweep(
        repeated_rows,
        sweep_name="es_availability",
        x_column="es_availability",
        xlabel="ES availability",
        title="Policy sensitivity to ES availability",
        filename="fig_phase1_es_availability_sweep",
    )
    _plot_b2_advantage_heatmap(grid_rows)

    print(f"Wrote figures to {FIGURE_DIR}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _plot_baseline_bar(
    rows: list[dict[str, str]],
    *,
    metric: str,
    ylabel: str,
    title: str,
    filename: str,
) -> None:
    baseline_rows = _policy_rows(
        row
        for row in rows
        if row["scenario"] == "baseline" and row["sweep_name"] == "baseline"
    )
    values = np.array([_float(row[f"{metric}_mean"]) for row in baseline_rows])
    lows = np.array([_float(row[f"{metric}_ci95_low"]) for row in baseline_rows])
    highs = np.array([_float(row[f"{metric}_ci95_high"]) for row in baseline_rows])
    yerr = np.vstack([values - lows, highs - values])

    fig, ax = plt.subplots(figsize=(3.35, 2.55), constrained_layout=True)
    x = np.arange(len(POLICY_ORDER))
    ax.bar(
        x,
        values,
        yerr=yerr,
        color=[POLICY_COLORS[policy] for policy in POLICY_ORDER],
        edgecolor="#272727",
        linewidth=0.7,
        error_kw={"elinewidth": 0.8, "capthick": 0.8, "capsize": 3},
    )
    ax.set_xticks(x, POLICY_ORDER)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.set_axisbelow(True)

    for xpos, value in zip(x, values):
        ax.text(xpos, value, f"{value:.1f}", ha="center", va="bottom", fontsize=7)

    _save_figure(fig, filename)


def _plot_sweep(
    rows: list[dict[str, str]],
    *,
    sweep_name: str,
    x_column: str,
    xlabel: str,
    title: str,
    filename: str,
) -> None:
    sweep_rows = [row for row in rows if row["sweep_name"] == sweep_name]

    fig, ax = plt.subplots(figsize=(4.4, 2.75), constrained_layout=True)
    for policy in POLICY_ORDER:
        policy_rows = sorted(
            [row for row in sweep_rows if row["policy"] == policy],
            key=lambda row: _float(row[x_column]),
        )
        x = np.array([_float(row[x_column]) for row in policy_rows])
        y = np.array([_float(row["mean_response_time_mean"]) for row in policy_rows])
        low = np.array(
            [_float(row["mean_response_time_ci95_low"]) for row in policy_rows]
        )
        high = np.array(
            [_float(row["mean_response_time_ci95_high"]) for row in policy_rows]
        )
        ax.plot(
            x,
            y,
            color=POLICY_COLORS[policy],
            marker=POLICY_MARKERS[policy],
            markersize=4,
            linewidth=1.5,
            label=policy,
        )
        ax.fill_between(x, low, high, color=POLICY_COLORS[policy], alpha=0.13, linewidth=0)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Mean response time (ms)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.5)
    ax.legend(title="Policy", ncols=3, loc="upper right")
    ax.set_axisbelow(True)

    _save_figure(fig, filename)


def _plot_b2_advantage_heatmap(rows: list[dict[str, str]]) -> None:
    b2_rows = [row for row in rows if row["policy"] == "B2"]
    origin_delays = sorted({_float(row["origin_delay"]) for row in b2_rows})
    availabilities = sorted({_float(row["es_availability"]) for row in b2_rows})

    matrix = np.full((len(availabilities), len(origin_delays)), np.nan)
    for row in b2_rows:
        y = availabilities.index(_float(row["es_availability"]))
        x = origin_delays.index(_float(row["origin_delay"]))
        matrix[y, x] = _float(row["b2_advantage_vs_b1_mean"])

    max_abs = float(np.nanmax(np.abs(matrix)))
    norm = TwoSlopeNorm(vcenter=0.0, vmin=-max_abs, vmax=max_abs)

    fig, ax = plt.subplots(figsize=(4.7, 3.1), constrained_layout=True)
    image = ax.imshow(matrix, cmap=ADVANTAGE_CMAP, norm=norm, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(len(origin_delays)), [f"{value:.0f}" for value in origin_delays])
    ax.set_yticks(
        np.arange(len(availabilities)),
        [f"{value:.2f}" for value in availabilities],
    )
    ax.set_xlabel("Origin delay (ms)")
    ax.set_ylabel("ES availability")
    ax.set_title("B2 advantage over B1", loc="left", fontweight="bold")

    for y_index, availability in enumerate(availabilities):
        for x_index, origin_delay in enumerate(origin_delays):
            value = matrix[y_index, x_index]
            text_color = "white" if abs(value) > max_abs * 0.55 else "#272727"
            ax.text(
                x_index,
                y_index,
                f"{value:.1f}",
                ha="center",
                va="center",
                fontsize=6.6,
                color=text_color,
            )

    cbar = fig.colorbar(image, ax=ax, shrink=0.86)
    cbar.set_label("B1 mean - B2 mean (ms)")
    ax.text(
        0.0,
        -0.28,
        "Positive values mean B2 is faster than B1.",
        transform=ax.transAxes,
        fontsize=7,
        color="#4D4D4D",
    )

    _save_figure(fig, "fig_phase1_b2_advantage_heatmap")


def _policy_rows(rows: object) -> list[dict[str, str]]:
    by_policy = {row["policy"]: row for row in rows}
    missing = [policy for policy in POLICY_ORDER if policy not in by_policy]
    if missing:
        raise ValueError(f"Missing policy rows: {', '.join(missing)}")
    return [by_policy[policy] for policy in POLICY_ORDER]


def _float(value: str) -> float:
    return float(value)


def _save_figure(fig: plt.Figure, filename: str) -> None:
    base = FIGURE_DIR / filename
    fig.savefig(f"{base}.svg", bbox_inches="tight")
    fig.savefig(f"{base}.pdf", bbox_inches="tight")
    fig.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{base}.tiff", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
