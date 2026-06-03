# Edge Cache Fallback Simulation

<p align="center">
  <a href="./README.md"><img src="https://img.shields.io/badge/English-README-2563eb?style=for-the-badge" alt="English README"></a>
  <a href="./README.ch.md"><img src="https://img.shields.io/badge/%E4%B8%AD%E6%96%87-%E8%AF%B4%E6%98%8E-2563eb?style=for-the-badge" alt="Chinese README"></a>
  <a href="./README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-%E8%AA%AC%E6%98%8E-2563eb?style=for-the-badge" alt="Japanese README"></a>
</p>

This repository contains a first-stage simulation study for fallback-control policies in a low-trust edge-cache environment. The goal is to make the experiment understandable, reproducible, and ready for a first progress report, even for a reader who has not seen the research proposal.

## 1. What This Project Studies

Modern video and content-delivery systems often place edge servers close to users so that every request does not have to go back to the origin server. This reduces latency and lowers the load on the core network. However, edge servers may be less reliable than a well-managed origin server because they can run on cheaper hardware, be deployed in weaker environments, or fail temporarily.

This project studies the following question:

> When the local edge-server group cannot reconstruct the requested content, should the system go directly to the origin server, or should it first ask neighboring edge servers for help?

The study assumes an erasure-coded cache. A file is split into chunks, and the client needs at least `K` chunks to reconstruct the file. In the current baseline, `K = 3`. If the local edge-server group cannot provide enough chunks, the system must choose a fallback action.

The core idea is that neighboring edge servers may already store useful chunks because content requests are skewed by popularity, approximately following a Zipf distribution. Searching neighbors can therefore help, but it can also hurt: if the neighbors are unreliable, the system may waste time probing them and then still need to contact the origin.

## 2. Current Phase and Scope

This repository implements a **preliminary Monte Carlo simulation**. It is intentionally simple and is meant to test the fallback-control logic before building a full discrete-event simulator.

The current phase does implement:

- request generation from a Zipf-like popularity distribution;
- local edge-server recovery checks;
- neighbor edge-server recovery checks;
- three fallback policies, `B0`, `B1`, and `B2`;
- request-level B2 decisions using the requested content rank and the number of missing chunks;
- repeated trials with fixed seeds for reproducibility;
- confidence intervals for reported metrics;
- one-dimensional sensitivity sweeps;
- a two-dimensional heatmap for the advantage of `B2` over `B1`;
- Zipf/cache-rank sensitivity sweeps;
- Nature-style research figures;
- an Excel report for easier reading;
- Chinese and Japanese result-interpretation documents.

The current phase does **not** yet implement:

- request arrival processes;
- service capacity;
- queueing delay;
- real server congestion;
- online trust learning;
- real CDN traces;
- content-level cache placement;
- cache-capacity dynamics;
- cache replacement policies.

This distinction is important: the current `origin_delay` increase experiment is an **origin-delay increase scenario**, not a true congestion model.

## 3. System Model in Plain Language

Each simulated request follows this logic.

1. A user requests a content item.
2. The content item is assumed to require at least `K` chunks for reconstruction.
3. The simulator checks whether the local edge-server group can provide enough chunks.
4. If local recovery succeeds, the request finishes at the edge.
5. If local recovery fails, the selected fallback policy decides what to do next.

The simulation separates two kinds of edge-server availability:

- `local_es_availability`: the reliability of the local edge servers close to the user.
- `neighbor_es_availability`: the reliability of the neighboring cooperative edge-server group.

This separation matters because one of the formal scenarios keeps the local servers normal but makes only the neighbor group unreliable. That is the key setting where `B2` should avoid useless neighbor searches.

## 4. Policies Implemented

### B0: Direct Origin Fallback

`B0` is the traditional baseline. If the local edge-server group cannot reconstruct the file, the system directly fetches the missing chunks from the origin server.

This is simple and avoids wasting time on unreliable neighbors, but it also means the system may use the origin even when nearby edge servers could have helped.

### B1: Static Neighbor-First Fallback

`B1` always searches the neighboring cooperative edge-server group after local recovery fails. If the neighbor group can provide enough chunks, the request finishes without using the origin. If the neighbor group also fails, the system then falls back to the origin.

This policy can reduce origin access when neighbors are reliable. However, when neighbors are unreliable, it can create a double delay: first the system spends time searching neighbors, then it still has to fetch from the origin.

### B2: Expected-Delay-Based Neighbor Search Decision

`B2` is a dynamic decision policy. After local recovery fails, it estimates whether neighbor search is worth trying. It compares:

- the expected delay of trying neighbors and falling back to origin if neighbors fail;
- the delay of going directly to the origin.

In Phase 1.1, this decision is made per request, not once per scenario. The current
model estimates the number of chunks still needed after the local attempt, then adjusts
neighbor success by content rank:

```text
missing_chunks = K - local_chunks
p_cache(rank) = cold + (hot - cold) * rank ** (-zipf_alpha * cache_rank_gamma)
p_chunk = neighbor_es_availability * p_cache(rank)
P_success = Pr(Binomial(neighbor_group_size, p_chunk) >= missing_chunks)
```

Then it compares:

```text
E_neighbor =
    P_success * neighbor_recovery_delay
    + (1 - P_success) * (neighbor_probe_delay + origin_delay)

Neighbor search is selected only when E_neighbor <= origin_delay.
```

This is a simplified probability model, not a learned trust model. It is enough for the first-stage experiment because the goal is to test whether an expected-delay decision can avoid obviously unprofitable neighbor fallback.

## 5. Baseline Parameters

The default first-stage experiment uses the following values.

| Parameter | Value | Meaning |
| --- | ---: | --- |
| `num_contents` | `500` | Number of content items in the simulated library. |
| `num_requests` | `10000` | Number of requests per trial in the default experiment. |
| `zipf_alpha` | `1.1` | Popularity skew of the request distribution. |
| `neighbor_cache_hot_prob` | `0.90` | Estimated probability that a very hot item is cached by a neighbor ES. |
| `neighbor_cache_cold_prob` | `0.15` | Estimated lower bound for cold-item neighbor caching. |
| `neighbor_cache_rank_gamma` | `1.0` | Controls how strongly cache probability drops with content rank. |
| `local_es_availability` | `0.82` | Normal local edge-server availability. |
| `neighbor_es_availability` | `0.82` by default | Normal neighbor availability unless a scenario overrides it. |
| `es_availability` | `0.82` | Compatibility field for older scripts. |
| `origin_delay` | `180.0 ms` | Default origin access delay. |
| `local_es_count` | `3` | Number of local edge servers checked by the model. |
| `neighbor_group_size` | `5` | Number of neighboring edge servers in the cooperative group. |
| `k` | `3` | Minimum number of chunks needed to reconstruct the file. |
| `local_probe_delay` | `12.0 ms` | Delay cost for local probing. |
| `neighbor_probe_delay` | `28.0 ms` | Delay cost for neighbor probing. |
| `local_recovery_delay` | `18.0 ms` | Recovery delay when local reconstruction succeeds. |
| `neighbor_recovery_delay` | `48.0 ms` | Recovery delay when neighbor reconstruction succeeds. |
| `seed` | `20260525` | Base random seed for reproducibility. |

## 6. Formal Scenarios

The first-stage study now uses three formal scenarios. These scenarios are the main bridge between the code and the research plan.

| Scenario key | External explanation | Local availability | Neighbor availability | Origin delay | Purpose |
| --- | --- | ---: | ---: | ---: | --- |
| `steady` | steady scenario | `0.82` | `0.82` | `180 ms` | Tests whether neighbor fallback adds unnecessary overhead under normal conditions. |
| `low_reliability_neighbor` | low-reliability neighbor ES scenario | `0.82` | `0.25` | `180 ms` | Tests whether `B2` avoids useless neighbor search when the neighbor group is unreliable. |
| `origin_congestion` | origin-delay increase scenario | `0.82` | `0.82` | `320 ms` | Tests the value of edge cooperation when the origin path is more expensive. |

The internal key `origin_congestion` is kept for compatibility with earlier output files. In reports and memos, it should be described as **origin-delay increase**, because the current model only increases `origin_delay`; it does not simulate queueing, request arrivals, service capacity, or real congestion.

## 7. Experiments Implemented

### 7.1 Baseline Experiment

`scripts/run_experiment.py` runs a quick baseline experiment for `B0`, `B1`, and `B2`. It is useful as a smoke test and produces a simple policy-level summary.

### 7.2 Single-Seed Sweep

`scripts/run_sweep.py` runs quick one-dimensional sweeps. It keeps the old fast workflow available so that the model can be checked quickly before running repeated trials.

### 7.3 Formal Three-Scenario Repeated Experiment

`scripts/run_scenarios.py` runs the three formal scenarios: `steady`, `low_reliability_neighbor`, and `origin_congestion` as the internal key for origin-delay increase.

For each scenario and each policy, the script runs repeated trials and reports statistics such as mean, standard deviation, standard error, and 95% confidence intervals.

### 7.4 Repeated Sensitivity Sweeps

`scripts/run_repeated.py` runs a larger repeated-trial workflow:

- baseline repeated trials;
- `origin_delay` sweep;
- `es_availability` sweep for compatibility;
- two-dimensional `origin_delay x neighbor_es_availability` grid.

The default number of trials is `10`. The seed for each trial is generated as:

```text
trial_seed = base_seed + trial_index
```

This makes the experiment reproducible while still allowing repeated-trial statistics.

### 7.5 Scenario-Aligned Heatmap Sweep

`scripts/run_memo_sweep.py` creates a heatmap grid aligned with the formal scenario parameters. It uses:

```text
neighbor_es_availability = [0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]
origin_delay = [80, 120, 180, 240, 320]
local_es_availability = 0.82
```

This grid covers:

- the low-reliability neighbor scenario at `neighbor_es_availability = 0.25`;
- the steady scenario at `neighbor_es_availability = 0.82` and `origin_delay = 180`;
- the origin-delay increase scenario at `neighbor_es_availability = 0.82` and `origin_delay = 320`.

### 7.6 Phase 1.1 B2/Zipf Sweep

`scripts/run_b2_zipf_sweep.py` is the main new Phase 1.1 sensitivity entry point. It
keeps the `neighbor_es_availability x origin_delay` grid and adds a second grid over:

```text
zipf_alpha = [0.6, 0.8, 1.0, 1.1, 1.3, 1.5]
neighbor_cache_rank_gamma = [0.3, 0.6, 1.0, 1.4, 2.0]
```

It also writes a hot/mid/cold rank-bucket summary so that the B2 decision can be checked
directly: B2 should be more willing to search neighbors for hot content and less willing
to probe neighbors for low-value cold requests.

## 8. Metrics

The main metrics are:

| Metric | Meaning |
| --- | --- |
| `mean_response_time` | Average response time across all simulated requests. |
| `p95_response_time` | 95th percentile response time, used to observe tail latency. |
| `origin_free_rate` | Fraction of requests completed without accessing the origin. |
| `local_failure_rate` | Fraction of requests where the local ES group could not reconstruct the file. |
| `neighbor_attempt_rate` | Fraction of all requests that probed the neighbor cooperative group. |
| `neighbor_failure_rate` | Fraction of neighbor fallback attempts that fail and then need origin fallback. |
| `b2_neighbor_choice_rate` | For B2 only: fraction of local-failure decisions where B2 selected neighbor probing. |
| `b2_advantage_vs_b1_mean` | Difference between `B1` and `B2` mean response time. Defined as `B1 - B2`. Positive values mean `B2` is faster than `B1`. |

The most important result pattern is conditional:

- Under normal conditions, `B1` and `B2` are often similar because `B2` also chooses neighbor search when neighbors are reliable.
- Under low neighbor reliability, `B2` tends to behave closer to `B0` by suppressing unprofitable neighbor searches.
- When origin delay is higher and neighbors are reliable, both `B1` and `B2` can benefit from neighbor fallback.

## 9. Result Files

| File or directory | Description |
| --- | --- |
| `results/summary.csv` | Baseline policy summary. |
| `results/sweep_summary.csv` | Quick single-seed sweep results. |
| `results/scenario_summary.csv` | Repeated-trial summary for the three formal scenarios. |
| `results/scenario_trials.csv` | Per-trial summaries for the formal scenarios. |
| `results/repeated_summary.csv` | Repeated-trial means, standard deviations, standard errors, and 95% confidence intervals. |
| `results/repeated_trials.csv` | Per-trial policy summaries for repeated experiments. |
| `results/grid_summary.csv` | Two-dimensional repeated grid over origin delay and neighbor availability. |
| `results/memo_heatmap_summary.csv` | Scenario-aligned heatmap grid covering the formal scenario settings. |
| `results/figures/` | Publication-style figures exported as SVG, PDF, PNG, and TIFF. |
| `results/phase1_b2_zipf/` | Versioned Phase 1.1 result batch for request-level B2 and Zipf/cache-rank sensitivity. |
| `results/phase1_b2_zipf/manifest.json` | Commands, git state, model defaults, and generated files for the Phase 1.1 batch. |
| `docs/project_map.md` | Project navigation: what each directory is for and how new result batches should be organized. |
| `docs/experiment_guide.md` | Beginner-friendly Phase 1.1 reproduction guide with commands, outputs, and metric definitions. |
| `docs/phase1_b2_zipf_report.md` | Detailed Chinese experiment report for Phase 1.1 with embedded figures and reviewer-style interpretation. |
| `results/edge_cache_fallback_report.xlsx` | Formatted Excel report for reading results without manually opening CSV files. |
| `phase1_results.ch.md` | Chinese first-stage result interpretation. |
| `phase1_results.ja.md` | Japanese first-stage result interpretation. |
| `research_log.md` | Research-log language index. |
| `research_log.ch.md` | Chinese research log. |
| `research_log.ja.md` | Japanese research log. |

## 10. How to Run

Create and activate the Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run quick checks:

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
```

Run the formal first-stage scenarios:

```powershell
python scripts\run_scenarios.py
```

Run the repeated sensitivity and grid experiments:

```powershell
python scripts\run_repeated.py
```

Run the scenario-aligned heatmap sweep:

```powershell
python scripts\run_memo_sweep.py
```

Run the Phase 1.1 request-level B2/Zipf workflow:

```powershell
python scripts\run_scenarios.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf
python scripts\run_b2_zipf_sweep.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf
python scripts\build_figures.py --results-dir results/phase1_b2_zipf
python scripts\write_manifest.py --output-dir results/phase1_b2_zipf --command "python scripts/run_scenarios.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf" --command "python scripts/run_b2_zipf_sweep.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf" --command "python scripts/build_figures.py --results-dir results/phase1_b2_zipf"
```

Generate figures and Excel report:

```powershell
python scripts\build_figures.py
python scripts\build_report.py
```

For faster development checks:

```powershell
python scripts\run_scenarios.py --trials 3 --num-requests 1000
python scripts\run_repeated.py --trials 3 --num-requests 1000
python scripts\run_b2_zipf_sweep.py --trials 2 --num-requests 1000 --output-dir results/phase1_b2_zipf
```

## 11. Validation

Run unit tests:

```powershell
python -m unittest discover -s tests
```

The test suite checks the main simulation behavior, Zipf/cache probability behavior,
request-level B2 decisions, repeated-trial statistics, confidence-interval consistency,
policy ordering, local/neighbor availability separation, and the heatmap sweep coverage
for the formal scenario parameters.

## 12. How to Read the Current Results

The first-stage result should not be read as "`B2` always wins." The better interpretation is:

> `B2` is useful when the value of neighbor search is conditional. It behaves like `B1` when neighbors are likely to help, and it behaves closer to `B0` when neighbor search is expected to be wasteful.

This is why the heatmap is important. It shows the region where `B2` has a positive advantage over `B1`, based on:

```text
B2 advantage = B1 mean response time - B2 mean response time
```

Positive values mean `B2` is faster than `B1`.

## 13. Next Research Step

The next modeling decision is whether to prioritize:

- content-level cache placement and cache capacity modeling; or
- a full discrete-event simulator with request arrivals, service capacity, and queueing delay.

The current repository is designed to make that decision easier by providing a reproducible first-stage baseline and clear evidence about when neighbor fallback is helpful or harmful.
