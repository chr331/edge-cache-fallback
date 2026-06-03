# 研究日志

## 2026-05-25：Baseline 与 sweep 基础

### 本阶段主题

本阶段完成低信任 edge-cache fallback-control 研究的第一版可复现实验框架。目标是先确认 `B0`、`B1`、`B2` 三种 fallback 策略的行为、指标和输出流程稳定，而不是一开始就加入队列、拥塞、真实 trace 或 trust-learning。

### 做了什么

- 建立 `src/edge_cache_sim/`、`scripts/`、`tests/`、`results/` 的项目结构。
- 实现第一阶段 Monte Carlo 仿真模型，用随机请求和 ES 可用性模拟 local recovery、neighbor fallback 和 origin fallback。
- 实现并比较三种策略：
  - `B0`: local ES 失败后直接回 origin。
  - `B1`: local ES 失败后先尝试 neighbor ES，neighbor 失败后再回 origin。
  - `B2`: local ES 失败后比较 neighbor-search 的期望延迟和直接 origin 延迟，选择期望延迟更低的动作。
- 生成 `results/summary.csv` 作为 baseline 数据源。
- 生成 `results/sweep_summary.csv`，覆盖 `origin_delay` 与 `es_availability` 两组 sensitivity sweep。
- 生成 `results/edge_cache_fallback_report.xlsx`，用 Excel 替代直接阅读 CSV 的体验。

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

### 为什么加入 jitter

响应时间中加入小幅正向随机抖动，是为了避免所有路径的 latency 完全 deterministic。真实 edge-cache 系统里，即使同一条路径也会受到调度、网络波动、序列化开销等因素影响；如果每条路径都是固定延迟，p95 等 tail-latency 指标会显得过于整齐。

当前 jitter 很小，只是在每条路径的基础延迟上加入 gamma 分布产生的正向波动。它的目的不是改变哪种策略更快的主判断，而是让 repeated trials 和 p95 指标更接近真实系统中的轻微波动。

### 参数设定说明

- `num_requests = 10000`: 默认样本量足够大，mean 和 p95 比较稳定。
- `num_contents = 500`: 内容空间适中，便于观察 Zipf 热点分布，同时保持实验轻量。
- `zipf_alpha = 1.1`: 表示有热点但不过分极端的请求分布。
- `es_availability = 0.82`: 让 local / neighbor recovery 都有成功和失败的可能。
- `origin_delay = 180.0`: 让 origin 明显慢于 local 和 neighbor 路径，便于观察 fallback 价值。
- `local_es_count = 3`, `k = 3`: local recovery 不是总能成功，因此需要 fallback。
- `neighbor_group_size = 5`: neighbor pool 略大，用于观察 cooperative recovery 的收益。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`: neighbor search 比 local probe 更贵，但仍可能比 origin 划算。
- `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`: neighbor recovery 比 local recovery 慢，用来反映跨边缘节点协作的额外成本。
- `seed = 20260525`: 固定随机种子，保证 baseline 和 sweep 可复现。

## 2026-05-25：第一阶段统计加固

### 本阶段主题

这一阶段把第一阶段从“baseline 和 sweep 能跑”推进到“可以统计汇报”。重点是 repeated trials、confidence interval、二维 `B2 advantage` heatmap 数据，以及 Excel 报告入口。Ueyama-sensei memo 暂停，先只做代码、结果、图表和日志数据基础。

### 做了什么

- 先备份当前 GitHub 远端 `main` 到私有仓库 `chr331/edge-cache-fallback-backup-20260525`。
- 将 `research_log.md` 保留为中日研究日志索引。
- 保留 `_with_jitter()` 的 docstring，说明 latency 抖动的模型含义。
- 新增 `src/edge_cache_sim/repeated.py`，集中处理 repeated-trial 聚合、标准误和 95% confidence interval。
- 新增 `scripts/run_repeated.py`，作为第一阶段正式统计入口。
- 保留 `scripts/run_experiment.py` 和 `scripts/run_sweep.py` 作为快速 smoke test。
- 将核心仿真、sweep 和 repeated 输出从 pandas 依赖改为标准库 CSV 写出，降低运行环境要求。
- 扩展 `scripts/build_report.py`，增加 `Repeated Trials` 与 `B2 Advantage Grid` sheet。
- 增加 repeated-trial 单元测试，覆盖 trial count、CI 列、B2 advantage 计算和固定 seed 可复现性。

### repeated trials 设置

默认 `trials = 10`。每个 trial 的 seed 使用：

```text
trial_seed = base_seed + trial_index
```

对每个 scenario / policy / 参数点，输出以下统计：

- `mean`
- `std`
- `stderr`
- `ci95_low`
- `ci95_high`

当前 95% confidence interval 使用：

```text
mean +/- 1.96 * stderr
```

### sweep 与 grid 设置

保留两组一维 sweep：

- `origin_delay`: `40, 80, 120, 180, 240, 320`
- `es_availability`: `0.45, 0.55, 0.65, 0.75, 0.82, 0.90`

新增二维 grid：

```text
origin_delay x es_availability
```

B2 相对 B1 的优势定义为：

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

该值为正时，表示 B2 的平均响应时间低于 B1。

### 输出文件

- `results/repeated_summary.csv`: repeated-trial 汇总。
- `results/grid_summary.csv`: 二维 grid 汇总。
- `results/repeated_trials.csv`: 每个 trial 的 policy-level summary。
- `results/edge_cache_fallback_report.xlsx`: 阅读入口，包含 repeated summary 和 B2 advantage grid。

### 当前阶段判断

第一阶段代码层面的主要缺口已经补上：现在不仅能跑 baseline 和单 seed sweep，也能汇报 Monte Carlo variance、confidence interval 和二维参数区域下的 B2 advantage。本阶段已用默认 `trials = 10`、`num_requests = 10000` 生成 `repeated_summary.csv`、`grid_summary.csv` 和 `repeated_trials.csv`，并重新生成 Excel 报告。下一步是检查 heatmap 中 B2 明显优于 B1 的区域，再决定是否写正式进度 memo。

## 2026-05-25：第一阶段图表与结果解释

### 本阶段主题

这一阶段把已生成的 repeated-trial 和 grid 结果整理成 Nature-style 静态图表，并写出中日双语结果解读。重点不是新增模型，而是把第一阶段结果转成可读、可汇报、可复查的材料。

### 做了什么

- 安装并记录 `matplotlib` 依赖，用 Python 绘制图表。
- 新增 `scripts/build_figures.py`，从 `results/repeated_summary.csv` 和 `results/grid_summary.csv` 读取数据。
- 生成 baseline mean、baseline p95、origin-delay sweep、ES-availability sweep 和 B2 advantage heatmap。
- 每张图输出 `.svg`、`.pdf`、`.png` 和 `.tiff`，其中 `.svg` 保留可编辑文字。
- 新增 `phase1_results.ch.md` 和 `phase1_results.ja.md`，解释实验设置、repeated trials、confidence interval、B2 advantage 和当前限制。

### 当前结果判断

baseline 下，`B1` 与 `B2` 的平均响应时间几乎相同：`B1 = 44.8589`，`B2 = 44.8391`，B2 相对 B1 的 advantage 只有 `0.0198`。因此 baseline 下不能夸大 B2，只能说 B2 维持了与 B1 接近的性能。

二维 grid 中，36 个参数点里有 20 个点的 B2 advantage 为正。最大优势出现在 `origin_delay = 40.0`、`es_availability = 0.45`，为 `18.0856`。这说明 B2 的主要价值在于：当 origin 较快、neighbor 可用性较低时，B2 能避免 B1 固定搜索 neighbor 带来的额外延迟。

### 下一步

下一步可以基于 `phase1_results.ch.md` 和 `phase1_results.ja.md` 写一版给 Ueyama-sensei 的简短 progress memo。memo 应保持谨慎表达，强调第一阶段仿真和统计流程已经稳定，而不是把 B2 说成最终最优策略。

## 2026-05-25：第一阶段三场景补齐

### 本阶段主题

这一阶段把第一阶段结果从 baseline / sweep 扩展到研究计划书中的三个正式场景：定常シナリオ、低信頼近隣ESシナリオ和オリジン遅延増加シナリオ。目标是让第一阶段不仅“能跑”，而且能和研究计划书中的评价设计一一对应。代码里仍保留 `origin_congestion` 作为兼容旧输出的内部 key，但汇报口径不把它写成真实的拥塞或队列模型。

### 做了什么

- 将 local ES availability 和 neighbor ES availability 拆开。`es_availability` 继续作为兼容字段，`neighbor_es_availability` 用于单独控制近隣 ES 协调组可靠性。
- 新增 `src/edge_cache_sim/scenarios.py`，集中定义 `steady`、`low_reliability_neighbor`、`origin_congestion` 三个正式场景；其中 `origin_congestion` 是内部 key，对外对应オリジン遅延増加シナリオ。
- 新增 `scripts/run_scenarios.py`，输出 `results/scenario_summary.csv` 和 `results/scenario_trials.csv`。
- 更新 `scripts/build_figures.py`，新增三场景 mean response time、三场景 p95 response time、低信任 neighbor 场景 rates 图。
- 更新 `scripts/build_report.py`，在 Excel 报告中加入 `Formal Scenarios` sheet。
- 更新 `README.md`、`README.ch.md`、`README.ja.md` 和 `phase1_results.ch.md`、`phase1_results.ja.md`，说明三场景、`neighbor_es_availability`、结果解释和当前限制。
- 增加单元测试，覆盖 local / neighbor availability 分离、B2 expected delay 使用 neighbor availability、低信任 neighbor 下 B2 抑制无效搜索、三场景 policy 顺序和 CI 合法性。

### 三场景设置

- `steady`: local 和 neighbor 都使用正常可用率 `0.82`，origin delay 为 `180.0`。
- `low_reliability_neighbor`: local 保持 `0.82`，neighbor 降到 `0.25`，origin delay 为 `180.0`。
- `origin_congestion`: local 和 neighbor 都保持 `0.82`，origin delay 提高到 `320.0`。这是オリジン遅延増加シナリオ，不是真实拥塞队列模型。

### 当前结果判断

`steady` 场景下，`B1` 和 `B2` 接近是正常结果。`B2` 相对 `B1` 的 mean response time advantage 只有 `0.0198`，说明 neighbor 可靠时，B2 的判断基本会和 B1 一样选择 neighbor fallback。

`low_reliability_neighbor` 场景是本次补齐后最关键的结果。`B1` 的 neighbor failure rate 达到 `0.89777`，mean response time 为 `106.5593`，p95 response time 为 `229.0214`。`B2` 基本避免了无效 neighbor search，mean response time 降到 `100.7891`，p95 response time 降到 `201.3767`，相对 `B1` 的 mean response time advantage 为 `5.7702`。

オリジン遅延増加シナリオ下，`B0` 因 origin delay 增大明显变差，mean response time 达到 `163.6239`。`B1` 和 `B2` 都能利用可靠 neighbor，平均响应时间约为 `47.6`，明显优于 `B0`，但二者差距仍然很小。

### 第一阶段状态

从代码、结果、图表和说明文件角度看，第一阶段已经达到“可汇报”的收尾状态。当前交付物包括三场景 repeated results、sensitivity / grid 数据、confidence interval、Nature-style 图表、Excel 阅读入口，以及中日双语结果解读。

下一步可以进入 Ueyama-sensei progress memo 草稿阶段。memo 中需要明确说明：当前是 preliminary Monte Carlo simulation，不是完整 discrete-event simulation；`B2` 的主要价值不是在所有场景中显著超过 `B1`，而是在低信任 neighbor ES 条件下避免无效 fallback。

## 2026-05-26：第一阶段日文进捗メモ与 memo 用 heatmap

### 本阶段主题

这一阶段把第一阶段结果整理成给 Ueyama-sensei 的严格两页日文进捗メモ草稿，并补跑与三场景参数完全对齐的 memo 专用 sensitivity sweep。目标是让 memo 既能展示三场景主结果，也能用 heatmap 说明参数选择和 B2 有效区域不是随意选取。

### 做了什么

- 新增 `src/edge_cache_sim/memo_sweep.py` 和 `scripts/run_memo_sweep.py`，固定 local ES 可用率为 `0.82`，扫描近隣 ES 可用率 `[0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]` 与 origin delay `[80, 120, 180, 240, 320]`。
- 生成 `results/memo_heatmap_summary.csv`，覆盖低信頼近隣 ES 场景的 `0.25`、定常シナリオ的 `0.82 / 180`，以及オリジン遅延増加シナリオ的 `0.82 / 320`。
- 更新 `scripts/build_figures.py`，新增 memo 用 mean response time、p95 response time 和 B2 advantage heatmap 小图，并将 heatmap 纵轴统一为 `neighbor ES availability`。
- 新增 `memo/phase1_progress_memo_ja.tex`，使用 LuaLaTeX + `jlreq` 的日文 LaTeX 结构，正文明确写成 preliminary Monte Carlo simulation。
- 在 README、结果解读和研究日志中统一口径：第三场景对外写成オリジン遅延増加シナリオ，`origin_congestion` 仅保留为内部兼容 key。

### 当前限制

本机当前没有可用的 LuaLaTeX / TeX Live 环境，因此 `.tex` 源文件和 memo 用 PDF 图已经准备好，但 memo 主 PDF 尚未在本机成功编译。需要安装或配置 Japanese LaTeX 环境后再做最终版面确认。

## 2026-06-03：Phase 1.1 项目整理、request-level B2 与 Zipf 敏感性分析

### 本阶段主题

这一阶段把仓库整理成更容易持续更新的结构，并针对前一版 B2 “结果不够明显、Zipf 参数缺少敏感性分析”的问题做第一轮加固。重点不是声称 B2 已经是最终最优策略，而是让 B2 的判断从场景级固定选择变成 request-level 选择，使其能够根据 content rank、local 缺失 chunk 数和 neighbor 成功概率做出不同动作。

### 做了什么

- 新增 `docs/project_map.md`，说明 README、docs、scripts、src、tests、results、memo、overleaf 各自负责什么。
- 新增 `docs/experiment_guide.md`，写清楚 Phase 1.1 的运行命令、输出文件和指标含义。
- 新增 `CHANGELOG.md` 和 `scripts/write_manifest.py`，让每次结果批次都能记录更新时间、命令、参数、git 状态和输出文件。
- 将新结果统一放到 `results/phase1_b2_zipf/`，保留旧结果结构，避免破坏已有 memo 和 Overleaf 链接。
- 将 B2 改为 request-level decision：使用 `missing_chunks = K - local_chunks`，并用 content rank 估计 neighbor cache probability。
- 新增 `neighbor_cache_hot_prob = 0.90`、`neighbor_cache_cold_prob = 0.15`、`neighbor_cache_rank_gamma = 1.0` 三个默认参数。
- 新增 `scripts/run_b2_zipf_sweep.py`，覆盖 `neighbor_es_availability x origin_delay` 和 `zipf_alpha x neighbor_cache_rank_gamma` 两类 sensitivity analysis。
- 重画 Phase 1.1 图，主要版本化 SVG/PDF；PNG/TIFF 仅作为本地 QA 预览。

### 正式结果判断

正式批次使用 `trials = 10`、`num_requests = 10000`。三场景中，B2 相对 B1 的 mean response time advantage 分别为：`steady = 0.2746 ms`、`low_reliability_neighbor = 1.5561 ms`、`origin_congestion = 0.0769 ms`。这说明三场景柱状图里 B2 的差异仍然不是特别夸张，不能单靠三场景图声称 B2 显著优越。

更重要的结果来自 sensitivity 和 rank-bucket 图。`neighbor_es_availability x origin_delay` heatmap 中，最大 B2 advantage 为 `6.626 ms`，出现在 `neighbor_es_availability = 0.20`、`origin_delay = 80 ms`。这表明当 B1 的固定 neighbor search 容易变成额外开销时，B2 的抑制机制最明显。

`zipf_alpha x neighbor_cache_rank_gamma` heatmap 中，B2 advantage 随 `neighbor_cache_rank_gamma` 增大而更明显，最大值为 `3.904 ms`。rank-bucket 图显示，B2 对 hot content 的 neighbor choice rate 约为 `0.6823`，而 mid / cold bucket 为 `0.0`。这直接说明 Phase 1.1 的 B2 已经不是“永远搜索 neighbor”，而是主要把 neighbor search 留给热门内容。

### 验证

- `python -m unittest discover -s tests`：17 个测试通过。
- 正式运行：
  - `python scripts/run_scenarios.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf`
  - `python scripts/run_b2_zipf_sweep.py --trials 10 --num-requests 10000 --output-dir results/phase1_b2_zipf`
  - `python scripts/build_figures.py --results-dir results/phase1_b2_zipf`

### 当前限制与下一步

当前仍是 Monte Carlo 第一阶段，不包含 request arrival、queueing delay、service capacity、真实 CDN trace 或在线 trust learning。B2 的概率模型虽然比简单二项分布更有解释性，但仍然是人为设定的 rank-aware probability model。下一步可以考虑在不进入完整离散事件仿真之前，先把 B2 的概率估计扩展为更可辩护的模型，例如基于历史观测的 Beta-Binomial / Bayesian update，或把 cache placement 与 content popularity 显式连接起来。
