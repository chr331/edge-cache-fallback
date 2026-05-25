# Edge Cache Fallback Simulation

このリポジトリは、低信頼な edge-cache 環境における fallback-control policy を対象にした第一段階の Monte Carlo シミュレーションです。現時点の目的は、複雑なシステムモデルを最初から作ることではなく、B0/B1/B2 の比較、baseline、parameter sweep、Excel report、research log までの再現可能な流れを作ることです。

- English: [README.md](./README.md)
- Chinese: [README.ch.md](./README.ch.md)
- 中国語研究ログ: [research_log.ch.md](./research_log.ch.md)
- 日本語研究ログ: [research_log.ja.md](./research_log.ja.md)

## Policy 定義

- `B0`: local ES で内容を復元できない場合、直接 origin に fallback します。
- `B1`: local ES が失敗した場合、まず neighbor cooperative ES を探索し、neighbor でも失敗したら origin に fallback します。
- `B2`: local ES が失敗した場合、neighbor search の期待遅延と直接 origin delay を比較し、期待遅延が小さい方を選択します。

## 第一段階の実験設定

第一段階では Monte Carlo シミュレーションを使い、queueing、congestion、request arrival process、service capacity はまだ導入していません。まず fallback logic と metric calculation を安定させ、その後でモデルを拡張する方針です。

| パラメータ | baseline 値 | 設定理由 |
| --- | ---: | --- |
| `num_contents` | `500` | コンテンツ空間を中程度にして、Zipf 的な人気の偏りを観察しやすくしています。 |
| `num_requests` | `10000` | サンプル数を十分に確保し、mean と p95 を安定させています。 |
| `zipf_alpha` | `1.1` | ホットスポットはあるが極端すぎない需要分布として、baseline に適しています。 |
| `es_availability` | `0.82` | local / neighbor recovery の成功と失敗の両方が出るため、三つの policy を比較しやすくしています。 |
| `origin_delay` | `180.0` | origin を local や neighbor より明確に遅くし、fallback の価値が見えやすいようにしています。 |
| `local_es_count` | `3` | local 側の chunk source を限定し、local recovery が常に成功しないようにしています。 |
| `neighbor_group_size` | `5` | neighbor pool を local より少し大きくし、cooperative recovery の効果を見やすくしています。 |
| `k` | `3` | 復元には少なくとも 3 chunks が必要という erasure-coding の基本制約を残しています。 |
| `local_probe_delay` | `12.0` | local の探索コストを表します。 |
| `neighbor_probe_delay` | `28.0` | neighbor 探索は local より高コストですが、origin より有利な場合があります。 |
| `local_recovery_delay` | `18.0` | local recovery 完了後の基本遅延を表します。 |
| `neighbor_recovery_delay` | `48.0` | neighbor recovery は local より遅いが、origin が遅い状況では有効になり得ます。 |
| `seed` | `20260525` | 乱数シードを固定し、baseline と sweep の再現性を確保しています。 |

Latency jitter に関する説明は README ではなく research log に記録しています。これはモデル説明と実験記録に属する内容だからです。

## 環境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 実行

```powershell
python scripts\run_experiment.py
python scripts\run_sweep.py
python scripts\build_report.py
```

## 出力

- `results/summary.csv`: baseline 結果。policy ごとに 1 行です。
- `results/sweep_summary.csv`: `origin_delay` と `es_availability` の sensitivity 結果です。
- `results/edge_cache_fallback_report.xlsx`: ローカルで読むための Excel report です。
- `research_log.ch.md`: 中国語研究ログです。
- `research_log.ja.md`: 日本語研究ログです。

## 主な指標

- `mean_response_time`: 平均応答時間。
- `p95_response_time`: 95 パーセンタイル応答時間。tail latency を見るために使います。
- `origin_free_rate`: origin にアクセスせずに完了した割合。
- `neighbor_failure_rate`: neighbor fallback を試した後も失敗した割合。

## 検証

```powershell
python -m unittest discover -s tests
```
