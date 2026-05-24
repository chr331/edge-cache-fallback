# Edge Cache Fallback Simulation

このリポジトリは、低信頼な edge-cache 環境における fallback control を対象にした第一段階の Monte Carlo シミュレーションです。

- 日本語版 README: このファイル
- Chinese version: [README.md](./README.md)

## Policies

- `B0`: local ES が失敗したら、そのまま origin にフォールバックします。
- `B1`: local ES が失敗したら、まず neighbor の cooperative ES を探索し、neighbor でも失敗したら origin に戻ります。
- `B2`: local ES が失敗したら、neighbor 探索の期待遅延と origin 遅延を比較し、より小さい方を選びます。

## なぜ jitter を入れるのか

応答時間に小さな揺らぎを入れているのは、全ての経路があまりにも「きれい」に揃いすぎるのを避けるためです。実際の edge-cache やネットワーク処理では、同じ経路でもスケジューリング、待ち行列、シリアライズ、ネットワーク変動の影響で遅延が少しずつ変わります。揺らぎがないと mean と p95 が理想化されすぎて、tail latency の自然さが薄くなります。

ここでの jitter は小さく、各経路に少しだけ正の乱数揺らぎを足しているだけです。目的は「どの経路が速いか」という主判断を変えることではなく、tail latency をより現実的に見せることです。

## パラメータ設定

第一段階の実験では、local recovery、neighbor fallback、origin fallback の3つが一度の実行で見えるように、次の baseline 値を使っています。

- `num_requests = 10000`
  - サンプル数を十分にして、mean と p95 を安定させています。
- `num_contents = 500`
  - コンテンツ空間を中程度にして、Zipf の偏りが fallback 策略にどう効くかを見やすくしています。
- `zipf_alpha = 1.1`
  - ホットスポットはあるが極端すぎない需要分布で、第一段階の baseline に向いています。
- `es_availability = 0.82`
  - local / neighbor recovery の成功と失敗の両方が出るようにして、B0/B1/B2 を比較しやすくしています。
- `origin_delay = 180.0`
  - origin を local や neighbor よりかなり遅くして、fallback の価値が見えやすいようにし、後続の sweep でも比較しやすくしています。
- `local_es_count = 3`, `k = 3`
  - local recovery に 3/3 個の chunk 可用性を要求することで、local が常に成功するわけではなく、fallback が必要になるようにしています。
- `neighbor_group_size = 5`
  - neighbor 側を local より少し大きくして、cooperative recovery の効果を見やすくしています。
- `local_probe_delay = 12.0`, `neighbor_probe_delay = 28.0`, `local_recovery_delay = 18.0`, `neighbor_recovery_delay = 48.0`
  - これらは「探索 + 復旧」の基礎コストで、neighbor は local より高めですが、それでも origin よりは安い場合があります。
- `seed = 20260525`
  - 乱数シードを固定して再現性を確保しています。baseline も sweep も同じ条件なら同じ結果を再現できます。

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

主な出力:

- `results/summary.csv`: 再現可能な machine-readable summary
- `results/sweep_summary.csv`: origin-delay と ES availability の sensitivity 結果
- `results/edge_cache_fallback_report.xlsx`: 読みやすい形式の workbook
- `research_log.md`: 各 stage で何を変えたか、その理由

## CSV の項目

`results/summary.csv` は policy ごとに 1 行で、次の列を持ちます。

- `scenario`
- `policy`
- `mean_response_time`
- `p95_response_time`
- `origin_free_rate`
- `neighbor_failure_rate`
- `zipf_alpha`
- `es_availability`
- `origin_delay`
- `local_es_count`
- `neighbor_group_size`
- `k`

## 検証

```powershell
python -m unittest discover -s tests
```

## 補足

現時点のモデルは intentionally simple で、queue、congestion、request arrivals、service capacity は扱っていません。baseline の fallback ロジックが安定してから、必要なら SimPy で拡張します。
