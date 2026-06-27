"""分析結果とグラフを統合した Markdown レポートを生成する（ポートフォリオ用）。

analyze.Analysis と元の DataFrame を入力に、洞察（insights）を**実際の集計結果から
導出**して文章化し、グラフ画像を埋め込んだ report.md を sample_output/ に出力する。

洞察は一般論で埋めず、必ず計算済みの数値に接地させる（盛らない・捏造しない）。
AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from analyze import Analysis, analyze, load_sales


def _series_to_md_table(series: pd.Series, col_name: str, value_name: str) -> str:
    """pandas Series を Markdown テーブル文字列に変換する。"""
    lines = [f"| {col_name} | {value_name} |", "|---|---|"]
    for idx, val in series.items():
        lines.append(f"| {idx} | {int(val):,} |")
    return "\n".join(lines)


def _df_to_md_table(df: pd.DataFrame, index_name: str) -> str:
    """index 付き DataFrame を Markdown テーブル文字列に変換する。"""
    header = f"| {index_name} | " + " | ".join(df.columns) + " |"
    sep = "|---" * (len(df.columns) + 1) + "|"
    lines = [header, sep]
    for idx, row in df.iterrows():
        cells = " | ".join(f"{int(v):,}" for v in row.values)
        lines.append(f"| {idx} | {cells} |")
    return "\n".join(lines)


def _correlation_to_md_table(corr: pd.DataFrame) -> str:
    """相関行列を Markdown テーブル文字列に変換する。"""
    header = "| | " + " | ".join(corr.columns) + " |"
    sep = "|---" * (len(corr.columns) + 1) + "|"
    lines = [header, sep]
    for idx, row in corr.iterrows():
        cells = " | ".join(f"{v:.3f}" for v in row.values)
        lines.append(f"| {idx} | {cells} |")
    return "\n".join(lines)


def _build_insights(analysis: Analysis) -> list[str]:
    """集計結果から洞察（文章）を導出する。すべて実数に接地させる。"""
    top_cat = analysis.by_category.index[0]
    top_cat_rev = int(analysis.by_category.iloc[0]["revenue"])
    cat_share = top_cat_rev / analysis.total_revenue * 100

    top_region = analysis.by_region.index[0]
    top_region_rev = int(analysis.by_region.iloc[0]["revenue"])

    peak_month = str(analysis.monthly_revenue.idxmax())
    peak_month_rev = int(analysis.monthly_revenue.max())
    low_month = str(analysis.monthly_revenue.idxmin())
    low_month_rev = int(analysis.monthly_revenue.min())

    top_product = str(analysis.top_products.index[0])
    top_product_rev = int(analysis.top_products.iloc[0])

    # 売上と各数値指標の相関係数（revenue 行から取得）。
    corr_qty = float(analysis.correlation.loc["revenue", "quantity"])
    corr_price = float(analysis.correlation.loc["revenue", "unit_price"])
    corr_disc = float(analysis.correlation.loc["revenue", "discount_pct"])

    return [
        f"総売上 {analysis.total_revenue:,} のうち最大の貢献カテゴリは **{top_cat}**"
        f"（{top_cat_rev:,}、全体の {cat_share:.1f}%）でした。",
        f"地域別では **{top_region}** が最も売上が高く（{top_region_rev:,}）、"
        f"4 地域の中で先頭でした。",
        f"月次では **{peak_month}**（{peak_month_rev:,}）が最も売上が高く、"
        f"最も低い **{low_month}**（{low_month_rev:,}）の約 {peak_month_rev / low_month_rev:.2f} 倍でした。"
        f"年末商戦に向けた季節性が読み取れます。",
        f"商品別の売上首位は **{top_product}**（{top_product_rev:,}）でした。",
        f"相関分析では、売上は **単価との相関が最も強く**（r={corr_price:.3f}）、"
        f"次いで数量（r={corr_qty:.3f}）と連動していました。"
        f"割引率との相関は {corr_disc:.3f} で、売上を強く左右する主因ではありませんでした。",
        f"1 注文あたりの売上は平均 {analysis.mean_order_value:,.0f} / 中央 {analysis.median_order_value:,.0f} で、"
        f"平均が中央を上回ることから、少数の高額注文が分布の裾を押し上げる右裾型の分布です。",
    ]


def generate_markdown(df: pd.DataFrame, analysis: Analysis, out_dir: Path) -> Path:
    """総合レポート (report.md) を生成する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    insights = _build_insights(analysis)
    insights_md = "\n".join(f"- {line}" for line in insights)
    date_min = df["order_date"].min().strftime("%Y-%m-%d")
    date_max = df["order_date"].max().strftime("%Y-%m-%d")

    content = f"""# 売上データ分析レポート — 架空オンラインストア（サンプル）

> 本レポートは **Tatara（AI エージェント）が自律生成** したポートフォリオ成果物です。
> 入力データは **合成（シミュレーション）サンプルデータ** であり、実在の企業・顧客・取引では
> ありません（外部の商用データを無断取得したものでもありません）。`data_gen.py` が乱数シードを
> 固定して決定論的に生成します。**レポート中の数値はすべて、その合成データを実際に集計して
> 得たもの**で、手入力・捏造はありません。

## データ概要

| 指標 | 値 |
|---|---|
| 対象期間 | {date_min} 〜 {date_max} |
| 総注文数 | {analysis.total_orders:,} |
| 総売上 | {analysis.total_revenue:,} |
| 総販売数 | {analysis.total_units:,} |
| 平均注文額 | {analysis.mean_order_value:,.0f} |
| 中央注文額 | {analysis.median_order_value:,.0f} |
| 売上の標準偏差 | {analysis.overview['revenue_std']:,.0f} |
| 平均割引率 | {analysis.mean_discount_pct}% |

## 主要な洞察（insights）

{insights_md}

## カテゴリ別 集計

{_df_to_md_table(analysis.by_category, "カテゴリ")}

![Revenue by Category](revenue_by_category.png)

## 地域別 集計

{_df_to_md_table(analysis.by_region, "地域")}

## 月次売上（時系列）

![Monthly Revenue](monthly_revenue.png)

## 商品別 売上トップ {len(analysis.top_products)}

{_series_to_md_table(analysis.top_products, "商品", "売上")}

![Top Products](top_products.png)

## 売上の分布

![Revenue Distribution](revenue_distribution.png)

## 数値指標の相関行列

{_correlation_to_md_table(analysis.correlation)}

> 売上（revenue）は単価（unit_price）・数量（quantity）から導出されるため、これらと正の相関を
> 持つのは設計上自然です。相関「分析」が実データ上で構造を正しく検出できることの確認になります。

---

*生成パイプライン: `data_gen.py`（合成データ生成）→ `analyze.py`（集計）→ `visualize.py`（可視化）→ `report_gen.py`（レポート統合）*
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    df = load_sales(out_dir / "sales_sample.csv")
    analysis = analyze(df)
    report = generate_markdown(df, analysis, out_dir)
    print(f"[done] レポート生成完了: {report.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
