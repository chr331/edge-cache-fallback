# Phase 1.1 Experiment Guide

This guide explains how to reproduce the request-level B2 and Zipf-aware Phase 1.1
experiments. It is written for a reader who has not worked with the code before.

## What Changed In Phase 1.1

The earlier B2 policy made one decision per scenario: try the neighbor group or go to the
origin. Phase 1.1 makes B2 decide per request.

For each local recovery failure:

```text
missing_chunks = K - local_chunks
p_cache(rank) = cold + (hot - cold) * rank ** (-zipf_alpha * cache_rank_gamma)
p_chunk = neighbor_es_availability * p_cache(rank)
P_success = Pr(Binomial(neighbor_group_size, p_chunk) >= missing_chunks)
E_neighbor = P_success * neighbor_recovery_delay
           + (1 - P_success) * (neighbor_probe_delay + origin_delay)
```

B2 searches neighbors only when `E_neighbor <= origin_delay`.

This means B2 can behave differently for hot and cold content within the same scenario.
Hot content has a higher neighbor cache probability, while cold content is more likely to
fall back directly to the origin when neighbor probing is not worth the extra delay.

## Commands

Run all commands from the repository root.

### 1. Unit Tests

```bash
python -m unittest discover -s tests
```

This checks:

- Zipf probabilities become more head-heavy when `zipf_alpha` increases.
- Neighbor cache probability decreases with rank.
- Neighbor recovery uses `missing_chunks`, not a fixed requirement of `K` chunks.
- B2 can choose neighbors for hot content and origin for cold content.
- Fallback-stage metrics focus on requests where local recovery failed.
- Repeated-trial aggregation remains reproducible and includes the new metrics.

### 2. Smoke Run

Use a small run first to verify the pipeline quickly.

```bash
python scripts/run_scenarios.py --trials 2 --num-requests 1000 --output-dir results/phase1_b2_zipf
python scripts/run_b2_zipf_sweep.py --trials 2 --num-requests 1000 --output-dir results/phase1_b2_zipf
python scripts/build_figures.py --results-dir results/phase1_b2_zipf
```

### 3. Formal Phase 1.1 Run

The committed Phase 1.1 result batch uses:

```bash
python scripts/run_scenarios.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf
python scripts/run_b2_zipf_sweep.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf
python scripts/build_figures.py --results-dir results/phase1_b2_zipf
python scripts/write_manifest.py --output-dir results/phase1_b2_zipf --command "python scripts/run_scenarios.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf" --command "python scripts/run_b2_zipf_sweep.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf" --command "python scripts/build_figures.py --results-dir results/phase1_b2_zipf"
```

## Output Files

| File | Meaning |
| --- | --- |
| `scenario_summary.csv` | Repeated-trial summary for steady, low-reliability neighbor, origin-delay increase, and decision-boundary diagnostic scenarios. |
| `scenario_trials.csv` | Per-trial scenario summaries used to compute confidence intervals. |
| `neighbor_origin_grid_summary.csv` | Sensitivity grid over neighbor availability and origin delay. |
| `zipf_sensitivity_summary.csv` | Sensitivity grid over `zipf_alpha` and `neighbor_cache_rank_gamma`. |
| `rank_bucket_summary.csv` | Hot/mid/cold content-rank summary for B2 neighbor-choice behavior. |
| `rank_bucket_trials.csv` | Per-trial source data for the rank-bucket summary. |
| `manifest.json` | Batch metadata: commands, model defaults, git state, and output file list. |
| `figures/*.svg` and `figures/*.pdf` | Main reviewable figure artifacts. |

## How To Read The Metrics

| Metric | Meaning |
| --- | --- |
| `mean_response_time` | Average request response time in milliseconds. |
| `p95_response_time` | 95th percentile response time, used for tail latency. |
| `fallback_mean_response_time` | Mean response time among requests with `missing_chunks > 0`; this isolates the fallback-decision stage. |
| `fallback_p95_response_time` | 95th percentile response time among local-failure requests. |
| `origin_free_rate` | Fraction of requests completed without origin access. |
| `local_failure_rate` | Fraction of requests where local ES could not reconstruct the file. |
| `neighbor_attempt_rate` | Fraction of all requests that probed the neighbor group. |
| `neighbor_failure_rate` | Fraction of neighbor attempts that failed and then needed origin access. |
| `neighbor_skip_rate` | Fraction of local-failure decisions where the policy skipped neighbor probing. |
| `b2_neighbor_choice_rate` | For B2 only: fraction of local-failure decisions where B2 selected neighbor probing. |
| `b2_advantage_vs_b1_mean` | `B1 mean - B2 mean`; positive values mean B2 is faster than B1. |
| `b2_fallback_advantage_vs_b1_mean` | `B1 fallback mean - B2 fallback mean`; positive values mean B2 is faster after local recovery fails. |

## What The Phase 1.1 Figures Show

The figure set is designed around one claim:

> Request-level B2 suppresses low-value neighbor probing while preserving neighbor
> cooperation when the expected delay is favorable.

The scenario bars show whether B2 behaves reasonably under the three research-plan
scenarios and the decision-boundary diagnostic scenario. The fallback-stage scenario
figure focuses on requests where local recovery failed, which makes the B1/B2 decision
difference easier to see. The neighbor/origin heatmap shows where B2 is most useful
compared with static B1. The Zipf/cache heatmap shows that B2 becomes more valuable when
cache probability is more rank-sensitive. The rank-bucket figure directly checks that B2
is more willing to use neighbors for hot content than for mid/cold content in a
decision-boundary setting.

## Scope Limit

These experiments are still Monte Carlo simulations. They do not model request arrivals,
queues, service capacity, real CDN traces, online trust learning, or true origin-server
congestion. The internal key `origin_congestion` should be read as origin-delay increase
in this repository.
