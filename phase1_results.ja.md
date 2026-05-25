# 第一段階の結果解釈

## 主な結論

第一段階は、単一の baseline から、研究計画書に対応する三つの正式 scenario へ拡張されました。現在の出力は、`steady`、`low_reliability_neighbor`、内部 key としての `origin_congestion` の三つを含みます。ただし、対外的な説明では `origin_congestion` をオリジン遅延増加シナリオとして扱い、実際の queueing や server congestion を表すモデルとは区別します。

主な結論は慎重に述べる必要があります。`B2` の価値は条件付きです。通常環境では、`B1` と `B2` の性能はほぼ同じです。これは自然な結果です。neighbor ES が十分に信頼できる場合、`B2` の期待遅延判断も、多くの場合 neighbor fallback を選ぶためです。一方、低信頼 neighbor ES scenario では、`B2` は `B1` のような「先に neighbor を試し、失敗後に origin へ戻る」という二重の遅延負担を避けられます。

なお、現在のモデルは第一段階の preliminary Monte Carlo simulation です。完全な discrete-event simulation ではありません。目的は、fallback-control logic、統計処理、図表化、結果解釈が成立するかを確認することです。queueing、congestion、request arrival process、service capacity などは次段階の課題です。

## 実験設定

共通設定は以下の通りです。

| Parameter | Value |
| --- | ---: |
| `num_requests` | `10000` |
| `trials` | `10` |
| `zipf_alpha` | `1.1` |
| `local_es_count` | `3` |
| `neighbor_group_size` | `5` |
| `k` | `3` |
| `seed` | `20260525` |

三つの scenario は以下の通りです。

| Scenario | local ES availability | neighbor ES availability | origin delay | 研究計画書上の対応 |
| --- | ---: | ---: | ---: | --- |
| `steady` | `0.82` | `0.82` | `180.0` | 定常シナリオ |
| `low_reliability_neighbor` | `0.82` | `0.25` | `180.0` | 低信頼近隣ESシナリオ |
| `origin_congestion` | `0.82` | `0.82` | `320.0` | オリジン遅延増加シナリオ |

今回の重要な追加点は `neighbor_es_availability` です。従来の `es_availability` だけでは、local ES と neighbor ES の信頼性を分けて表現できませんでした。現在は、local ES は通常水準のまま、neighbor cooperative group だけを低信頼にする scenario を表現できます。

各 repeated trial の seed は以下の形で設定します。

```text
trial_seed = base_seed + trial_index
```

これにより、単一の random run に依存せず、Monte Carlo variance と 95% confidence interval を確認できます。

## Policy の意味

- `B0`: local ES で復元できない場合、直接 origin へ fallback します。
- `B1`: local ES で復元できない場合、常に neighbor ES を先に探索し、失敗した場合に origin へ fallback します。
- `B2`: local ES で復元できない場合、neighbor-search の期待遅延と直接 origin に行く遅延を比較し、期待遅延が小さい行動を選択します。

簡単に言えば、`B1` は「常に neighbor を試す」方式であり、`B2` は「neighbor を試す価値があるかを先に判断する」方式です。

## 三つの scenario の結果

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

`B2 advantage vs B1` は以下のように定義します。

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

この値が正であれば、`B2` の平均応答時間が `B1` より低いことを意味します。

## Scenario ごとの解釈

`steady` scenario では、local ES と neighbor ES の両方が通常の可用率です。この場合、`B1` と `B2` はほぼ同等です。`B2` の `B1` に対する advantage は `0.0198` にすぎません。これは問題ではなく、期待される結果です。neighbor fallback が有効な条件では、`B2` も neighbor fallback を選びやすいためです。

`low_reliability_neighbor` scenario では、neighbor ES availability を `0.25` に下げています。このとき、`B1` の neighbor failure rate は `0.89777` まで上がります。つまり、多くの場合で neighbor search が失敗し、その後 origin へ戻るため、二重の遅延が発生します。その結果、`B1` の mean response time は `106.5593`、p95 response time は `229.0214` になります。一方、`B2` は neighbor search が不利であると判断し、無効な探索を避けるため、mean response time は `100.7891`、p95 response time は `201.3767` に抑えられます。この scenario が、第一段階で `B2` の価値を最も明確に示しています。

内部 key が `origin_congestion` のオリジン遅延増加シナリオでは、origin delay を `320.0` に上げています。この場合、直接 origin に戻る `B0` は大きく悪化し、mean response time は `163.6239`、p95 response time は `341.3924` になります。`B1` と `B2` は信頼できる neighbor ES を使えるため、`B0` より明らかに良い結果です。ただし neighbor が信頼できるため、`B2` も多くの場合 neighbor fallback を選び、`B1` との差は小さくなります。

## Sweep と heatmap

三つの scenario に加えて、memo 用の sensitivity / grid analysis も追加しました。これは、heatmap と代表 scenario の parameter が別々の設定に見えないようにするためです。この grid は三つの代表 scenario で用いた主要 parameter を含みます。

```text
neighbor_es_availability = [0.20, 0.25, 0.30, 0.35, 0.45, 0.55, 0.65, 0.82]
origin_delay = [80, 120, 180, 240, 320]
local_es_availability = 0.82
```

40 個の grid parameter points のうち、以下の結果でした。

- `29` 点では `B2 advantage vs B1` が正であり、`B2` の平均応答時間が `B1` より低い結果でした。
- `11` 点では負でしたが、負の幅は小さいものでした。
- 最大 advantage は `origin_delay = 80.0`、`neighbor_es_availability = 0.20` のときで、`10.9897` でした。
- 最小値は `origin_delay = 320.0`、`neighbor_es_availability = 0.25` のときで、`-0.1971` でした。

この heatmap は、`B2` が常に `B1` に大きく勝つことを示すものではありません。むしろ、近隣 ES 可用率が低く、origin cost が相対的に高すぎない領域で、`B2` が無駄な neighbor fallback を避けられることを補足的に示しています。図軸は `neighbor ES availability` とし、正文では `近隣 ES 可用率` と説明します。

## Figure files

Figures は `scripts/build_figures.py` により Python + Matplotlib で生成し、`results/figures/` に出力しています。現在は正式結果用 figure と memo 用 figure があります。

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

各 figure は `.svg`、`.pdf`、`.png`、`.tiff` として保存しています。`.svg` では text を editable な状態で保持しているため、後から論文図や報告資料用に調整しやすくしています。

## 現在の制限

現在の model には、queueing、congestion、request arrival process、service capacity、real CDN trace、trust-learning は含まれていません。したがって、結果は第一段階の fallback-control logic における傾向を示すものであり、実運用性能を直接表すものではありません。

また、現在のオリジン遅延増加シナリオは、`origin_delay` を大きくすることで origin cost の上昇を表現しているだけです。実際の congestion queue model ではありません。次段階で正式な discrete-event simulation に進む場合、request arrival、service rate、queueing delay、cache replacement policy などを加える必要があります。

## 第一段階の状態

code、results、figures、documents の観点では、第一段階は報告可能な状態まで補完できています。三つの正式 scenario、repeated results、confidence interval、CSV data source、Excel report、Nature-style figures、中国語・日本語の結果解釈がそろいました。

次は model をさらに広げるより先に、これらの結果をもとに Ueyama-sensei 向けの短い progress memo draft を作成するのが自然です。その memo では、第一段階は preliminary simulation であること、そして `B2` の価値は低信頼 neighbor ES 条件で無効な fallback を避ける点にあることを、慎重に述べるべきです。
