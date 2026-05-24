# Research Log

## 2026-05-25

### Stage 1: Project scaffold

- Progress: Created the implementation plan for a first-stage edge-cache fallback-control simulation.
- Decision: Keep CSV as the reproducible data source, but use a formatted Excel workbook as the main reading artifact.
- Decision: Record stage-by-stage progress in this log so each run explains what changed and what to inspect.
- Next step: Implement the Monte Carlo simulation for B0, B1, and B2.

### Stage 2: Simulation model

- Progress: Added the first Monte Carlo model for local ES recovery, neighbor fallback, and origin fallback.
- Policy definitions: B0 falls back directly to origin; B1 tries neighbor ES first; B2 compares expected neighbor delay with origin delay before choosing.
- Limitation: This version does not model queues, congestion, request arrivals, or service capacity. Those belong in a later SimPy-based stage if needed.
- Next step: Run the baseline experiment and inspect policy-level metrics.

### Stage 3: Result presentation

- Progress: Added a report-generation plan that turns `results/summary.csv` into `results/edge_cache_fallback_report.xlsx`.
- Decision: The Excel workbook should contain Overview, Parameters, Summary, and Charts sheets.
- Result: Baseline output was generated with three policies. Mean response time was about 101.247 for B0, 45.214 for B1, and 45.170 for B2.
- Result: Origin-free completion rate was about 0.5503 for B0, 0.9790 for B1, and 0.9788 for B2.
- Interpretation: In this baseline, neighbor fallback greatly reduces origin access and response time. B2 is close to B1 because the selected parameters make neighbor search clearly worthwhile.
- Next step: Add parameter sweeps for origin delay and ES availability to find cases where B2 differs more clearly from B1.
