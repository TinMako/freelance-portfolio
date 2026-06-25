# データ分析レポート生成（ポートフォリオ）

合成サンプルの売上データを入力に、`pandas` で集計・統計分析し、`matplotlib` で
グラフを生成して、洞察（insights）付きの Markdown レポートを自動生成する、
**エンドツーエンドのデータ分析パイプライン**のサンプルです。

> ## 🤖 透明性の明記（AI 生成）
> 本ポートフォリオのコード・ドキュメント・分析は、AI エージェント **Tatara** が
> 自律的に設計・実装・実行・検証して生成したものです。
> 入力データ（`sample_output/sales_sample.csv`）は、`data_gen.py` が乱数シードを
> 固定して生成した **合成（シミュレーション）サンプルデータ** です。
> 実在の企業・顧客・取引ではなく、外部の商用データを無断取得したものでもありません。
> レポート中の数値はすべて、その合成データを実際に集計して得た**実出力**であり、
> 手入力・捏造は一切ありません。
> （副業案件における AI 利用開示・データ出所開示の習慣化として明記しています。）

## 何ができるか

| ステップ | スクリプト | 役割 |
|---|---|---|
| 1. 生成 | `data_gen.py` | 季節性・カテゴリ別価格帯を持つ合成売上データ（既定 800 行 / 2025 年）を決定論的に生成 |
| 2. 集計 | `analyze.py` | `pandas` で記述統計・カテゴリ/地域別グループ集計・月次時系列・トップ N・相関行列を算出 |
| 3. 可視化 | `visualize.py` | `matplotlib` で分布・時系列・トップ N・カテゴリ別の 4 グラフを生成 |
| 4. レポート | `report_gen.py` | 集計結果から洞察を導出し、グラフを埋め込んだ Markdown レポートに統合 |

4 つは個別実行でき、`run_all.py` で一括実行もできます。

## セットアップ

```bash
# 仮想環境を作成（任意。uv / venv どちらでも可）
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

## 使い方

```bash
# 一括実行（生成 → 集計 → 可視化 → レポート）
python run_all.py

# または個別に
python data_gen.py      # sample_output/sales_sample.csv を生成
python analyze.py       # summary_overview / by_category / by_region / monthly_revenue / top_products / correlation の各 CSV
python visualize.py     # revenue_distribution / monthly_revenue / top_products / revenue_by_category の各 PNG
python report_gen.py    # report.md を生成
```

実行後、`sample_output/` に以下が出力されます:

```
sample_output/
├── sales_sample.csv          # 合成サンプルの生データ（注文明細 800 行）
├── summary_overview.csv      # 注文数・総売上・平均/中央注文額・割引率などの全体指標
├── by_category.csv           # カテゴリ別 注文数・売上・平均注文額
├── by_region.csv             # 地域別 注文数・売上
├── monthly_revenue.csv       # 月次売上（時系列）
├── top_products.csv          # 商品別 売上トップ N
├── correlation.csv           # 数量・単価・割引率・売上の相関行列
├── revenue_distribution.png  # 注文売上の分布ヒストグラム
├── monthly_revenue.png       # 月次売上の折れ線（時系列）
├── top_products.png          # 商品別売上トップ N の横棒
├── revenue_by_category.png   # カテゴリ別売上の縦棒
└── report.md                 # グラフ・洞察を含む総合 Markdown レポート
```

## カスタマイズ方法

- **自分の CSV を使う**: 実データの CSV を `sample_output/sales_sample.csv` として配置し、
  `data_gen.py` のステップを飛ばして `analyze.py` から実行します。列名
  （`order_date` / `region` / `category` / `product` / `quantity` / `unit_price` /
  `discount_pct` / `revenue`）を合わせるか、`analyze.py` の `load_sales()` / `analyze()` を
  対象データに合わせて調整します。
- **データ規模・期間の変更**: `data_gen.py` の `generate_sales(seed=..., n_rows=..., year=...)`
  を変更します。`seed` を変えれば別パターンの合成データになります（再現性は維持）。
- **集計内容の変更**: `analyze.py` の `analyze()` に集計ロジックを追加します。
  `top_n` 引数でトップ N の件数を変えられます。相関対象は `NUMERIC_COLS` で調整します。
- **グラフの変更**: `visualize.py` の各 `_plot_*()` 関数を編集します（色は冒頭の定数で統一）。
- **レポート・洞察の変更**: `report_gen.py` の `_build_insights()`（洞察の導出ロジック）と
  `generate_markdown()`（レイアウト）を編集します。

## 設計上の配慮

- **ToS / 法務セーフ**: 入力は**自己生成の合成サンプルデータのみ**。商用データの無断取得・
  スクレイピングは行いません。データ出所を README とレポートの両方で明示します。
- **洞察はデータに接地**: レポートの insights は一般論で埋めず、`analyze()` が計算した
  実際の集計値（カテゴリ構成比・相関係数・季節ピーク等）から導出します（盛らない・捏造しない）。
- **正直な失敗**: 入力欠落・空データ・必須列欠落を握り潰さず、例外または非ゼロ終了コードで
  顕在化させます（「動かないのに完成」と偽りません）。
- **再現性**: 乱数シードを固定し、同じ入力からは同じ出力が得られます。
- **イミュータブル設計**: 分析結果は `frozen` データクラス（`Analysis`）で表現し、副作用を避けます。
- **最小構成**: 過剰実装を避け、`pandas` + `matplotlib` の標準的な構成で完結させています。

## 実出力の結果（このリポジトリ同梱の sample_output）

`seed=42` で生成した合成データ（800 注文 / 2025 年）を分析した実際の結果です:

- 総売上: **27,069,991**（800 注文）
- 最大カテゴリ: **Electronics**（13,510,071、全体の **49.9%**）
- 最大地域: **North**（7,037,849）
- 売上ピーク月: **2025-11**（3,254,363、最小の 2025-02 の約 **2.18 倍** = 季節性）
- 売上トップ商品: **Smartwatch**（3,909,938）
- 相関: 売上は**単価と最も強く相関**（r=**0.808**）、次いで数量（r=0.424）

詳細は [`sample_output/report.md`](sample_output/report.md) を参照してください。

## ライセンス / 注意

学習・ポートフォリオ用途のサンプルです。実案件に適用する際は、対象データの利用許諾・
個人情報/機密の取り扱い・関連法令を必ず確認してください。入力が合成データである点を
成果物に明記する運用を推奨します。
