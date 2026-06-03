# Edge Cache Fallback Simulation

<p align="center">
  <a href="./README.md"><img src="https://img.shields.io/badge/English-README-2563eb?style=for-the-badge" alt="English README"></a>
  <a href="./README.ch.md"><img src="https://img.shields.io/badge/%E4%B8%AD%E6%96%87-%E8%AF%B4%E6%98%8E-2563eb?style=for-the-badge" alt="中国語説明"></a>
  <a href="./README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-%E8%AA%AC%E6%98%8E-2563eb?style=for-the-badge" alt="日本語説明"></a>
</p>

このリポジトリは，低信頼な edge-cache 環境における fallback-control policy を評価するための第一段階シミュレーションです。この説明は，研究計画書を読んでいない人でも，何を目的として，どのような実験を実装し，どのように結果を読むべきかが分かるように詳しくまとめています。

## 1. この研究で扱う問題

動画配信や CDN では，すべてのユーザー要求を origin server に送ると，応答遅延が増え，core network や origin server の負荷も大きくなります。そのため，ユーザーに近い場所に edge server を配置し，可能な限り edge 側で要求を処理することが重要です。

しかし，edge server は origin server と比べて信頼性が低い場合があります。低性能なハードウェア，弱い運用環境，一時的な障害などにより，必要な chunk を提供できないことがあります。

本研究の中心的な問いは次の通りです。

> local edge server 集合だけでは要求された content を復元できない場合，システムは直接 origin に行くべきか，それとも先に近隣 edge server に協力を求めるべきか。

本研究では erasure coding を前提とします。ファイルは複数の chunk に分割され，復元には少なくとも `K` 個の chunk が必要です。現在の第一段階では `K = 3` としています。local ES から十分な chunk が得られない場合，fallback policy が次の行動を決めます。

近隣 ES への fallback は常に有効とは限りません。人気 content は Zipf 分布に従って要求されるため，近隣 ES が有用な chunk を持っている可能性があります。一方で，近隣 ES 自体の信頼性が低い場合，探索に時間を使った後に失敗し，結局 origin に戻るため，二重の遅延負担が発生します。

## 2. 現在の段階

現在の実装は **preliminary Monte Carlo simulation** です。これは完全な離散事象シミュレーションではなく，fallback-control logic の傾向を確認するための第一段階モデルです。

現在すでに実装している内容は以下の通りです。

- Zipf 分布に基づく content request の生成；
- local ES による chunk recovery の判定；
- neighbor ES による chunk recovery の判定；
- `B0`，`B1`，`B2` の三つの fallback policy；
- local ES availability と neighbor ES availability の分離；
- 三つの正式 scenario；
- repeated trials；
- mean，std，stderr，95% confidence interval の出力；
- origin delay sweep；
- ES availability sweep；
- `origin_delay x neighbor_es_availability` の二次元 grid；
- `B2 advantage vs B1` の計算；
- Nature-style の research figures；
- Excel report；
- 中国語・日本語の result interpretation；

現在まだ導入していない内容は以下の通りです。

- request arrival process；
- service capacity；
- queueing delay；
- 実際の server congestion；
- online trust learning；
- real CDN trace；
- content-level cache placement；
- cache capacity dynamics；
- cache replacement policy。

したがって，現在の `origin_delay` 増加実験は **オリジン遅延増加シナリオ** として説明すべきであり，実際の congestion model として説明してはいけません。

## 3. シミュレーションの流れ

各 request は次の流れで処理されます。

1. ユーザーがある content を要求する。
2. content は複数の chunk に分割されていると仮定する。
3. 復元には少なくとも `K` 個の chunk が必要である。
4. まず local ES 集合が十分な chunk を提供できるかを確認する。
5. local recovery が成功すれば，request は edge 側で完了する。
6. local recovery が失敗すれば，fallback policy に従って次の行動を決める。
7. policy によって，直接 origin に行く，neighbor を探索してから origin に行く，または期待遅延に基づき選択する。

今回の実装で重要なのは，可用率を二つに分けた点です。

- `local_es_availability`: local ES の可用率。
- `neighbor_es_availability`: 近隣協調グループの ES 可用率。

これにより，「local ES は通常の信頼性を持つが，近隣協調グループだけが低信頼」という条件を表現できます。この条件は，`B2` が無効な neighbor search を抑制できるかを観察するために重要です。

## 4. 三つの policy

### B0: 直接 origin fallback

`B0` は最も単純な baseline です。local ES で content を復元できない場合，不足 chunk を直接 origin から取得します。

この方式は neighbor search による無駄な遅延を避けられますが，近隣 ES が有用な chunk を持っている場合でも origin に依存してしまいます。

### B1: 固定的な neighbor-first fallback

`B1` は local recovery が失敗した後，常に近隣 ES 協調グループを探索します。neighbor recovery が成功すれば origin を使わずに完了します。neighbor recovery も失敗した場合，origin に fallback します。

neighbor ES が信頼できる場合，B1 は origin access を減らす可能性があります。一方で，neighbor ES が低信頼な場合，先に neighbor を探索し，失敗した後に origin に戻るため，二重の遅延負担が生じます。

### B2: 期待遅延に基づく近隣探索判定方式

`B2` は local recovery が失敗した後，neighbor search を常に実行するのではなく，neighbor search が有利かどうかを期待遅延で判定します。

現在の簡略モデルでは，近隣復元成功確率を次のように近似します。

```text
P_success = Pr(X >= K), where X follows a Binomial distribution
```

そして，neighbor search の期待遅延を次の式で評価します。

```text
E_neighbor =
    P_success * neighbor_recovery_delay
    + (1 - P_success) * (neighbor_probe_delay + origin_delay)
```

判定条件は次の通りです。

```text
E_neighbor <= origin_delay
```

この条件を満たす場合，B2 は neighbor search を行います。満たさない場合，直接 origin を選択します。

ここでの `P_success` は簡略化された確率モデルであり，online trust learning によって推定された値ではありません。

## 5. baseline parameter

| Parameter | Value | 説明 |
| --- | ---: | --- |
| `num_contents` | `500` | simulated content library の大きさ。 |
| `num_requests` | `10000` | default で各 trial に用いる request 数。 |
| `zipf_alpha` | `1.1` | content popularity の偏り。 |
| `local_es_availability` | `0.82` | 通常状態の local ES 可用率。 |
| `neighbor_es_availability` | default `0.82` | 通常状態の neighbor ES 可用率。scenario により変更される。 |
| `es_availability` | `0.82` | 旧 script との互換性のための field。 |
| `origin_delay` | `180.0 ms` | default の origin access delay。 |
| `local_es_count` | `3` | local ES の数。 |
| `neighbor_group_size` | `5` | 近隣協調グループの ES 数。 |
| `k` | `3` | content recovery に必要な chunk 数。 |
| `local_probe_delay` | `12.0 ms` | local probe の delay。 |
| `neighbor_probe_delay` | `28.0 ms` | neighbor probe の delay。 |
| `local_recovery_delay` | `18.0 ms` | local recovery 成功時の delay。 |
| `neighbor_recovery_delay` | `48.0 ms` | neighbor recovery 成功時の delay。 |
| `seed` | `20260525` | reproducibility のための base seed。 |

## 6. 三つの正式 scenario

第一段階では，baseline だけでなく，研究計画書に対応する三つの正式 scenario を実装しています。

| Scenario key | 外部説明 | Local availability | Neighbor availability | Origin delay | 目的 |
| --- | --- | ---: | ---: | ---: | --- |
| `steady` | 定常シナリオ | `0.82` | `0.82` | `180 ms` | 通常条件で B1/B2 が追加 overhead を生むかを確認する。 |
| `low_reliability_neighbor` | 低信頼近隣 ES シナリオ | `0.82` | `0.25` | `180 ms` | neighbor が低信頼な場合に，B2 が B1 の無効な neighbor search を抑制できるかを確認する。 |
| `origin_congestion` | オリジン遅延増加シナリオ | `0.82` | `0.82` | `320 ms` | origin path が高コストな場合に neighbor fallback が有効かを確認する。 |

`origin_congestion` は既存出力との互換性のために残している internal key です。論文，memo，報告では **オリジン遅延増加シナリオ** と書くのが正確です。現在の model は queueing や service capacity を含んでいないため，実際の congestion を再現しているわけではありません。

## 7. 実験 script の役割

### `scripts/run_experiment.py`

baseline の smoke test です。`B0`，`B1`，`B2` を一度実行し，基本的な policy-level summary を出力します。

### `scripts/run_sweep.py`

single-seed の簡易 sweep です。`origin_delay` や ES availability を変化させたときの傾向を素早く確認できます。

### `scripts/run_scenarios.py`

第一段階の三つの正式 scenario を実行する main entry point です。

- `steady`;
- `low_reliability_neighbor`;
- `origin_congestion` という internal key の origin delay increase scenario。

scenario ごと，policy ごとの repeated-trial summary と trial-level summary を出力します。

### `scripts/run_repeated.py`

より大きな repeated-trial workflow です。default では以下を実行します。

- baseline repeated trials；
- `origin_delay` sweep；
- `es_availability` sweep；
- `origin_delay x neighbor_es_availability` 二次元 grid。

default は `trials = 10` です。各 trial の seed は次のように設定します。

```text
trial_seed = base_seed + trial_index
```

これにより，reproducibility を保ちながら Monte Carlo variance と 95% confidence interval を計算できます。

### `scripts/run_memo_sweep.py`

heatmap のために追加した sensitivity sweep です。正式 scenario の parameter と完全に対応する範囲を使います。

```text
neighbor_es_availability = [0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]
origin_delay = [80, 120, 180, 240, 320]
local_es_availability = 0.82
```

この grid は以下を含みます。

- low-reliability neighbor scenario の `0.25`;
- steady scenario の `0.82 / 180`;
- origin delay increase scenario の `0.82 / 320`。

したがって，heatmap は scenario parameter の根拠を補足する sensitivity analysis として使えます。

## 8. 評価指標

| Metric | 意味 |
| --- | --- |
| `mean_response_time` | 全 request の平均応答時間。 |
| `p95_response_time` | 95 percentile response time。tail latency の確認に使う。 |
| `origin_free_rate` | origin にアクセスせずに完了した request の割合。 |
| `neighbor_failure_rate` | neighbor fallback を試した後に失敗し，origin に戻った割合。 |
| `b2_advantage_vs_b1_mean` | `B1 mean_response_time - B2 mean_response_time`。正の値は B2 が B1 より速いことを示す。 |

現在の結果は「B2 が常に勝つ」という意味ではありません。より正確には次のように読むべきです。

> B2 の価値は条件付きである。neighbor が信頼できる場合，B2 は B1 に近い挙動を示す。neighbor が低信頼な場合，B2 は無効な neighbor search を抑制し，B0 に近い挙動を示す。

そのため，baseline で B1 と B2 が似ていることは異常ではなく，B2 の decision logic と整合する自然な結果です。

## 9. Output files

| File or directory | 内容 |
| --- | --- |
| `results/summary.csv` | baseline result。policy ごとに 1 行。 |
| `results/sweep_summary.csv` | quick single-seed sweep result。 |
| `results/scenario_summary.csv` | 三つの正式 scenario の repeated-trial summary。 |
| `results/scenario_trials.csv` | 正式 scenario の trial-level policy summary。 |
| `results/repeated_summary.csv` | repeated trials の mean，std，stderr，95% CI。 |
| `results/repeated_trials.csv` | repeated experiment の trial-level summary。 |
| `results/grid_summary.csv` | `origin_delay x neighbor_es_availability` 二次元 grid。 |
| `results/memo_heatmap_summary.csv` | 正式 scenario parameter と対応する heatmap grid。 |
| `results/figures/` | Nature-style static figures。SVG，PDF，PNG，TIFF を含む。 |
| `results/edge_cache_fallback_report.xlsx` | CSV を直接読まなくても確認できる Excel report。 |
| `phase1_results.ch.md` | 中国語の第一段階 result interpretation。 |
| `phase1_results.ja.md` | 日本語の第一段階 result interpretation。 |
| `research_log.ch.md` | 中国語 research log。 |
| `research_log.ja.md` | 日本語 research log。 |

## 10. 実行方法

Python environment を作成します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

quick check:

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
```

三つの正式 scenario:

```powershell
python scripts\run_scenarios.py
```

repeated trials と grid:

```powershell
python scripts\run_repeated.py
```

heatmap sweep:

```powershell
python scripts\run_memo_sweep.py
```

figures と Excel report:

```powershell
python scripts\build_figures.py
python scripts\build_report.py
```

開発確認用の軽い実行:

```powershell
python scripts\run_scenarios.py --trials 3 --num-requests 1000
python scripts\run_repeated.py --trials 3 --num-requests 1000
```

## 11. Validation

unit tests:

```powershell
python -m unittest discover -s tests
```

test suite では以下を確認します。

- local availability と neighbor availability を別々に制御できること；
- `B2` の expected delay が neighbor availability を使うこと；
- repeated trial count が正しいこと；
- `ci95_low <= mean <= ci95_high` が成り立つこと；
- `B2 advantage` が B1/B2 の mean response time から計算されること；
- 三つの正式 scenario がすべて `B0`，`B1`，`B2` を含むこと；
- policy order が `B0`, `B1`, `B2` に固定されていること；
- heatmap sweep が正式 scenario parameter を含むこと。

## 12. 次の研究段階

現在の第一段階は，fallback-control logic の基本的な傾向を再現可能な形で示すための基礎です。次の段階では，以下のどちらを優先するかを検討する必要があります。

- content-level cache placement と cache capacity を導入する方向；
- request arrival，service capacity，queueing delay を含む full discrete-event simulation に拡張する方向。

このリポジトリは，その判断のために，実行可能な code，統計的に報告可能な results，説明可能な figures をまとめた第一段階の土台です。
