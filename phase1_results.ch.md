# 第一阶段结果解读

## 核心结论

第一阶段现在已经从单一 baseline 扩展为研究计划书中的三个正式实验场景：`steady`、`low_reliability_neighbor` 和内部 key 为 `origin_congestion` 的オリジン遅延増加シナリオ。因此现在的结果更适合用来支撑第一阶段汇报。这里保留 `origin_congestion` 只是为了兼容已有输出文件和脚本命名，对外汇报不把它表述成真实的拥塞或队列模型。

核心结论仍然要谨慎表述：`B2` 的价值是条件性的。正常环境下，`B1` 和 `B2` 几乎一样，这是合理的，因为 neighbor ES 可靠时，`B2` 的期望延迟判断通常也会选择 neighbor fallback。`B2` 真正体现价值的地方，是低信任 neighbor ES 场景：当 neighbor 成功率很低、origin 又不是特别慢时，`B2` 会避免 `B1` 那种“先试 neighbor，失败后再回 origin”的双重延迟。

当前模型仍是第一阶段 preliminary Monte Carlo simulation，不是完整的离散事件仿真。它用于验证 fallback-control 逻辑、统计流程、图表和结果解释是否成立，后续如果要模拟队列、拥塞、到达过程和服务能力，再进入更正式的 discrete-event simulation。

## 实验设置

公共设置如下：

| 参数 | 值 |
| --- | ---: |
| `num_requests` | `10000` |
| `trials` | `10` |
| `zipf_alpha` | `1.1` |
| `local_es_count` | `3` |
| `neighbor_group_size` | `5` |
| `k` | `3` |
| `seed` | `20260525` |

三场景设置如下：

| Scenario | local ES availability | neighbor ES availability | origin delay | 对应研究计划书场景 |
| --- | ---: | ---: | ---: | --- |
| `steady` | `0.82` | `0.82` | `180.0` | 定常シナリオ |
| `low_reliability_neighbor` | `0.82` | `0.25` | `180.0` | 低信頼近隣ESシナリオ |
| `origin_congestion` | `0.82` | `0.82` | `320.0` | オリジン遅延増加シナリオ |

这次补齐的关键字段是 `neighbor_es_availability`。以前 `es_availability` 同时代表 local 和 neighbor 的可靠性，因此很难表达“local 正常，但近隣協調グループ低信任”的场景。现在 local 和 neighbor 可以分开控制，`es_availability` 继续作为兼容字段，默认代表 local availability。

每个 repeated trial 使用：

```text
trial_seed = base_seed + trial_index
```

这样做是为了避免只看一次随机运行造成误判。每个 policy 都输出均值、标准差、标准误和 95% confidence interval。

## 策略含义

- `B0`: local ES 恢复失败后，直接访问 origin。
- `B1`: local ES 恢复失败后，固定先搜索 neighbor ES；neighbor 失败后再访问 origin。
- `B2`: local ES 恢复失败后，比较 neighbor-search 的期望延迟和直接访问 origin 的延迟，选择期望延迟更低的动作。

简单说，`B1` 是“总是先试邻居”，`B2` 是“先判断试邻居是否划算”。

## 三场景结果

| Scenario | Policy | Mean response time | p95 response time | Origin-free rate | Neighbor failure rate | B2 advantage vs B1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `steady` | `B0` | `101.0823` | `201.4085` | `0.55121` | `0.00000` | |
| `steady` | `B1` | `44.8589` | `70.7171` | `0.98075` | `0.04304` | |
| `steady` | `B2` | `44.8391` | `70.6902` | `0.98092` | `0.04264` | `0.0198` |
| `low_reliability_neighbor` | `B0` | `100.9463` | `201.3883` | `0.55217` | `0.00000` | |
| `low_reliability_neighbor` | `B1` | `106.5593` | `229.0214` | `0.59590` | `0.89777` | |
| `low_reliability_neighbor` | `B2` | `100.7891` | `201.3767` | `0.55303` | `0.00000` | `5.7702` |
| `origin_congestion` | `B0` | `163.6239` | `341.3924` | `0.55213` | `0.00000` | |
| `origin_congestion` | `B1` | `47.6843` | `70.7355` | `0.98059` | `0.04318` | |
| `origin_congestion` | `B2` | `47.5801` | `70.7444` | `0.98075` | `0.04298` | `0.1042` |

`B2 advantage vs B1` 的定义是：

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

该值为正时，表示 `B2` 的平均响应时间低于 `B1`。

## 场景解释

在 `steady` 场景中，local 和 neighbor 都处于正常可用水平。此时 `B1` 和 `B2` 非常接近，`B2` 相对 `B1` 的平均响应时间优势只有 `0.0198`。这不是问题，而是符合预期：当 neighbor fallback 本身是划算的，`B2` 的判断结果会接近 `B1`。

在 `low_reliability_neighbor` 场景中，neighbor ES 可用率降低到 `0.25`。这时 `B1` 的 neighbor failure rate 达到 `0.89777`，说明它大量尝试了无效 neighbor search，并且失败后还要再回 origin，所以 mean response time 上升到 `106.5593`，p95 response time 上升到 `229.0214`。`B2` 会判断 neighbor search 不划算，因此基本避免这类无效搜索，mean response time 为 `100.7891`，p95 response time 为 `201.3767`。这是第一阶段最清楚体现 `B2` 价值的场景。

在内部 key 为 `origin_congestion` 的オリジン遅延増加シナリオ中，origin delay 增大到 `320.0`。此时直接回 origin 的 `B0` 明显变差，mean response time 达到 `163.6239`，p95 response time 达到 `341.3924`。`B1` 和 `B2` 都能利用可靠 neighbor 完成大部分请求，因此明显优于 `B0`。不过由于 neighbor 可靠，`B2` 仍然会经常选择 neighbor fallback，所以 `B1` 和 `B2` 的差距仍然不大。

## Sweep 与 heatmap

除了三场景结果，第一阶段还增加了 memo 专用 sensitivity / grid 分析，用来解释 heatmap 和场景参数不是另起炉灶。这个 grid 覆盖了三场景中使用的关键参数点：

```text
neighbor_es_availability = [0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]
origin_delay = [80, 120, 180, 240, 320]
local_es_availability = 0.82
```

在 40 个 grid 参数点中：

- `29` 个参数点的 `B2 advantage vs B1` 为正，表示 `B2` 平均响应时间低于 `B1`。
- `11` 个参数点为负，但负值幅度较小。
- 最大优势出现在 `origin_delay = 80.0`、`neighbor_es_availability = 0.20`，优势为 `10.9897`。
- 最小值出现在 `origin_delay = 320.0`、`neighbor_es_availability = 0.25`，为 `-0.1971`。

这个 heatmap 的作用是补足说明：`B2` 不是在所有地方都显著赢过 `B1`，而是在近隣 ES 可用率较低、origin 成本相对不高的区域更有价值。图轴和正文都应写成 `neighbor ES availability` / `近隣 ES 可用率`，避免和 local ES 可用率混淆。

## 图表文件

图表由 `scripts/build_figures.py` 使用 Python + Matplotlib 生成，输出到 `results/figures/`。当前包含正式结果图和 memo 专用图：

- `fig_phase1_baseline_mean_response_time`
- `fig_phase1_baseline_p95_response_time`
- `fig_phase1_origin_delay_sweep`
- `fig_phase1_es_availability_sweep`
- `fig_phase1_b2_advantage_heatmap`
- `fig_phase1_scenario_mean_response_time`
- `fig_phase1_scenario_p95_response_time`
- `fig_phase1_low_reliability_neighbor_rates`
- `fig_phase1_memo_scenario_mean_response_time`
- `fig_phase1_memo_scenario_p95_response_time`
- `fig_phase1_memo_b2_advantage_heatmap`

每组图同时输出 `.svg`、`.pdf`、`.png` 和 `.tiff`。其中 `.svg` 保留可编辑文字，适合后续论文图或汇报图微调。

## 当前限制

当前模型还没有加入 queueing、congestion、request arrival process、service capacity、真实 CDN trace 或 trust-learning。因此结果只能说明第一阶段 fallback-control 逻辑下的趋势，不能直接代表真实部署性能。

另一个限制是，当前オリジン遅延増加シナリオ只是通过增大 `origin_delay` 表达 origin 成本上升，并不是真正的拥塞队列模型。后续若进入正式 discrete-event simulation，需要把请求到达、服务速率、排队延迟和缓存替换策略纳入模型。

## 第一阶段状态

从代码、结果、图表和说明文件角度看，第一阶段已经补齐到可以汇报的状态：三场景 repeated results、confidence interval、CSV 数据源、Excel 阅读入口、Nature-style 图表、中日双语结果解读都已经完成。

下一步不是继续扩展模型，而是先基于这些结果写一版简短、谨慎的 Ueyama-sensei progress memo。memo 里应强调第一阶段是 preliminary simulation，并说明 `B2` 的价值主要体现在低信任 neighbor ES 条件下避免无效 fallback，而不是宣称 `B2` 在所有场景中绝对最优。
