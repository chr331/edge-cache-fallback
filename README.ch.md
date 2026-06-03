# Edge Cache Fallback Simulation

<p align="center">
  <a href="./README.md"><img src="https://img.shields.io/badge/English-README-2563eb?style=for-the-badge" alt="English README"></a>
  <a href="./README.ch.md"><img src="https://img.shields.io/badge/%E4%B8%AD%E6%96%87-%E8%AF%B4%E6%98%8E-2563eb?style=for-the-badge" alt="中文说明"></a>
  <a href="./README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-%E8%AA%AC%E6%98%8E-2563eb?style=for-the-badge" alt="日本語説明"></a>
</p>

这个仓库是一个第一阶段研究仿真项目，用来研究低信任 edge-cache 环境下的 fallback control。这里的说明尽量从零开始写，让没有看过研究计划书的人也能知道：这个实验想解决什么问题、代码实现了什么、实验怎么跑、结果应该怎么理解。

## 1. 这个研究在问什么问题

在视频分发、CDN、边缘缓存系统里，如果所有用户请求都回到 origin server，会造成更高的延迟，也会增加核心网络和 origin 的压力。因此系统通常会在用户附近放置 edge server，让用户尽量从边缘侧拿到内容。

但是 edge server 不一定像 origin server 那么可靠。它可能运行在较便宜的硬件上，也可能部署在运维条件较弱的环境里，所以会出现暂时不可用、chunk 不完整、无法完成恢复等情况。

本研究关注的问题是：

> 当 local edge server 集合无法恢复用户请求的内容时，系统应该直接访问 origin，还是应该先去问附近的 neighbor edge server？

这里的内容恢复使用 erasure coding 的思想：一个文件被拆成多个 chunk，只要拿到至少 `K` 个 chunk 就可以恢复文件。当前第一阶段实验中，`K = 3`。如果 local ES 拿不到足够 chunk，就需要 fallback。

neighbor fallback 不是一定好。它的好处是：热门内容可能也缓存在附近的 neighbor ES 中，先问 neighbor 可能避免访问 origin。它的风险是：如果 neighbor ES 本身也不可靠，系统会先浪费时间搜索 neighbor，失败后仍然回到 origin，这会形成“双重延迟”。

## 2. 当前阶段做到了什么

当前项目是 **preliminary Monte Carlo simulation**，也就是第一阶段的初步 Monte Carlo 仿真。它的目标不是一步到位做完整离散事件仿真，而是先把 fallback 策略本身跑清楚，形成可复现、可统计、可画图、可汇报的初始证据。

当前已经实现了：

- 用 Zipf 分布模拟内容请求热度；
- 模拟 local ES 是否能提供足够 chunk；
- 模拟 neighbor ES 是否能提供足够 chunk；
- 实现 `B0`、`B1`、`B2` 三种 fallback 策略；
- 将 local ES 可用率和 neighbor ES 可用率拆开；
- 增加三个正式实验场景；
- 增加 repeated trials；
- 输出 mean、std、stderr、95% confidence interval；
- 增加 origin delay sweep；
- 增加 ES availability sweep；
- 增加 `origin_delay x neighbor_es_availability` 二维 grid；
- 计算 `B2 advantage vs B1`；
- 生成 Nature-style 图表；
- 生成 Excel 阅读入口；
- 准备中文、日文结果解读文件。

当前还没有实现：

- request arrival process；
- service capacity；
- queueing delay；
- 真实 server congestion；
- 在线 trust learning；
- 真实 CDN trace；
- content-level cache placement；
- cache capacity 动态；
- cache replacement policy。

所以需要特别注意：当前的 `origin_delay` 增大实验只能叫“origin delay increase scenario / オリジン遅延増加シナリオ”，不能说成真正模拟了 origin congestion。

## 3. 仿真系统是怎么工作的

每一个请求大致按下面流程执行：

1. 生成一个用户请求，请求某个 content。
2. 这个 content 被看作由多个 chunk 组成。
3. 系统需要至少 `K` 个 chunk 才能恢复文件。
4. 仿真先检查 local ES 集合能不能提供足够 chunk。
5. 如果 local 恢复成功，请求在边缘侧完成。
6. 如果 local 恢复失败，就进入 fallback policy。
7. 不同 policy 会决定：直接 origin、先 neighbor 再 origin、或者根据期望延迟判断。

这次代码加固里最重要的一点是拆分了两个可用率：

- `local_es_availability`：用户本地 edge server 的可用率；
- `neighbor_es_availability`：近隣协作组 edge server 的可用率。

这样就可以模拟一种更细的情况：local ES 还算正常，但 neighbor cooperative group 很不可靠。这正是观察 `B2` 是否能避免无效 neighbor search 的关键。

## 4. 三个策略具体是什么意思

### B0：直接回 origin

`B0` 是最朴素的 baseline。如果 local ES 无法恢复内容，就直接从 origin 获取缺失 chunk。

它的优点是简单，不会浪费时间搜索不可靠的 neighbor。缺点是可能过度依赖 origin，错过 edge 协作恢复的机会。

### B1：固定先搜索 neighbor

`B1` 是 static neighbor-first fallback。local 恢复失败后，它总是先搜索 neighbor cooperative ES group。如果 neighbor 能恢复，就不用访问 origin；如果 neighbor 也失败，就再访问 origin。

它在 neighbor 可靠时可能有优势，因为能减少 origin access。但在 neighbor 很不可靠时，它会先尝试 neighbor，失败后再访问 origin，导致额外延迟。

### B2：基于期望延迟的 neighbor search 判定

`B2` 是 expected-delay-based neighbor search decision。local 恢复失败后，它不是无条件搜索 neighbor，而是先估计 neighbor search 是否值得。

当前简化模型中，neighbor 恢复成功概率写成：

```text
P_success = Pr(X >= K), X 服从 Binomial 分布
```

然后计算 neighbor search 的期望延迟：

```text
E_neighbor =
    P_success * neighbor_recovery_delay
    + (1 - P_success) * (neighbor_probe_delay + origin_delay)
```

如果：

```text
E_neighbor <= origin_delay
```

就说明先搜索 neighbor 的期望延迟不高于直接 origin，`B2` 会选择 neighbor search。否则 `B2` 会直接访问 origin。

注意：这里的 `P_success` 只是第一阶段的简化概率模型，不是在线学习出来的 trust score。

## 5. baseline 参数

| 参数 | 数值 | 说明 |
| --- | ---: | --- |
| `num_contents` | `500` | 内容库大小。 |
| `num_requests` | `10000` | 默认每个 trial 的请求数。 |
| `zipf_alpha` | `1.1` | 请求热度的偏斜程度。 |
| `local_es_availability` | `0.82` | 正常 local ES 可用率。 |
| `neighbor_es_availability` | 默认 `0.82` | 正常 neighbor ES 可用率，可被场景覆盖。 |
| `es_availability` | `0.82` | 兼容旧脚本的字段。 |
| `origin_delay` | `180.0 ms` | 默认 origin 获取延迟。 |
| `local_es_count` | `3` | local ES 数量。 |
| `neighbor_group_size` | `5` | neighbor cooperative group 的 ES 数量。 |
| `k` | `3` | 恢复文件至少需要的 chunk 数。 |
| `local_probe_delay` | `12.0 ms` | local probe 延迟。 |
| `neighbor_probe_delay` | `28.0 ms` | neighbor probe 延迟。 |
| `local_recovery_delay` | `18.0 ms` | local 恢复成功时的恢复延迟。 |
| `neighbor_recovery_delay` | `48.0 ms` | neighbor 恢复成功时的恢复延迟。 |
| `seed` | `20260525` | 基础随机种子，用于复现。 |

## 6. 三个正式实验场景

第一阶段现在不再只有 baseline，而是补齐了三个正式 scenario。

| 场景 key | 对外说明 | local 可用率 | neighbor 可用率 | origin delay | 想观察什么 |
| --- | --- | ---: | ---: | ---: | --- |
| `steady` | 定常场景 | `0.82` | `0.82` | `180 ms` | 正常环境下，B1/B2 是否会带来额外开销。 |
| `low_reliability_neighbor` | 低信頼近隣 ES 场景 | `0.82` | `0.25` | `180 ms` | neighbor 不可靠时，B2 是否能避免 B1 的无效搜索。 |
| `origin_congestion` | origin delay increase 场景 | `0.82` | `0.82` | `320 ms` | origin 路径变慢时，neighbor fallback 是否更有价值。 |

`origin_congestion` 是代码里的兼容 key。写论文、memo、汇报时应该说“origin delay increase / オリジン遅延増加”，因为当前只是把 `origin_delay` 增大，并没有模拟 queueing 或真实拥塞。

## 7. 实验脚本做了什么

### `scripts/run_experiment.py`

这是最简单的 baseline smoke test。它跑一次 baseline，对 `B0`、`B1`、`B2` 输出基本指标，用来确认仿真流程能跑通。

### `scripts/run_sweep.py`

这是快速 single-seed sweep。它保留了早期快速检查用的 sweep 入口，可以快速看 `origin_delay` 或 ES availability 改变时策略趋势是否合理。

### `scripts/run_scenarios.py`

这是第一阶段三个正式场景的主入口。它会跑：

- `steady`;
- `low_reliability_neighbor`;
- `origin_congestion` 这个内部 key，对外解释为 origin delay increase。

输出包括每个 policy 的 repeated-trial 汇总，以及每个 trial 的原始 policy-level summary。

### `scripts/run_repeated.py`

这是更完整的 repeated trials 和 sensitivity sweep 入口。默认会跑：

- baseline repeated trials；
- `origin_delay` sweep；
- `es_availability` sweep；
- `origin_delay x neighbor_es_availability` 二维 grid。

默认 `trials = 10`。每次 trial 的 seed 采用：

```text
trial_seed = base_seed + trial_index
```

这样既能复现，又能计算 Monte Carlo 方差和 95% confidence interval。

### `scripts/run_memo_sweep.py`

这是为了 heatmap 单独补的 sweep。它的参数和正式场景对齐：

```text
neighbor_es_availability = [0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]
origin_delay = [80, 120, 180, 240, 320]
local_es_availability = 0.82
```

它覆盖了：

- low-reliability neighbor 的 `0.25`;
- steady 的 `0.82 / 180`;
- origin delay increase 的 `0.82 / 320`。

所以 heatmap 不是另起炉灶，而是用来说明正式场景参数所在的敏感性区域。

## 8. 评价指标怎么理解

| 指标 | 含义 |
| --- | --- |
| `mean_response_time` | 所有请求的平均响应时间。 |
| `p95_response_time` | 95 分位响应时间，用来看 tail latency。 |
| `origin_free_rate` | 不访问 origin 就完成请求的比例。 |
| `neighbor_failure_rate` | 尝试 neighbor fallback 后仍然失败、最后回 origin 的比例。 |
| `b2_advantage_vs_b1_mean` | `B1 mean_response_time - B2 mean_response_time`。正数表示 B2 比 B1 更快。 |

目前结果的核心不是“B2 永远赢”，而是：

> B2 的价值是条件性的。neighbor 可靠时，B2 通常接近 B1；neighbor 不可靠时，B2 会更接近 B0，避免 B1 的无效 neighbor search。

所以 baseline 里 B1 和 B2 很接近不是错误，而是符合 B2 判定逻辑的正常结果。

## 9. 输出文件说明

| 文件或目录 | 内容 |
| --- | --- |
| `results/summary.csv` | baseline 结果，每个 policy 一行。 |
| `results/sweep_summary.csv` | 快速 single-seed sweep 结果。 |
| `results/scenario_summary.csv` | 三个正式场景的 repeated-trial 汇总。 |
| `results/scenario_trials.csv` | 三个正式场景中每个 trial 的 policy summary。 |
| `results/repeated_summary.csv` | repeated trials 的 mean、std、stderr、95% CI。 |
| `results/repeated_trials.csv` | repeated 实验的每个 trial summary。 |
| `results/grid_summary.csv` | `origin_delay x neighbor_es_availability` 二维 grid。 |
| `results/memo_heatmap_summary.csv` | 与正式场景参数对齐的 heatmap grid。 |
| `results/figures/` | Nature-style 静态图表，包含 SVG、PDF、PNG、TIFF。 |
| `results/edge_cache_fallback_report.xlsx` | Excel 阅读入口，方便不直接看 CSV。 |
| `phase1_results.ch.md` | 中文第一阶段结果解读。 |
| `phase1_results.ja.md` | 日文第一阶段结果解读。 |
| `research_log.ch.md` | 中文研究日志。 |
| `research_log.ja.md` | 日文研究日志。 |

## 10. 如何运行

创建环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

快速检查：

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
```

运行三个正式场景：

```powershell
python scripts\run_scenarios.py
```

运行 repeated trials 和 grid：

```powershell
python scripts\run_repeated.py
```

运行 heatmap sweep：

```powershell
python scripts\run_memo_sweep.py
```

生成图表和 Excel：

```powershell
python scripts\build_figures.py
python scripts\build_report.py
```

开发时可以用小规模：

```powershell
python scripts\run_scenarios.py --trials 3 --num-requests 1000
python scripts\run_repeated.py --trials 3 --num-requests 1000
```

## 11. 如何验证

运行测试：

```powershell
python -m unittest discover -s tests
```

测试覆盖了：

- local 和 neighbor availability 是否能分别控制；
- `B2` 是否使用 neighbor availability 估计 expected delay；
- repeated trial count 是否正确；
- CI 是否满足 `ci95_low <= mean <= ci95_high`；
- `B2 advantage` 是否由 B1/B2 的 mean response time 计算；
- 三个正式场景是否都包含 `B0`、`B1`、`B2`；
- policy 顺序是否保持 `B0`, `B1`, `B2`；
- heatmap sweep 是否覆盖正式场景参数。

## 12. 下一步研究方向

当前第一阶段的作用是证明 fallback control 的基本逻辑和条件性趋势。下一步需要决定优先扩展哪条线：

- 加入 content-level cache placement 和 cache capacity；
- 或者加入 request arrival、service capacity、queueing delay，做完整 discrete-event simulation。

这个仓库现在提供的是第一阶段的稳定基础：代码能跑、结果可复现、统计能汇报、图表能解释。
