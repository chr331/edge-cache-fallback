# Edge Cache Fallback Simulation

这个仓库用于第一阶段的低信任 edge-cache fallback-control 仿真。当前目标是先把 `B0`、`B1`、`B2` 三种策略做成可复现、可统计汇报的 Monte Carlo 实验，而不是引入队列、拥塞、真实 trace 或 trust-learning。

- English: [README.md](./README.md)
- Japanese: [README.ja.md](./README.ja.md)
- 中文研究日志: [research_log.ch.md](./research_log.ch.md)
- 日文研究日志: [research_log.ja.md](./research_log.ja.md)

## 策略定义

- `B0`: local ES 无法恢复内容时，直接 fallback 到 origin。
- `B1`: local ES 失败后，先搜索 neighbor cooperative ES；neighbor 也失败时再回 origin。
- `B2`: local ES 失败后，比较 neighbor-search 的期望延迟和直接访问 origin 的延迟，选择期望延迟更低的动作。

## 第一阶段实验设置

| 参数 | baseline 值 | 说明 |
| --- | ---: | --- |
| `num_contents` | `500` | 中等内容空间，用于模拟 Zipf 热点分布。 |
| `num_requests` | `10000` | 默认样本量，用于稳定 mean 和 p95。 |
| `zipf_alpha` | `1.1` | 有热点但不过分极端的请求分布。 |
| `es_availability` | `0.82` | 让 local / neighbor recovery 同时存在成功和失败。 |
| `origin_delay` | `180.0` | 让 origin 明显慢于 local / neighbor 路径。 |
| `local_es_count` | `3` | local 侧 chunk 来源有限。 |
| `neighbor_group_size` | `5` | neighbor 池略大，用于观察协作恢复收益。 |
| `k` | `3` | 至少需要 3 个 chunk 才能恢复内容。 |
| `seed` | `20260525` | 固定随机种子，便于复现。 |

## 环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行实验

快速 baseline 和单 seed sweep：

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
```

第一阶段正式统计入口：

```powershell
python scripts\run_repeated.py
```

开发验证可用较小规模：

```powershell
python scripts\run_repeated.py --trials 3 --num-requests 1000
```

生成阅读用 Excel：

```powershell
python scripts\build_report.py
```

## repeated trials 与 grid sweep

`scripts/run_repeated.py` 默认对 baseline、`origin_delay` sweep、`es_availability` sweep 以及二维 `origin_delay x es_availability` grid 做重复实验。默认 `trials = 10`，每次 trial 的 seed 使用 `base_seed + trial_index`，用于估计 Monte Carlo 方差和 95% confidence interval。

二维 grid 会计算：

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

如果该值为正，表示 B2 的平均响应时间低于 B1。

## 输出文件

- `results/summary.csv`: baseline 结果，每个 policy 一行。
- `results/sweep_summary.csv`: `origin_delay` 和 `es_availability` 的单 seed sweep。
- `results/repeated_summary.csv`: repeated trials 的 mean、std、stderr 和 95% CI。
- `results/grid_summary.csv`: 二维 `origin_delay x es_availability` grid 的 repeated 统计。
- `results/repeated_trials.csv`: 每个 trial 的 policy-level summary。
- `results/edge_cache_fallback_report.xlsx`: 本地阅读用 Excel 报告，包含 repeated summary 和 B2 advantage grid sheet。

## 关键指标

- `mean_response_time`: 平均响应时间。
- `p95_response_time`: 95 分位响应时间，用于观察 tail latency。
- `origin_free_rate`: 不访问 origin 就完成请求的比例。
- `neighbor_failure_rate`: 尝试 neighbor fallback 后仍失败的比例。
- `b2_advantage_vs_b1_mean`: B1 与 B2 平均响应时间差，定义为 `B1 - B2`。

## 验证

```powershell
python -m unittest discover -s tests
```
