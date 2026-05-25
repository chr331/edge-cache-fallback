# 研究ログ

## 2026-05-25：Baseline と sweep の基盤

### 本段階のテーマ

本段階では、低信頼 edge-cache 環境における fallback-control 研究の再現可能な第一版実験基盤を作成しました。目的は、最初から queueing、congestion、real trace、trust-learning を入れることではなく、まず `B0`、`B1`、`B2` の fallback policy、評価指標、出力フローを安定させることです。

### 実施内容

- `src/edge_cache_sim/`、`scripts/`、`tests/`、`results/` の project structure を整理しました。
- 第一段階の Monte Carlo simulation model を実装し、random requests と ES availability により local recovery、neighbor fallback、origin fallback を模擬しました。
- 三つの policy を実装して比較しました。
  - `B0`: local ES が失敗した後、直接 origin に戻ります。
  - `B1`: local ES が失敗した後、まず neighbor ES を試し、neighbor も失敗したら origin に戻ります。
  - `B2`: local ES が失敗した後、neighbor-search の期待遅延と直接 origin delay を比較し、期待遅延が小さい行動を選びます。
- `results/summary.csv` を baseline data source として生成しました。
- `results/sweep_summary.csv` を生成し、`origin_delay` と `es_availability` の sensitivity sweep を実行しました。
- `results/edge_cache_fallback_report.xlsx` を生成し、CSV を直接読む代わりに Excel で確認できるようにしました。

### 実験設定

- Scenario: `baseline`
- Number of requests: `10000`
- Zipf alpha: `1.1`
- ES availability: `0.82`
- Origin delay: `180.0`
- Local ES count: `3`
- Neighbor group size: `5`
- Required chunks `K`: `3`
- Random seed: `20260525`

### なぜ jitter を入れるか

応答時間に小さな正方向の random jitter を入れているのは、すべての経路の latency が完全に deterministic になることを避けるためです。実際の edge-cache system では、同じ経路でも scheduling、network fluctuation、serialization cost などにより少しずつ遅延が変わります。すべてを固定遅延にすると、p95 などの tail-latency 指標が不自然に整いすぎます。

現在の jitter は小さく、各経路の base delay に gamma distribution 由来の正方向の揺らぎを足すだけです。目的は、どの policy が速いかという主な判断を変えることではなく、repeated trials と p95 指標を現実の軽い変動に近づけることです。

### パラメータ設定の意図

- `num_requests = 10000`: デフォルトの sample size として十分で、mean と p95 を安定させます。
- `num_contents = 500`: 中程度の content space とし、Zipf の人気分布を観察しつつ実験を軽く保ちます。
- `zipf_alpha = 1.1`: 人気の偏りはあるが極端すぎない demand distribution を表します。
- `es_availability = 0.82`: local / neighbor recovery の成功と失敗が両方出るようにします。
- `origin_delay = 180.0`: origin を local と neighbor 経路より明確に遅くし、fallback の価値を見やすくします。
- `local_es_count = 3`, `k = 3`: local recovery が常に成功しないため、fallback が必要になります。
- `neighbor_group_size = 5`: neighbor pool を少し大きくし、cooperative recovery の効果を観察します。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`: neighbor search は local probe より高コストですが、origin より有利な場合があります。
- `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`: neighbor recovery は local recovery より遅く、edge nodes 間協調の追加コストを表します。
- `seed = 20260525`: random seed を固定し、baseline と sweep の再現性を確保します。

## 2026-05-25：第一段階の統計強化

### 本段階のテーマ

この段階では、第一段階を「baseline と sweep が実行できる」状態から「統計的に報告できる」状態へ進めました。焦点は repeated trials、confidence interval、二次元 `B2 advantage` heatmap data、Excel report の入口です。Ueyama-sensei 向け memo は一時停止し、まず code、results、figures、research log の基盤だけを整えます。

### 実施内容

- 現在の GitHub remote `main` を private backup repository `chr331/edge-cache-fallback-backup-20260525` に保存しました。
- `research_log.md` は中国語・日本語の research log index として保持しました。
- `_with_jitter()` の docstring を残し、latency jitter の model 上の意味を明示しました。
- `src/edge_cache_sim/repeated.py` を追加し、repeated-trial aggregation、standard error、95% confidence interval をまとめました。
- `scripts/run_repeated.py` を追加し、第一段階の正式な統計実行入口としました。
- `scripts/run_experiment.py` と `scripts/run_sweep.py` は quick smoke test として残しました。
- core simulation、sweep、repeated output は pandas 依存を避け、standard-library CSV output に変更しました。
- `scripts/build_report.py` を拡張し、`Repeated Trials` と `B2 Advantage Grid` sheet を追加しました。
- repeated-trial unit tests を追加し、trial count、CI columns、B2 advantage calculation、fixed-seed reproducibility を確認しました。

### repeated trials の設定

デフォルトは `trials = 10` です。各 trial の seed は次の形で設定します。

```text
trial_seed = base_seed + trial_index
```

各 scenario / policy / parameter point について、次の統計量を出力します。

- `mean`
- `std`
- `stderr`
- `ci95_low`
- `ci95_high`

現在の 95% confidence interval は次の式で計算します。

```text
mean +/- 1.96 * stderr
```

### sweep と grid の設定

一次元 sweep は二つ残しています。

- `origin_delay`: `40, 80, 120, 180, 240, 320`
- `es_availability`: `0.45, 0.55, 0.65, 0.75, 0.82, 0.90`

新しく二次元 grid を追加しました。

```text
origin_delay x es_availability
```

B2 の B1 に対する advantage は次のように定義します。

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

この値が正であれば、B2 の mean response time が B1 より低いことを意味します。

### 出力ファイル

- `results/repeated_summary.csv`: repeated-trial summary。
- `results/grid_summary.csv`: 二次元 grid summary。
- `results/repeated_trials.csv`: trial ごとの policy-level summary。
- `results/edge_cache_fallback_report.xlsx`: repeated summary と B2 advantage grid を含む読み取り用入口。

### 現在の判断

第一段階の code 側の主な不足は補強できました。現在は baseline と single-seed sweep だけでなく、Monte Carlo variance、confidence interval、二次元パラメータ領域における B2 advantage も報告できます。本段階ではデフォルトの `trials = 10`、`num_requests = 10000` で `repeated_summary.csv`、`grid_summary.csv`、`repeated_trials.csv` を生成し、Excel report も再生成しました。次は heatmap 上で B2 が B1 より明確に有利な領域を確認してから、正式な progress memo を書く段階です。
