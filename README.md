# Edge Cache Fallback Simulation

This repository is a first-stage Monte Carlo simulation for fallback control in low-trust edge-cache environments.

- Japanese version: [README_ja.md](./README_ja.md)

## Policies

- `B0`: local ES failure falls back directly to origin.
- `B1`: local ES failure searches neighboring cooperative ES first, then origin if neighbor recovery fails.
- `B2`: local ES failure compares expected neighbor-search delay and origin delay, then chooses the lower expected-delay action.

## Why jitter?

中文：我们在响应时间里加了一点很小的抖动，是为了避免所有路径的时间都过于“整齐”。真实的 edge-cache 或网络流程里，即便走同一条路径，每次请求的耗时也不会完全一样，通常会受到调度、排队、序列化和网络波动的影响。没有抖动时，mean 和 p95 会显得太理想化，也容易出现很多完全相同的响应时间，尾延迟的味道会淡一些。

日本語：応答時間に小さな揺らぎを入れているのは、全ての経路があまりにも「きれい」に揃いすぎるのを避けるためです。実際の edge-cache やネットワーク処理では、同じ経路でもスケジューリング、待ち行列、シリアライズ、ネットワーク変動の影響で遅延が少しずつ変わります。抖動がないと mean と p95 が理想化されすぎて、tail latency の自然さが薄くなります。

中文：这里的抖动很小，只是给每条路径加一点正向随机波动，不会改变“哪条路径更快”的主判断。它的作用是让尾延迟更像真实系统，而不是把仿真变成完全确定性的数字比较。

日本語：ここでの jitter は小さく、各経路に少しだけ正の乱数揺らぎを足しているだけです。目的は「どの経路が速いか」という主判断を変えることではなく、tail latency をより現実的に見せることです。

## Parameter choices

These are the baseline values used in the first-stage experiment. They are chosen so that local recovery, neighbor fallback, and origin fallback all remain visible in one run.

- `num_requests = 10000`
  - 中文：样本量足够大，mean 和 p95 会更稳定，不容易被单次随机波动带偏。
  - 日本語：サンプル数を十分にして、mean と p95 を安定させています。
- `num_contents = 500`
  - 中文：内容空间适中，便于观察 Zipf 热点分布对 fallback 策略的影响。
  - 日本語：コンテンツ空間を中程度にして、Zipf の偏りが fallback 策略にどう効くかを見やすくしています。
- `zipf_alpha = 1.1`
  - 中文：这是一个“有热点但不过分极端”的需求分布，适合第一阶段 baseline。
  - 日本語：ホットスポットはあるが極端すぎない需要分布で、第一段階の baseline に向いています。
- `es_availability = 0.82`
  - 中文：让 local / neighbor recovery 都有成功和失败的空间，方便比较 B0/B1/B2。
  - 日本語：local / neighbor recovery の成功と失敗の両方が出るようにして、B0/B1/B2 を比較しやすくしています。
- `origin_delay = 180.0`
  - 中文：让 origin 明显慢于本地和 neighbor 路径，便于看出 fallback 的价值，也给后续 sweep 留出对比空间。
  - 日本語：origin を local や neighbor よりかなり遅くして、fallback の価値が見えやすいようにし、後続の sweep でも比較しやすくしています。
- `local_es_count = 3`, `k = 3`
  - 中文：local 恢复要求 3/3 个 chunk 可用，表示 local recovery 并不总能成功，这样才需要 fallback。
  - 日本語：local recovery に 3/3 個の chunk 可用を要求することで、local が常に成功するわけではなく、fallback が必要になるようにしています。
- `neighbor_group_size = 5`
  - 中文：neighbor 池略大于 local 池，用来测试 cooperative recovery 的效果。
  - 日本語：neighbor 側を local より少し大きくして、cooperative recovery の効果を見やすくしています。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`, `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`
  - 中文：这些值表示“探测 + 恢复”的基础成本层级，neighbor 通常比 local 更贵，但仍有可能比 origin 划算。
  - 日本語：これらは「探索 + 復旧」の基礎コストで、neighbor は local より高めですが、それでも origin よりは安い場合があります。
- `seed = 20260525`
  - 中文：固定随机种子保证可复现；baseline 和 sweep 都可以重复跑出同一组结果。
  - 日本語：乱数シードを固定して再現性を確保しています。baseline も sweep も同じ条件なら同じ結果を再現できます。

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the experiments

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

The current model intentionally stays simple: it does not model queues, congestion, request arrivals, or service capacity. Those can be added later with SimPy once the baseline fallback logic is stable.

## GitHub Notes

This repository keeps the concise README on GitHub, while the detailed rationale for jitter, parameter choices, and stage progression lives in this repository as Markdown files.
