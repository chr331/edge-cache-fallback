# Research Log

## 2026-05-25

### 本阶段主题

本阶段完成了低信任 edge-cache 环境下 fallback-control 研究的第一版可复现实验脚手架。目标不是先追求复杂模型，而是先把 B0/B1/B2 三种策略跑通、记录关键指标，并建立“仿真 -> 结果 -> 图表/Excel -> 研究说明 -> GitHub 备份”的基础流程。

### 做了什么

- Project scaffold: 整理了 Python 项目结构，新增 `src/edge_cache_sim/`、`scripts/`、`tests/` 和 `results/`。
- Simulation model: 实现了第一阶段 Monte Carlo 仿真模型，用随机请求和 ES 可用性模拟 local recovery、neighbor fallback 和 origin fallback。
- Policy comparison: 实现并比较三种策略：
  - `B0`: local ES 失败后直接回 origin。
  - `B1`: local ES 失败后先搜索 neighbor ES，neighbor 失败后再回 origin。
  - `B2`: local ES 失败后比较 neighbor-search 的期望延迟和 origin 延迟，选择期望延迟更低的动作。
- Result output: 生成 `results/summary.csv` 作为可复现实验数据源。
- Readable report: 生成 `results/edge_cache_fallback_report.xlsx`，包含 Overview、Parameters、Summary 和 Charts 四个 sheet，用来替代直接阅读裸 CSV。
- Verification: 添加 5 个单元测试，覆盖 local success、B0 fallback、B1 neighbor recovery、B2 origin choice 和三策略 summary 输出。
- GitHub: 创建公开仓库 `chr331/edge-cache-fallback`，并将第一版代码、README、研究日志和示例 CSV 推送到 `main`。

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

Baseline 结果如下：

- `B0`: mean response time `101.247`, p95 `201.405`, origin-free rate `0.5503`, neighbor failure rate `0.0000`
- `B1`: mean response time `45.214`, p95 `70.844`, origin-free rate `0.9790`, neighbor failure rate `0.0468`
- `B2`: mean response time `45.170`, p95 `70.909`, origin-free rate `0.9788`, neighbor failure rate `0.0474`

### 初步判断

Neighbor fallback 在 baseline 参数下明显有效。与 B0 相比，B1/B2 大幅减少了访问 origin 的比例，也降低了平均响应时间和 p95 响应时间。

B2 在这一组参数下没有明显优于 B1，主要原因是当前 baseline 中 neighbor ES 可用性较高、origin delay 较大，因此 neighbor search 几乎总是值得尝试。换句话说，这组参数更适合证明“neighbor fallback 有价值”，但还不足以突出 B2 的动态选择优势。

### 当前限制

- 当前模型是第一阶段 Monte Carlo，不包含 queueing、request arrival process、service capacity 或 congestion。
- 当前只跑了 baseline，还没有做参数敏感性分析。
- 目前没有引入真实 trace 或真实 CDN/edge workload。
- B2 的判断基于期望延迟，还没有考虑在线估计误差、trust score 或 neighbor 状态观测成本。

### 下一步

- 做 `origin_delay` sweep，观察 origin 变快或变慢时 B2 是否开始和 B1 拉开差距。
- 做 `es_availability` sweep，观察 neighbor 不稳定时 B2 是否能避免不值得的 neighbor search。
- 增加图表：policy metric vs origin delay、policy metric vs ES availability、B2 advantage heatmap。
- 准备一版给 Ueyama-sensei 的简短日文 progress memo，说明已经完成 baseline simulation，并询问下一步参数设定是否合理。
