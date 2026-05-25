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

## 2026-05-25：第一段階の figures と結果解釈

### 本段階のテーマ

この段階では、すでに生成した repeated-trial と grid の結果を Nature-style の static figures に整理し、中国語・日本語の結果解釈文書を作成しました。目的は新しい model を追加することではなく、第一段階の結果を読みやすく、報告しやすく、再確認しやすい形にすることです。

### 実施内容

- `matplotlib` dependency を追加し、Python で figures を作成できるようにしました。
- `scripts/build_figures.py` を追加し、`results/repeated_summary.csv` と `results/grid_summary.csv` を入力として使うようにしました。
- baseline mean、baseline p95、origin-delay sweep、ES-availability sweep、B2 advantage heatmap を生成しました。
- 各 figure は `.svg`、`.pdf`、`.png`、`.tiff` として保存しました。`.svg` は editable text を保持します。
- `phase1_results.ch.md` と `phase1_results.ja.md` を追加し、実験設定、repeated trials、confidence interval、B2 advantage、現在の制限を説明しました。

### 現在の結果判断

baseline では、`B1` と `B2` の mean response time はほぼ同じです。`B1 = 44.8589`、`B2 = 44.8391` であり、B2 の B1 に対する advantage は `0.0198` にとどまります。そのため、baseline だけで B2 が明確に優れているとは言えず、B2 は B1 と同程度の性能を維持していると解釈するのが適切です。

二次元 grid では、36 個の parameter points のうち 20 点で B2 advantage が正でした。最大 advantage は `origin_delay = 40.0`、`es_availability = 0.45` のときの `18.0856` です。これは、origin が速く neighbor availability が低い場合に、B2 が B1 の固定的な neighbor-search cost を避けられることを示しています。

### 次の段階

次は `phase1_results.ch.md` と `phase1_results.ja.md` をもとに、Ueyama-sensei 向けの短い progress memo draft を作成できます。memo では、B2 を最終的に最適な policy と主張するのではなく、第一段階の simulation と統計処理の流れが整ったことを中心に説明するのが安全です。

## 2026-05-25：第一段階の三シナリオ補完

### 本段階のテーマ

この段階では、第一段階の結果を baseline / sweep から、研究計画書に対応する三つの正式 scenario へ拡張しました。対象は、定常シナリオ、低信頼近隣ESシナリオ、オリジン遅延増加シナリオです。目的は、第一段階の結果を研究計画書の評価設計と対応させることです。code では互換性のために `origin_congestion` という内部 key を残していますが、報告では実際の queueing congestion model とは区別します。

### 実施内容

- local ES availability と neighbor ES availability を分離しました。`es_availability` は互換性のために残し、`neighbor_es_availability` で近隣 ES 協調グループの信頼性を個別に制御できるようにしました。
- `src/edge_cache_sim/scenarios.py` を追加し、`steady`、`low_reliability_neighbor`、`origin_congestion` の三つの正式 scenario を定義しました。`origin_congestion` は内部 key であり、対外的にはオリジン遅延増加シナリオとして扱います。
- `scripts/run_scenarios.py` を追加し、`results/scenario_summary.csv` と `results/scenario_trials.csv` を出力するようにしました。
- `scripts/build_figures.py` を更新し、三 scenario の mean response time、三 scenario の p95 response time、低信頼 neighbor scenario の rates figure を追加しました。
- `scripts/build_report.py` を更新し、Excel report に `Formal Scenarios` sheet を追加しました。
- `README.md`、`README.ch.md`、`README.ja.md`、`phase1_results.ch.md`、`phase1_results.ja.md` を更新し、三 scenario、`neighbor_es_availability`、結果解釈、現在の制限を説明しました。
- unit tests を追加し、local / neighbor availability の分離、B2 expected delay が neighbor availability を使うこと、低信頼 neighbor 条件で B2 が無効な探索を抑制すること、三 scenario の policy order と CI の妥当性を確認しました。

### 三つの scenario 設定

- `steady`: local と neighbor の両方を通常可用率 `0.82`、origin delay を `180.0` に設定します。
- `low_reliability_neighbor`: local は `0.82` のまま、neighbor を `0.25` に下げ、origin delay は `180.0` にします。
- `origin_congestion`: local と neighbor は `0.82` のまま、origin delay を `320.0` に上げます。これはオリジン遅延増加シナリオであり、実際の congestion queue model ではありません。

### 現在の結果判断

`steady` scenario で `B1` と `B2` が近いことは自然な結果です。`B2` の `B1` に対する mean response time advantage は `0.0198` にとどまり、neighbor が信頼できる場合には、B2 の判断も B1 と同様に neighbor fallback を選びやすいことを示しています。

`low_reliability_neighbor` scenario が今回の補完で最も重要な結果です。`B1` の neighbor failure rate は `0.89777`、mean response time は `106.5593`、p95 response time は `229.0214` でした。一方、`B2` は無効な neighbor search をほぼ避け、mean response time は `100.7891`、p95 response time は `201.3767` でした。`B2` の `B1` に対する mean response time advantage は `5.7702` です。

オリジン遅延増加シナリオでは、origin delay の増加により `B0` が大きく悪化し、mean response time は `163.6239` になりました。`B1` と `B2` は信頼できる neighbor を利用できるため、mean response time は約 `47.6` で、`B0` より明らかに良い結果です。ただし、neighbor が信頼できるため、`B1` と `B2` の差は小さいままです。

### 第一段階の状態

code、results、figures、documents の観点では、第一段階は報告可能な状態まで到達しました。現在の成果物には、三 scenario の repeated results、sensitivity / grid data、confidence interval、Nature-style figures、Excel report、中国語・日本語の結果解釈が含まれます。

次は Ueyama-sensei 向けの progress memo draft に進めます。memo では、現在の結果は preliminary Monte Carlo simulation であり、完全な discrete-event simulation ではないことを明確にする必要があります。また、`B2` の主な価値は、すべての scenario で `B1` を大きく上回ることではなく、低信頼 neighbor ES 条件で無効な fallback を避ける点にあると説明するのが適切です。

## 2026-05-26：第一段階の日本語進捗メモと memo 用 heatmap

### 本段階のテーマ

この段階では、第一段階の結果を Ueyama-sensei 向けの 2 ページ日本語進捗メモ draft として整理しました。あわせて、三つの代表 scenario の parameter と完全に対応する memo 用 sensitivity sweep を追加し、heatmap が parameter selection と B2 の有効領域を補足的に説明できるようにしました。

### 実施内容

- `src/edge_cache_sim/memo_sweep.py` と `scripts/run_memo_sweep.py` を追加しました。local ES availability は `0.82` に固定し、近隣 ES 可用率 `[0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]` と origin delay `[80, 120, 180, 240, 320]` を走査します。
- `results/memo_heatmap_summary.csv` を生成しました。この grid は、低信頼近隣 ES scenario の `0.25`、定常 scenario の `0.82 / 180`、オリジン遅延増加 scenario の `0.82 / 320` を含みます。
- `scripts/build_figures.py` を更新し、memo 用の mean response time、p95 response time、B2 advantage heatmap を生成するようにしました。heatmap の縦軸は `neighbor ES availability` に統一しました。
- `memo/phase1_progress_memo_ja.tex` を追加しました。LuaLaTeX + `jlreq` を想定し、本文では preliminary Monte Carlo simulation と明記しています。
- README、結果解釈、研究ログの表現を統一し、第三 scenario は対外的にオリジン遅延増加シナリオと説明するようにしました。`origin_congestion` は内部互換 key としてのみ残しています。

### 現在の制限

現環境には使用可能な LuaLaTeX / TeX Live がないため、`.tex` source と memo 用 PDF figures は準備済みですが、memo 本体 PDF はまだコンパイルできていません。Japanese LaTeX 環境を導入または設定した後、最終的な 2 ページ layout を確認する必要があります。
