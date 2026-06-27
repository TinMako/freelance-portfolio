# Web スクレイパー + 分析 + レポート（ポートフォリオ）

公開された練習用サイト [`quotes.toscrape.com`](https://quotes.toscrape.com) から
引用文データを収集し、統計分析してグラフ付きレポートを自動生成する、
**エンドツーエンドのデータ収集パイプライン**のサンプルです。

> ## 🤖 透明性の明記（AI 生成）
> 本ポートフォリオのコード・ドキュメント・分析は、AI エージェント **Tatara** が
> 自律的に設計・実装・実行・検証して生成したものです。
> サンプルデータ（`sample_output/`）は実際に当該サイトをスクレイピングして取得した
> **実データ**であり、捏造・改変は一切していません。
> （副業案件における AI 利用開示要件の習慣化として明記しています。）

## 何ができるか

| ステップ | スクリプト | 役割 |
|---|---|---|
| 1. 収集 | `scraper.py` | `requests` + `BeautifulSoup` で全 10 ページを巡回し、引用文・著者・タグを構造化 CSV 化 |
| 2. 集計 | `analyzer.py` | `pandas` で件数・分布・トップ N・文字数統計を算出し集計 CSV を出力 |
| 3. 可視化 | `report_gen.py` | `matplotlib` で棒グラフを生成し、Markdown レポートに統合 |

3 つは個別実行でき、`run_all.py` で一括実行もできます。

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
# 一括実行（収集 → 集計 → レポート）
python run_all.py

# または個別に
python scraper.py       # sample_output/quotes.csv を生成
python analyzer.py      # summary_overview.csv / top_authors.csv / top_tags.csv を生成
python report_gen.py    # top_authors.png / top_tags.png / report.md を生成
```

実行後、`sample_output/` に以下が出力されます:

```
sample_output/
├── quotes.csv             # 収集した生データ（引用文・著者・タグ）
├── summary_overview.csv   # 総件数・著者数・タグ数・文字数統計
├── top_authors.csv        # 著者別 引用件数トップ N
├── top_tags.csv           # タグ別 出現頻度トップ N
├── top_authors.png        # 著者別 引用件数の棒グラフ
├── top_tags.png           # タグ出現頻度の棒グラフ
└── report.md              # グラフを含む総合 Markdown レポート
```

## カスタマイズ方法

- **対象サイトの変更**: `scraper.py` の `BASE_URL` を変更します。
  ただし**スクレイピングが許可されたサイトのみ**を対象にしてください
  （`scraper.py` は `urllib.robotparser` で robots.txt を事前確認します）。
- **収集項目の変更**: `parse_quotes()` の CSS セレクタ（`span.text` / `small.author` / `a.tag`）を
  対象サイトの構造に合わせて調整します。`Quote` データクラスの項目もあわせて変更します。
- **集計内容の変更**: `analyzer.py` の `analyze()` に集計ロジックを追加します。
  `top_n` 引数でトップ N の件数を変えられます。
- **グラフ・レポートの変更**: `report_gen.py` の `_bar_chart()` や `generate_markdown()` を編集します。
- **リクエスト間隔**: `scraper.py` の `POLITE_DELAY`（既定 1.0 秒）でサーバ負荷を調整します。

## 設計上の配慮

- **ToS / 法務セーフ**: 対象は**スクレイピング学習用に公開された練習サイトのみ**。
  商用サイトの無断スクレイピングは行いません。robots.txt を必ず確認します。
- **礼儀的アクセス**: ページ間に待機を入れ、明示的な User-Agent を送信します。
- **正直な失敗**: ネットワーク異常・HTML 構造変化・空結果を握り潰さず、
  例外または非ゼロ終了コードで顕在化させます（「動かないのに完成」と偽りません）。
- **イミュータブル設計**: レコードは `frozen` データクラスで表現し、副作用を避けます。
- **最小構成**: 過剰実装を避け、標準的なライブラリ構成で完結させています。

## 実データの結果（このリポジトリ同梱の sample_output）

- 総引用件数: **100 件**（全 10 ページ）
- ユニーク著者数: **50 名**
- ユニークタグ数: **137 種**
- 最多引用著者: **Albert Einstein**（10 件）

詳細は [`sample_output/report.md`](sample_output/report.md) を参照してください。

## ライセンス / 注意

学習・ポートフォリオ用途のサンプルです。実案件へ転用する際は、
対象サイトの利用規約・robots.txt・関連法令を必ず確認してください。
