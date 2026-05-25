# Edge Cache Fallback Simulation

This repository contains a first-stage Monte Carlo simulation for fallback-control policies in low-trust edge-cache environments.

## Policies

- `B0`: if local edge servers cannot recover the requested content, fall back directly to the origin server.
- `B1`: if local recovery fails, search neighboring cooperative edge servers first, then fall back to origin if neighbor recovery fails.
- `B2`: if local recovery fails, compare the expected neighbor-search delay with direct origin delay, then choose the lower expected-delay action.

## Baseline Parameters

The default first-stage experiment uses these baseline values:

| Parameter | Value |
| --- | ---: |
| `scenario` | `baseline` |
| `num_contents` | `500` |
| `num_requests` | `10000` |
| `zipf_alpha` | `1.1` |
| `es_availability` | `0.82` |
| `neighbor_es_availability` | same as `es_availability` unless overridden |
| `origin_delay` | `180.0` |
| `local_es_count` | `3` |
| `neighbor_group_size` | `5` |
| `k` | `3` |
| `local_probe_delay` | `12.0` |
| `neighbor_probe_delay` | `28.0` |
| `local_recovery_delay` | `18.0` |
| `neighbor_recovery_delay` | `48.0` |
| `seed` | `20260525` |

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
python scripts\run_scenarios.py
python scripts\run_repeated.py
python scripts\run_memo_sweep.py
python scripts\build_figures.py
python scripts\build_report.py
```

For a faster development check:

```powershell
python scripts\run_scenarios.py --trials 3 --num-requests 1000
python scripts\run_repeated.py --trials 3 --num-requests 1000
```

## Outputs

- `results/summary.csv`: baseline summary with one row per policy.
- `results/sweep_summary.csv`: origin-delay and ES-availability sensitivity results.
- `results/scenario_summary.csv`: repeated-trial results for the formal steady, low-reliability-neighbor, and origin-delay-increase scenarios. The internal key `origin_congestion` is kept only for compatibility.
- `results/scenario_trials.csv`: per-trial policy summaries used to build the formal scenario statistics.
- `results/repeated_summary.csv`: repeated-trial means, standard errors, and 95% confidence intervals.
- `results/grid_summary.csv`: two-dimensional `origin_delay x neighbor_es_availability` repeated sweep.
- `results/memo_heatmap_summary.csv`: memo-specific sensitivity grid aligned with the formal scenario parameters.
- `results/repeated_trials.csv`: per-trial policy summaries used to build repeated statistics.
- `results/figures/`: Nature-style static figures exported as SVG, PDF, PNG, and TIFF.
- `results/edge_cache_fallback_report.xlsx`: formatted local workbook for reading.
- `memo/phase1_progress_memo_ja.tex`: two-page Japanese progress memo source for Ueyama-sensei.
- `phase1_results.ch.md` and `phase1_results.ja.md`: bilingual first-stage result interpretation.
- `research_log.md`: language-specific research-log index.

## CSV Schema

The baseline summary uses these fields:

- `scenario`
- `policy`
- `mean_response_time`
- `p95_response_time`
- `origin_free_rate`
- `neighbor_failure_rate`
- `zipf_alpha`
- `es_availability`
- `local_es_availability`
- `neighbor_es_availability`
- `origin_delay`
- `local_es_count`
- `neighbor_group_size`
- `k`

The repeated summary adds:

- `trial_count`
- `sweep_name`
- `sweep_value`
- metric columns ending in `_mean`, `_std`, `_stderr`, `_ci95_low`, and `_ci95_high`
- `b2_advantage_vs_b1_mean`

## Validate

```powershell
python -m unittest discover -s tests
```

## Scope

The current model intentionally stays simple and should be read as a preliminary Monte Carlo simulation. It does not yet model queueing, congestion, request arrivals, service capacity, online trust estimation, or real CDN traces. Those extensions are planned after the first-stage scenario evidence is stable.
