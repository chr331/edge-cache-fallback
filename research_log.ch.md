# 研究日志

## 2026-05-25：Baseline 阶段

### 本阶段主题

本阶段完成了低信任 edge-cache 环境下 fallback-control 研究的第一版可复现实验脚手架。目标不是先追求复杂模型，而是先把 B0/B1/B2 三种策略跑通、记录关键指标，并建立“仿真 -> 结果 -> 图表/Excel -> 研究说明 -> GitHub 备份”的基础流程。

### 做了什么

- 整理 Python 项目结构，新增 `src/edge_cache_sim/`、`scripts/`、`tests/` 和 `results/`。
- 实现第一阶段 Monte Carlo 仿真模型，用随机请求和 ES 可用性模拟 local recovery、neighbor fallback 和 origin fallback。
- 实现并比较三种策略：
  - `B0`: local ES 失败后直接回 origin。
  - `B1`: local ES 失败后先搜索 neighbor ES，neighbor 失败后再回 origin。
  - `B2`: local ES 失败后比较 neighbor-search 的期望延迟和 origin 延迟，选择期望延迟更低的动作。
- 生成 `results/summary.csv` 作为可复现实验数据源。
- 生成 `results/edge_cache_fallback_report.xlsx`，包含 Overview、Parameters、Summary 和 Charts 四个 sheet，用来替代直接阅读裸 CSV。
- 添加 5 个单元测试，覆盖 local success、B0 fallback、B1 neighbor recovery、B2 origin choice 和三策略 summary 输出。
- 创建公开仓库 `chr331/edge-cache-fallback`，并将第一版代码、README、研究日志和示例 CSV 推送到 `main`。

### 实验设置

- Scenario: `baseline`
- Number of requests: `10000`
- Zipf alpha: `1.1`
- ES availability: `0.82`
- Origin delay: `180.0`
- Local ES count: `3`
- Neighbor group size: `5`
- Required chunks `K`: `3`
- Random seed: `20260525`

### 关键指标

- `mean_response_time`: 平均响应时间。
- `p95_response_time`: 95 分位响应时间，用来观察 tail latency。
- `origin_free_rate`: 不访问 origin 就完成请求的比例。
- `neighbor_failure_rate`: 尝试 neighbor fallback 后仍失败的比例。

### 初步结果

- `B0`: mean response time `101.247`, p95 `201.405`, origin-free rate `0.5503`, neighbor failure rate `0.0000`
- `B1`: mean response time `45.214`, p95 `70.844`, origin-free rate `0.9790`, neighbor failure rate `0.0468`
- `B2`: mean response time `45.170`, p95 `70.909`, origin-free rate `0.9788`, neighbor failure rate `0.0474`

### 初步判断

Neighbor fallback 在 baseline 参数下明显有效。与 B0 相比，B1/B2 大幅减少了访问 origin 的比例，也降低了平均响应时间和 p95 响应时间。

B2 在这一组参数下没有明显优于 B1，主要原因是当前 baseline 中 neighbor ES 可用性较高、origin delay 较大，因此 neighbor search 几乎总是值得尝试。这组参数更适合证明“neighbor fallback 有价值”，但还不足以突出 B2 的动态选择优势。

### 为什么加入 jitter

响应时间里加入小幅随机抖动，是为了避免所有路径的时间都过于“整齐”。真实 edge-cache 系统里，同一路径的延迟会受到调度、排队、网络波动、序列化开销等影响；如果完全使用 deterministic delay，baseline 结果会显得不自然，p95 也会缺少尾部波动。

当前 jitter 很小，只是在每条路径的基础延迟上加一点正向随机波动。它的目的不是改变“哪个策略更快”的主判断，而是让 tail latency 更接近真实系统。

### 参数设定说明

- `num_requests = 10000`: 保证样本量足够，mean 和 p95 更稳定。
- `num_contents = 500`: 内容空间适中，便于观察 Zipf 热点分布，同时保持实验轻量。
- `zipf_alpha = 1.1`: 表示有热点但不过分极端的需求分布。
- `es_availability = 0.82`: 让 local / neighbor 恢复都有成功和失败的可能。
- `origin_delay = 180.0`: 让 origin 明显慢于本地和 neighbor 路径，便于看出 fallback 的价值。
- `local_es_count = 3`, `k = 3`: local 恢复不是总能成功，因此需要 fallback。
- `neighbor_group_size = 5`: neighbor 池略大，便于观察 cooperative recovery 的效果。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`: neighbor search 比 local probe 更贵，但仍可能比 origin 划算。
- `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`: neighbor recovery 比 local recovery 慢，用来反映跨边缘节点协作的额外成本。
- `seed = 20260525`: 固定随机种子，保证可以重复出同一组 baseline 结果。

### 当前限制

- 当前模型是第一阶段 Monte Carlo，不包含 queueing、request arrival process、service capacity 或 congestion。
- 当前只跑了 baseline，还没有做多次重复实验来估计置信区间。
- 目前没有引入真实 trace 或真实 CDN/edge workload。
- B2 的判断基于期望延迟，还没有考虑在线估计误差、trust score 或 neighbor 状态观测成本。

### 下一步

- 做 `origin_delay` sweep，观察 origin 变快或变慢时 B2 是否开始和 B1 拉开差距。
- 做 `es_availability` sweep，观察 neighbor 不稳定时 B2 是否能避免不值得的 neighbor search。
- 增加图表：policy metric vs origin delay、policy metric vs ES availability、B2 advantage heatmap。
- 准备给 Ueyama-sensei 的简短日文 progress memo。

## 2026-05-25：Parameter Sweep 阶段

### 本阶段主题

本阶段从单一 baseline 扩展到参数敏感性分析，重点检查 B2 的动态 fallback 判断在什么条件下可能比固定 neighbor-first 的 B1 更有意义。

### 做了什么

- 添加 `scripts/run_sweep.py`，运行两组 controlled sweep：
  - `origin_delay`: `40, 80, 120, 180, 240, 320`
  - `es_availability`: `0.45, 0.55, 0.65, 0.75, 0.82, 0.90`
- 生成 `results/sweep_summary.csv`，每个 policy 和每个 sweep 点一行。
- 扩展 `results/edge_cache_fallback_report.xlsx`，新增 `Origin Delay Sweep`、`ES Availability Sweep` 和 `B2 Advantage` 三个 sheet。
- 添加 mean response time、p95 response time、origin-free rate 和 neighbor failure rate 的折线图。
- 添加 B2 advantage 汇总，其中 `b2_advantage_vs_b1 = B1 mean response time - B2 mean response time`。

### 实验设置

两组 sweep 都使用同一个第一阶段 Monte Carlo 模型。除被 sweep 的参数外，其他参数保持 baseline：

- Number of requests: `10000`
- Zipf alpha: `1.1`
- Local ES count: `3`
- Neighbor group size: `5`
- Required chunks `K`: `3`
- Origin-delay sweep fixed ES availability: `0.82`
- ES-availability sweep fixed origin delay: `180.0`

### 初步结果

Origin-delay sweep 中，当 `origin_delay = 40` 时，B2 mean response time 为 `38.174`，B1 为 `42.210`，B2 advantage 为 `4.036`。这说明当 origin 相对较快时，B2 可以避免不必要的 neighbor search，更接近直接 origin 的选择。

在更高的 origin delay 下，B1 和 B2 的表现接近，B2 advantage 在小范围内正负波动。

ES-availability sweep 中，B1 和 B2 在所有测试 availability 上都非常接近。当前结果说明，仅改变 availability 还不足以稳定地区分 B2 和 B1。

### 初步判断

这个阶段给出了 B2 的第一条有用证据：当 origin 访问足够快，neighbor search 不一定划算时，B2 的动态判断可以减少额外搜索成本。

不过，当前 B2 规则仍然比较粗，只使用全局期望延迟比较。下一步更有研究价值的是让 B2 依赖更丰富的 local state，例如 neighbor trust、近期失败率、观测到的 neighbor response time 或 online estimate。

### 当前限制

- 每个 sweep 点只使用一个 seed，还没有量化 Monte Carlo variance。
- neighbor ES availability 仍然是同质假设。
- B2 使用全局 expected-delay comparison，还不是在线学习或 per-neighbor 状态判断。
- 目前还没有 confidence interval。

### 下一步

- 对每个 sweep 点增加 repeated trials，并报告平均值和置信区间。
- 添加 trust / availability mismatch scenario，让 B2 观察到比 B1 假设更低的 neighbor reliability。
- 添加 `origin_delay` 和 `es_availability` 的二维 heatmap，观察 B2 advantage 区域。
- 准备一版日文 progress memo，总结 baseline 和 sweep 的发现。
