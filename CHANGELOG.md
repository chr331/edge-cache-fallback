# Changelog

All notable project updates are recorded here so that future result batches are easier
to audit.

## 2026-06-03: Phase 1.1 Request-Level B2 And Zipf Sensitivity

### Added

- Added `docs/project_map.md` to explain the repository layout, result-batch rule, and
  tracked versus ignored outputs.
- Added `docs/experiment_guide.md` with beginner-friendly commands, output-file
  descriptions, metric definitions, and scope limits for Phase 1.1.
- Added `scripts/run_b2_zipf_sweep.py` for:
  - `neighbor_es_availability x origin_delay` B2 advantage heatmap data;
  - `zipf_alpha x neighbor_cache_rank_gamma` sensitivity data;
  - hot/mid/cold rank-bucket summaries for B2 neighbor-choice behavior.
- Added `scripts/write_manifest.py` to record command history, model defaults, git
  state, and generated output files for each result batch.
- Added `results/phase1_b2_zipf/` as the versioned output directory for this phase.

### Changed

- Changed B2 from a scenario-level fixed decision to a request-level decision based on
  `missing_chunks`, `content_rank`, neighbor availability, and rank-aware neighbor cache
  probability.
- Updated neighbor recovery probability to use `missing_chunks` rather than requiring a
  fixed fresh set of `K` chunks after local recovery already failed.
- Added neighbor cache parameters to `SimulationConfig`:
  - `neighbor_cache_hot_prob = 0.90`;
  - `neighbor_cache_cold_prob = 0.15`;
  - `neighbor_cache_rank_gamma = 1.0`.
- Updated result rows and summaries with explainability metrics such as
  `local_chunks`, `missing_chunks`, `content_rank`, `neighbor_cache_probability`,
  `neighbor_chunk_probability`, `b2_neighbor_success_probability`,
  `b2_expected_neighbor_delay`, `b2_neighbor_selected`, `neighbor_attempt_rate`, and
  `b2_neighbor_choice_rate`.
- Reworked figure generation so Phase 1.1 figures are exported as SVG/PDF primary
  artifacts, with PNG/TIFF treated as local QA previews.
- Updated README files to point readers to the project map, experiment guide, manifest,
  and Phase 1.1 result directory.

### Validation

- Unit tests cover Zipf skew behavior, rank-monotonic cache probability, missing-chunk
  recovery, hot/cold B2 request decisions, repeated-trial reproducibility, and stable
  output columns.
- The Phase 1.1 pipeline is validated with:
  - `python -m unittest discover -s tests`;
  - `python scripts/run_scenarios.py --trials 2 --num-requests 1000 --output-dir results/phase1_b2_zipf`;
  - `python scripts/run_b2_zipf_sweep.py --trials 2 --num-requests 1000 --output-dir results/phase1_b2_zipf`;
  - `python scripts/build_figures.py --results-dir results/phase1_b2_zipf`.

### Scope

- This remains a first-stage Monte Carlo simulation. It does not yet model request
  arrivals, queueing, service capacity, true CDN congestion, online trust learning, or
  cache replacement dynamics.
- The internal `origin_congestion` scenario key is retained for compatibility, but the
  documented interpretation is origin-delay increase.
