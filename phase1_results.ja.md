# 第一段階の結果解釈

## 主な結論

第一段階の結果からは、`B2` の価値は条件付きであると慎重に言えます。baseline 設定では `B1` と `B2` の平均応答時間はほぼ同じです。一方で、`origin_delay` と `es_availability` の組み合わせによっては、`B2` が不利な neighbor fallback を避けることで、固定的に neighbor を探索する `B1` より安定した性能を示します。

これは最終的な system-level conclusion ではありません。現時点の結果は、第一段階の Monte Carlo model に基づき、fallback-control logic、統計処理、可視化の流れを確認するためのものです。

## 実験設定

baseline は次の設定で実行しました。

| Parameter | Value |
| --- | ---: |
| `num_requests` | `10000` |
| `trials` | `10` |
| `zipf_alpha` | `1.1` |
| `es_availability` | `0.82` |
| `origin_delay` | `180.0` |
| `local_es_count` | `3` |
| `neighbor_group_size` | `5` |
| `k` | `3` |
| `seed` | `20260525` |

各 repeated trial の seed は次の形で設定しました。

```text
trial_seed = base_seed + trial_index
```

これにより、単一の random run に依存せず、Monte Carlo variance と 95% confidence interval を確認できます。

## Policy の意味

- `B0`: local ES で復元できない場合、直接 origin に fallback します。
- `B1`: local ES が失敗した後、固定的に neighbor ES を探索し、neighbor も失敗した場合に origin に fallback します。
- `B2`: local ES が失敗した後、neighbor-search の期待遅延と直接 origin に行く遅延を比較し、期待遅延が小さい行動を選びます。

簡単に言うと、`B1` は「常にまず neighbor を試す」方法であり、`B2` は「neighbor を試す価値があるかを先に判断する」方法です。

## baseline の結果

baseline repeated trials の主な結果は次の通りです。

| Policy | Mean response time | 95% CI | p95 response time | Origin-free rate |
| --- | ---: | ---: | ---: | ---: |
| `B0` | `101.0823` | `100.6808` - `101.4838` | `201.4085` | `0.55121` |
| `B1` | `44.8589` | `44.6308` - `45.0870` | `70.7171` | `0.98075` |
| `B2` | `44.8391` | `44.6211` - `45.0571` | `70.6902` | `0.98092` |

baseline では、`B1` と `B2` はどちらも `B0` より明らかに良い結果です。`B0` は local recovery に失敗すると直接 origin に戻るため、origin delay が大きい設定では応答時間が悪化します。一方、`B1` と `B2` は neighbor ES を利用できるため、多くの request を origin-free で完了できます。

ただし、`B2` の `B1` に対する平均応答時間の advantage は次の通りです。

```text
B2 advantage vs B1 = 0.0198
```

この差は非常に小さいため、baseline だけから `B2` が `B1` より明確に優れるとは言えません。より適切には、baseline 条件では `B2` は `B1` とほぼ同等の性能を維持している、と解釈します。

## sweep と heatmap の結果

二次元 grid は次の組み合わせで実行しました。

```text
origin_delay x es_availability
```

評価値は次の定義です。

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

この値が正であれば、`B2` の平均応答時間が `B1` より低いことを意味します。

36 個の grid parameter points のうち：

- `20` 点では値が正で、`B2` が `B1` より速い結果でした。
- `16` 点では値が負でしたが、負の幅は小さいものでした。
- 最大 advantage は `origin_delay = 40.0`、`es_availability = 0.45` で、`18.0856` でした。
- 最小値は `origin_delay = 320.0`、`es_availability = 0.75` で、`-0.1796` でした。

この傾向は、origin が速く、neighbor availability が低い場合に、`B1` が不要な neighbor-search cost を払いやすいことを示しています。`B2` はそのような場合に直接 origin を選びやすく、不利な neighbor fallback を避けられます。

## Figure files

Figures は `scripts/build_figures.py` により Python + Matplotlib で生成し、`results/figures/` に出力しました。

- `fig_phase1_baseline_mean_response_time`: baseline mean response time。
- `fig_phase1_baseline_p95_response_time`: baseline p95 response time。
- `fig_phase1_origin_delay_sweep`: origin delay sensitivity。
- `fig_phase1_es_availability_sweep`: ES availability sensitivity。
- `fig_phase1_b2_advantage_heatmap`: B2 advantage over B1。

各 figure は `.svg`、`.pdf`、`.png`、`.tiff` として保存しています。`.svg` では text を editable な状態で保持しており、後から論文図や報告資料用に調整しやすくしています。

## 現在の制限

現在の model には、queueing、congestion、request arrival process、service capacity、real CDN trace、trust-learning は含まれていません。したがって、結果は第一段階の fallback-control logic における傾向を示すものであり、実運用性能を直接表すものではありません。

## 次の段階

次は、これらの figures と結果をもとに、Ueyama-sensei 向けの短い progress memo draft を作成するのが自然です。memo では `B2` を過度に主張せず、再現可能な simulation framework、repeated trials、confidence interval、heatmap を整備したこと、そして `B2` は neighbor fallback が不利な場合に余計な探索コストを避ける可能性があることを中心に述べるのがよいです。
