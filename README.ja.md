# Edge Cache Fallback Simulation

このリポジトリは、低信頼な edge-cache 環境における fallback-control policy の第一段階シミュレーションです。現時点の目的は、`B0`、`B1`、`B2` の三つの policy を再現可能で統計的に報告できる Monte Carlo 実験にすることであり、queueing、congestion、real trace、trust-learning はまだ導入しません。

- English: [README.md](./README.md)
- Chinese: [README.ch.md](./README.ch.md)
- 中国語研究ログ: [research_log.ch.md](./research_log.ch.md)
- 日本語研究ログ: [research_log.ja.md](./research_log.ja.md)

## Policy 定義

- `B0`: local ES で復元できない場合、直接 origin に fallback します。
- `B1`: local ES が失敗した後、先に neighbor cooperative ES を探索し、neighbor も失敗した場合に origin に fallback します。
- `B2`: local ES が失敗した後、neighbor-search の期待遅延と直接 origin に行く遅延を比較し、期待遅延が小さい行動を選びます。

## 第一段階の実験設定

| パラメータ | baseline 値 | 説明 |
| --- | ---: | --- |
| `num_contents` | `500` | Zipf 型の人気分布を見るための中程度のコンテンツ空間。 |
| `num_requests` | `10000` | mean と p95 を安定させるためのデフォルトサンプル数。 |
| `zipf_alpha` | `1.1` | 人気の偏りはあるが極端すぎない要求分布。 |
| `es_availability` | `0.82` | local / neighbor recovery の成功と失敗が両方出る設定。 |
| `origin_delay` | `180.0` | origin を local / neighbor 経路より明確に遅くする設定。 |
| `local_es_count` | `3` | local 側の chunk source を限定。 |
| `neighbor_group_size` | `5` | neighbor pool を少し大きくして協調復元の効果を見る。 |
| `k` | `3` | 復元には少なくとも 3 chunks が必要。 |
| `seed` | `20260525` | 再現性のための固定 seed。 |

## 環境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 実行

baseline と single-seed sweep:

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
```

第一段階の正式な統計実行:

```powershell
python scripts\run_repeated.py
```

開発確認用の軽い実行:

```powershell
python scripts\run_repeated.py --trials 3 --num-requests 1000
```

読みやすい Excel report の生成:

```powershell
python scripts\build_report.py
```

## repeated trials と grid sweep

`scripts/run_repeated.py` はデフォルトで baseline、`origin_delay` sweep、`es_availability` sweep、二次元の `origin_delay x es_availability` grid を repeated trials として実行します。デフォルトは `trials = 10` で、各 trial の seed は `base_seed + trial_index` として設定します。これにより Monte Carlo variance と 95% confidence interval を報告できます。

二次元 grid では次の値を計算します。

```text
B2 advantage vs B1 = B1 mean_response_time - B2 mean_response_time
```

この値が正であれば、B2 の平均応答時間が B1 より低いことを意味します。

## 出力

- `results/summary.csv`: baseline 結果。policy ごとに 1 行。
- `results/sweep_summary.csv`: `origin_delay` と `es_availability` の single-seed sweep。
- `results/repeated_summary.csv`: repeated trials の mean、std、stderr、95% CI。
- `results/grid_summary.csv`: 二次元 `origin_delay x es_availability` grid の repeated 統計。
- `results/repeated_trials.csv`: trial ごとの policy-level summary。
- `results/edge_cache_fallback_report.xlsx`: repeated summary と B2 advantage grid sheet を含む Excel report。

## 主な指標

- `mean_response_time`: 平均応答時間。
- `p95_response_time`: 95 percentile 応答時間。tail latency の確認に使います。
- `origin_free_rate`: origin にアクセスせず完了した割合。
- `neighbor_failure_rate`: neighbor fallback を試した後も失敗した割合。
- `b2_advantage_vs_b1_mean`: B1 と B2 の平均応答時間差。定義は `B1 - B2`。

## 検証

```powershell
python -m unittest discover -s tests
```
