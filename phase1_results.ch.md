# 第一阶段结果解读

## 核心结论

第一阶段结果支持一个谨慎结论：`B2` 的价值是条件性的。baseline 设置下，`B1` 和 `B2` 的平均响应时间几乎相同；但在某些 `origin_delay` 和 `es_availability` 组合下，`B2` 能避免不划算的 neighbor fallback，因此比固定先搜索 neighbor 的 `B1` 更稳。

这还不是最终系统结论。当前结果来自第一阶段 Monte Carlo 模型，用来确认 fallback-control 逻辑、统计流程和可视化分析是否成立。

## 实验设置

baseline 使用以下设置：

| 参数 | 值 |
| --- | ---: |
| `num_requests` | `10000` |
| `trials` | `10` |
| `zipf_alpha` | `1.1` |
| `es_availability` | `0.82` |
| `origin_delay` | `180.0` |
| `local_es_count` | `3` |
| `neighbor_group_size` | `5` |
| `k` | `3` |
| `seed` | `20260525` |

每个 repeated trial 使用：

```text
trial_seed = base_seed + trial_index
```

这样做的目的，是避免只看一次随机实验造成“刚好这次比较好或比较差”的误判。

## 策略含义

- `B0`: local ES 恢复失败后，直接访问 origin。
- `B1`: local ES 恢复失败后，固定先搜索 neighbor ES；neighbor 失败后再访问 origin。
- `B2`: local ES 恢复失败后，比较 neighbor-search 的期望延迟和直接访问 origin 的延迟，选择期望延迟更低的动作。

简单说，`B1` 是“总是先试邻居”，`B2` 是“先判断试邻居是否划算”。

## baseline 结果

baseline repeated trials 的主要结果如下：

| Policy | Mean response time | 95% CI | p95 response time | Origin-free rate |
| --- | ---: | ---: | ---: | ---: |
| `B0` | `101.0823` | `100.6808` - `101.4838` | `201.4085` | `0.55121` |
| `B1` | `44.8589` | `44.6308` - `45.0870` | `70.7171` | `0.98075` |
| `B2` | `44.8391` | `44.6211` - `45.0571` | `70.6902` | `0.98092` |

在 baseline 下，`B1` 和 `B2` 都明显优于 `B0`。原因是 `B0` local 失败后直接回 origin，而 origin delay 较高；`B1` 和 `B2` 能利用 neighbor ES 完成大部分请求。

但 `B2` 相对 `B1` 的平均响应时间优势只有：

```text
B2 advantage vs B1 = 0.0198
```

这个差距非常小。因此 baseline 下不能说 `B2` 显著优于 `B1`，更合适的说法是：`B2` 在正常 baseline 条件下保持了和 `B1` 几乎相同的性能。

## sweep 与 heatmap 结果

二维 grid 使用：

```text
origin_delay x es_availability
```

并计算：

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

该值为正时，表示 `B2` 比 `B1` 更快。

在 36 个 grid 参数点中：

- `20` 个参数点为正，表示 `B2` 平均响应时间低于 `B1`。
- `16` 个参数点为负，但负值幅度很小。
- 最大优势出现在 `origin_delay = 40.0`、`es_availability = 0.45`，优势为 `18.0856`。
- 最小值出现在 `origin_delay = 320.0`、`es_availability = 0.75`，为 `-0.1796`。

这个模式说明：当 origin 很快、neighbor 可用性较低时，固定搜索 neighbor 的 `B1` 容易多付一次 neighbor-search 成本；`B2` 会更倾向于直接访问 origin，因此能避免这类浪费。

## 图表文件

图表由 `scripts/build_figures.py` 使用 Python + Matplotlib 生成，输出到 `results/figures/`。

- `fig_phase1_baseline_mean_response_time`: baseline 平均响应时间。
- `fig_phase1_baseline_p95_response_time`: baseline p95 响应时间。
- `fig_phase1_origin_delay_sweep`: origin delay sensitivity。
- `fig_phase1_es_availability_sweep`: ES availability sensitivity。
- `fig_phase1_b2_advantage_heatmap`: B2 相对 B1 的优势区域。

每张图同时输出 `.svg`、`.pdf`、`.png` 和 `.tiff`。其中 `.svg` 保留可编辑文字，适合后续论文图或汇报图微调。

## 当前限制

当前模型还没有加入 queueing、congestion、request arrival process、service capacity、真实 CDN trace 或 trust-learning。因此结果只能说明第一阶段 fallback-control 逻辑下的趋势，不能直接代表真实部署性能。

## 下一步

下一步建议先基于这些图和结果写一版简短的 Ueyama-sensei 进度 memo 草稿。memo 里重点不应夸大 `B2`，而应表达：已经完成可复现实验框架、repeated trials、confidence interval 和 heatmap；初步发现 `B2` 的主要价值是在 neighbor fallback 不划算时避免额外开销。
