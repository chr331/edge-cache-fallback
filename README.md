# Edge Cache Fallback Simulation

This repository contains a first-stage Monte Carlo simulation for fallback
control in low-trust edge-cache environments.

## Policies

- `B0`: local ES failure falls back directly to origin.
- `B1`: local ES failure searches neighboring cooperative ES first, then origin
  if neighbor recovery fails.
- `B2`: local ES failure compares expected neighbor-search delay and origin
  delay, then chooses the lower expected-delay action.

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run The Baseline Experiment

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
python scripts\build_report.py
```

Primary outputs:

- `results/summary.csv`: reproducible machine-readable summary.
- `results/sweep_summary.csv`: origin-delay and ES-availability sensitivity results.
- `results/edge_cache_fallback_report.xlsx`: formatted workbook for reading.
- `research_log.md`: stage-by-stage explanation of what changed and why.

## CSV Schema

The main experiment summary file is `results/summary.csv`.
It contains one row per policy with these fields:

- `scenario`
- `policy`
- `mean_response_time`
- `p95_response_time`
- `origin_free_rate`
- `neighbor_failure_rate`
- `zipf_alpha`
- `es_availability`
- `origin_delay`
- `local_es_count`
- `neighbor_group_size`
- `k`

## Validate

```powershell
python -m unittest discover -s tests
```

## Notes

The current model intentionally stays simple: it does not model queues,
congestion, request arrivals, or service capacity. Those can be added later
with SimPy once the baseline fallback logic is stable.
