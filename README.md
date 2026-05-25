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
python scripts\build_report.py
```

## Outputs

- `results/summary.csv`: baseline summary with one row per policy.
- `results/sweep_summary.csv`: origin-delay and ES-availability sensitivity results.
- `results/edge_cache_fallback_report.xlsx`: formatted local workbook for reading.
- `research_log.md`: stage-by-stage research notes.

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
- `origin_delay`
- `local_es_count`
- `neighbor_group_size`
- `k`

## Validate

```powershell
python -m unittest discover -s tests
```

## Scope

The current model intentionally stays simple. It does not yet model queueing, congestion, request arrivals, service capacity, online trust estimation, or real CDN traces. Those extensions are planned after the baseline fallback logic and parameter sweeps are stable.
