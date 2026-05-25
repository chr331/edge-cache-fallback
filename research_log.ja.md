# 研究ログ

## 2026-05-25：Baseline 段階

### 本段階のテーマ

本段階では、低信頼 edge-cache 環境における fallback-control 研究の第一版の再現可能な実験基盤を作成しました。最初から複雑なモデルを作るのではなく、まず B0/B1/B2 の三つの policy を実行し、主要指標を記録し、「simulation -> results -> figures/Excel -> research notes -> GitHub backup」という基本的な流れを整えることを目的としました。

### 実施内容

- Python project structure を整理し、`src/edge_cache_sim/`、`scripts/`、`tests/`、`results/` を追加しました。
- 第一段階の Monte Carlo simulation model を実装し、random requests と ES availability によって local recovery、neighbor fallback、origin fallback を模擬しました。
- 三つの policy を実装して比較しました。
  - `B0`: local ES が失敗した後、直接 origin に fallback します。
  - `B1`: local ES が失敗した後、neighbor ES を先に探索し、neighbor も失敗したら origin に fallback します。
  - `B2`: local ES が失敗した後、neighbor-search の期待遅延と origin delay を比較し、期待遅延が小さい行動を選びます。
- `results/summary.csv` を再現可能な実験データとして生成しました。
- `results/edge_cache_fallback_report.xlsx` を生成し、Overview、Parameters、Summary、Charts の四つの sheet を用意しました。
- local success、B0 fallback、B1 neighbor recovery、B2 origin choice、三 policy の summary 出力を確認する 5 件の unit tests を追加しました。
- 公開 GitHub repository `chr331/edge-cache-fallback` を作成し、第一版の code、README、research log、sample CSV を `main` に push しました。

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

### 主な指標

- `mean_response_time`: 平均応答時間。
- `p95_response_time`: 95 percentile 応答時間。tail latency を見るために使います。
- `origin_free_rate`: origin にアクセスせずに完了した割合。
- `neighbor_failure_rate`: neighbor fallback を試した後も失敗した割合。

### 初期結果

- `B0`: mean response time `101.247`, p95 `201.405`, origin-free rate `0.5503`, neighbor failure rate `0.0000`
- `B1`: mean response time `45.214`, p95 `70.844`, origin-free rate `0.9790`, neighbor failure rate `0.0468`
- `B2`: mean response time `45.170`, p95 `70.909`, origin-free rate `0.9788`, neighbor failure rate `0.0474`

### 初期判断

Baseline parameter では neighbor fallback が明確に有効でした。B0 と比較すると、B1/B2 は origin access の割合を大きく減らし、mean response time と p95 response time も低下させました。

一方で、この設定では B2 が B1 より明確に優れているとは言えません。理由は、neighbor ES availability が比較的高く、origin delay も大きいため、neighbor search がほぼ常に有利になるからです。この baseline は「neighbor fallback に価値がある」ことを示すには適していますが、B2 の dynamic selection の優位性を強く示すにはまだ不十分です。

### なぜ jitter を入れるのか

応答時間に小さな乱数の揺らぎを入れているのは、全ての経路の遅延があまりにも「きれい」に揃いすぎることを避けるためです。実際の edge-cache system では、同じ経路でも scheduling、queueing、network fluctuation、serialization cost などによって遅延が少しずつ変わります。完全に deterministic な delay だけを使うと、baseline results が不自然になり、p95 の tail latency らしさも弱くなります。

現在の jitter は小さく、各経路の基本遅延に少しだけ正の random variation を加えるものです。目的は「どの policy が速いか」という主な比較を変えることではなく、tail latency をより現実的に見せることです。

### パラメータ設定の意図

- `num_requests = 10000`: サンプル数を十分に確保し、mean と p95 を安定させています。
- `num_contents = 500`: コンテンツ空間を中程度にして、Zipf 的な人気の偏りを観察しやすくしつつ、実験を軽量に保っています。
- `zipf_alpha = 1.1`: ホットスポットはあるが極端すぎない需要分布を表します。
- `es_availability = 0.82`: local / neighbor recovery の成功と失敗が両方出るようにしています。
- `origin_delay = 180.0`: origin を local や neighbor より明確に遅くし、fallback の価値を見えやすくしています。
- `local_es_count = 3`, `k = 3`: local recovery が常に成功しないため、fallback が必要になります。
- `neighbor_group_size = 5`: neighbor pool を少し大きくし、cooperative recovery の効果を見やすくしています。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`: neighbor search は local probe より高コストですが、origin より有利な場合があります。
- `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`: neighbor recovery は local recovery より遅く、edge nodes 間の協調に伴う追加コストを表します。
- `seed = 20260525`: random seed を固定し、同じ baseline results を再現できるようにしています。

### 現在の制限

- 現在のモデルは第一段階の Monte Carlo であり、queueing、request arrival process、service capacity、congestion は含みません。
- baseline は実行済みですが、confidence interval を出すための repeated trials はまだ行っていません。
- real trace や real CDN/edge workload はまだ導入していません。
- B2 の判断は expected delay に基づいており、online estimation error、trust score、neighbor state observation cost はまだ考慮していません。

### 次のステップ

- `origin_delay` sweep を行い、origin が速い場合または遅い場合に B2 が B1 と差を出せるか確認します。
- `es_availability` sweep を行い、neighbor が不安定な場合に B2 が不要な neighbor search を避けられるか確認します。
- policy metric vs origin delay、policy metric vs ES availability、B2 advantage heatmap を追加します。
- Ueyama-sensei 向けの短い日本語 progress memo を準備します。

## 2026-05-25：Parameter Sweep 段階

### 本段階のテーマ

本段階では、単一 baseline から parameter sensitivity analysis に拡張しました。特に、B2 の dynamic fallback decision が、固定的な neighbor-first policy である B1 より意味を持つ条件を確認することを目的としました。

### 実施内容

- `scripts/run_sweep.py` を追加し、二つの controlled sweep を実行しました。
  - `origin_delay`: `40, 80, 120, 180, 240, 320`
  - `es_availability`: `0.45, 0.55, 0.65, 0.75, 0.82, 0.90`
- `results/sweep_summary.csv` を生成し、各 policy と各 sweep point を 1 行として記録しました。
- `results/edge_cache_fallback_report.xlsx` を拡張し、`Origin Delay Sweep`、`ES Availability Sweep`、`B2 Advantage` の三つの sheet を追加しました。
- mean response time、p95 response time、origin-free rate、neighbor failure rate の line charts を追加しました。
- `b2_advantage_vs_b1 = B1 mean response time - B2 mean response time` として B2 advantage summary を追加しました。

### 実験設定

二つの sweep は同じ第一段階 Monte Carlo model を使用しています。sweep 対象の parameter 以外は baseline 設定を維持しました。

- Number of requests: `10000`
- Zipf alpha: `1.1`
- Local ES count: `3`
- Neighbor group size: `5`
- Required chunks `K`: `3`
- Origin-delay sweep fixed ES availability: `0.82`
- ES-availability sweep fixed origin delay: `180.0`

### 初期結果

Origin-delay sweep では、`origin_delay = 40` のとき、B2 mean response time は `38.174`、B1 は `42.210` で、B2 advantage は `4.036` でした。これは、origin が比較的速い場合、B2 が不要な neighbor search を避け、より直接 origin に近い判断をできることを示しています。

より高い origin delay では、B1 と B2 の結果は近く、B2 advantage は小さな範囲で正負に揺れました。

ES-availability sweep では、すべての tested availability で B1 と B2 は非常に近い結果でした。現時点の parameterization では、availability だけを変えても B2 と B1 を安定して分離するには不十分です。

### 初期判断

この段階では、B2 に関する最初の有用な evidence が得られました。origin access が十分速く、neighbor search が必ずしも有利ではない場合、B2 の dynamic decision は追加探索コストを減らす可能性があります。

ただし、現在の B2 rule はまだ粗く、global expected-delay comparison のみを使っています。次の研究方向としては、neighbor trust、recent failure rate、observed neighbor response time、online estimate など、より豊かな local state を B2 に入れることが重要です。

### 現在の制限

- 各 sweep point は 1 seed のみであり、Monte Carlo variance はまだ評価していません。
- neighbor ES availability は homogeneous assumption のままです。
- B2 は global expected-delay comparison を使っており、online learning や per-neighbor state ではありません。
- confidence interval はまだ報告していません。

### 次のステップ

- 各 sweep point に repeated trials を追加し、平均値と confidence interval を報告します。
- trust / availability mismatch scenario を追加し、B2 が B1 の仮定より低い neighbor reliability を観測する状況を作ります。
- `origin_delay` と `es_availability` の 2D heatmap を追加し、B2 advantage が出る領域を確認します。
- baseline と sweep の結果をまとめた日本語 progress memo を作成します。
