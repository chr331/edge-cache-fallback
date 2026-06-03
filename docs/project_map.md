# Project Map

This repository is organized as a first-stage research simulation package. It keeps old
Phase 1 outputs in place and adds new versioned result batches for later updates.

## Start Here

| Path | Purpose |
| --- | --- |
| `README.md` | High-level project explanation, model scope, and quick navigation. |
| `docs/experiment_guide.md` | Step-by-step commands for running, testing, and interpreting Phase 1.1. |
| `docs/phase1_b2_zipf_report.md` | Detailed Phase 1.1 experiment report with embedded figures and reviewer-style interpretation. |
| `CHANGELOG.md` | Chronological record of project updates. |
| `src/edge_cache_sim/` | Simulation model, policy logic, scenarios, repeated-trial aggregation. |
| `scripts/` | Command-line entry points for experiments, figures, reports, and manifests. |
| `tests/` | Unit tests for policy behavior, Zipf/cache probabilities, and aggregation. |
| `results/` | Historical Phase 1 CSV and figure outputs. |
| `results/phase1_b2_zipf/` | Versioned Phase 1.1 outputs for request-level B2, Zipf/cache sensitivity, fallback-stage metrics, and the decision-boundary diagnostic scenario. |
| `memo/` and `overleaf/` | Japanese progress memo material and Overleaf-ready package. |

## Result Batch Rule

New experiment batches should use a named subdirectory under `results/`.

Recommended pattern:

```text
results/<phase_or_date>/
  manifest.json
  scenario_summary.csv
  scenario_trials.csv
  <sweep>_summary.csv
  figures/
    *.svg
    *.pdf
```

The manifest is the first file to check when a result directory feels unclear. It records
the command list, model defaults, git state at generation time, and generated output files.

## Tracked And Ignored Outputs

CSV, SVG, and PDF files are intended to be reviewable artifacts. PNG and TIFF files are
generated for visual QA and local preview; they are ignored by Git unless explicitly added
for a special reason.
