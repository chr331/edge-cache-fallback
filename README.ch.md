# Edge Cache Fallback Simulation

这个仓库是低信任 edge-cache 环境下 fallback-control 策略的第一阶段 Monte Carlo 仿真项目。当前目标不是先做复杂系统模型，而是先把 B0/B1/B2 三种策略跑通，形成可复现的 baseline、参数 sweep、Excel 报告和研究日志。

- English: [README.md](./README.md)
- Japanese: [README.ja.md](./README.ja.md)
- 中文研究日志: [research_log.ch.md](./research_log.ch.md)
- 日文研究日志: [research_log.ja.md](./research_log.ja.md)

## 策略定义

- `B0`: local ES 无法恢复内容时，直接回 origin。
- `B1`: local ES 失败后，先搜索 neighbor cooperative ES；neighbor 也失败时再回 origin。
- `B2`: local ES 失败后，比较 neighbor search 的期望延迟和直接访问 origin 的延迟，选择期望延迟更低的动作。

## 第一阶段实验设定

第一阶段使用 Monte Carlo 仿真，不引入队列、拥塞、请求到达过程或服务能力模型。这样做是为了先确认 fallback 逻辑和指标计算稳定，再逐步增加复杂度。

| 参数 | baseline 值 | 设定理由 |
| --- | ---: | --- |
| `num_contents` | `500` | 内容空间适中，可以观察 Zipf 热点分布，又不会让第一阶段实验过重。 |
| `num_requests` | `10000` | 样本量足够大，让 mean 和 p95 更稳定。 |
| `zipf_alpha` | `1.1` | 表示“有热点但不过分极端”的请求分布，适合作为 baseline。 |
| `es_availability` | `0.82` | local / neighbor recovery 都会出现成功和失败，便于比较三种策略。 |
| `origin_delay` | `180.0` | 让 origin 明显慢于 local 和 neighbor 路径，方便看出 fallback 的价值。 |
| `local_es_count` | `3` | local 侧只提供有限 chunk 来源，使 local recovery 不会总是成功。 |
| `neighbor_group_size` | `5` | neighbor 池略大于 local 池，用于观察 cooperative recovery 的收益。 |
| `k` | `3` | 需要至少 3 个 chunk 才能恢复内容，保留 erasure-coding 设定的核心约束。 |
| `local_probe_delay` | `12.0` | 表示 local 探测成本。 |
| `neighbor_probe_delay` | `28.0` | neighbor 探测比 local 更贵，但仍可能比 origin 划算。 |
| `local_recovery_delay` | `18.0` | 表示 local 恢复完成后的基础延迟。 |
| `neighbor_recovery_delay` | `48.0` | neighbor 恢复比 local 慢，但在 origin 很慢时仍可能有价值。 |
| `seed` | `20260525` | 固定随机种子，保证 baseline 和 sweep 可以复现。 |

关于 latency jitter 的说明不放在 README 里，而是记录在研究日志中，因为它属于模型解释和实验记录的一部分。

## 运行环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 运行实验

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
python scripts\build_report.py
```

## 输出文件

- `results/summary.csv`: baseline 结果，每个 policy 一行。
- `results/sweep_summary.csv`: `origin_delay` 和 `es_availability` 的参数敏感性结果。
- `results/edge_cache_fallback_report.xlsx`: 本地阅读用的 Excel 报告。
- `research_log.ch.md`: 中文研究日志。
- `research_log.ja.md`: 日文研究日志。

## 关键指标

- `mean_response_time`: 平均响应时间。
- `p95_response_time`: 95 分位响应时间，用于观察 tail latency。
- `origin_free_rate`: 不访问 origin 就完成请求的比例。
- `neighbor_failure_rate`: 尝试 neighbor fallback 后仍失败的比例。

## 验证

```powershell
python -m unittest discover -s tests
```
