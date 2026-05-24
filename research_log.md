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

## 2026-05-25: Parameter Sweep Stage

### 本阶段主题

本阶段从单一 baseline 扩展到参数敏感性分析，重点检查 B2 的动态 fallback 判断在什么条件下可能比固定 neighbor-first 的 B1 更有意义。

### 做了什么

- Added `scripts/run_sweep.py` to run two controlled sweeps:
  - `origin_delay`: `40, 80, 120, 180, 240, 320`
  - `es_availability`: `0.45, 0.55, 0.65, 0.75, 0.82, 0.90`
- Generated `results/sweep_summary.csv` with one row per policy and sweep point.
- Extended `results/edge_cache_fallback_report.xlsx` with three new sheets:
  - `Origin Delay Sweep`
  - `ES Availability Sweep`
  - `B2 Advantage`
- Added line charts for mean response time, p95 response time, origin-free rate, and neighbor failure rate.
- Added a B2 advantage summary where `b2_advantage_vs_b1 = B1 mean response time - B2 mean response time`.

### 实验设置

Both sweeps use the same first-stage Monte Carlo model and keep the baseline settings unless the swept parameter changes:

- Number of requests: `10000`
- Zipf alpha: `1.1`
- Local ES count: `3`
- Neighbor group size: `5`
- Required chunks `K`: `3`
- Origin-delay sweep fixed ES availability: `0.82`
- ES-availability sweep fixed origin delay: `180.0`

### 初步结果

Origin-delay sweep:

- When `origin_delay = 40`, B2 mean response time was `38.174`, while B1 was `42.210`; B2 advantage was `4.036`.
- At higher origin delays, B1 and B2 stayed close. B2 advantage fluctuated between small positive and small negative values.
- Interpretation: when origin is relatively fast, B2 can avoid unnecessary neighbor search and behave closer to B0/origin choice.

ES-availability sweep:

- B1 and B2 were very close across all tested availability values.
- At low ES availability, neighbor fallback often fails, but B2 still mostly follows the same decision boundary under the current expected-delay model.
- Interpretation: this sweep shows that availability alone is not enough to strongly separate B2 from B1 under the current parameterization.

### 初步判断

This stage gives the first useful evidence for B2: it can help when origin access is fast enough that neighbor search becomes less attractive. However, the current B2 rule is still too coarse to show a stable advantage across all tested settings.

The strongest research direction now is to make B2 depend on richer or more local state, such as estimated neighbor trust, measured neighbor response time, or recent neighbor failure history. That would better match the low-trust edge-cache setting.

### 当前限制

- The sweep uses one seed per parameter point, so Monte Carlo variance is not yet quantified.
- The model still assumes homogeneous neighbor ES availability.
- B2 uses a global expected-delay comparison, not online learning or per-neighbor state.
- No confidence intervals are reported yet.

### 下一步

- Add repeated trials per sweep point and report mean plus confidence interval.
- Add a trust/availability mismatch scenario where B2 observes lower expected neighbor reliability than B1 assumes.
- Add a 2D heatmap for B2 advantage across `origin_delay` and `es_availability`.
- Prepare a short Japanese progress memo summarizing baseline and sweep findings for Ueyama-sensei.
