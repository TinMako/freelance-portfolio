"""分析結果からグラフ画像を生成する（ポートフォリオ用）。

analyze.Analysis と元の DataFrame を入力に、
- 注文売上の分布ヒストグラム (revenue_distribution.png)
- 月次売上の時系列折れ線 (monthly_revenue.png)
- 商品別売上トップ N の横棒グラフ (top_products.png)
- カテゴリ別売上の縦棒グラフ (revenue_by_category.png)
を sample_output/ に出力する。

matplotlib はヘッドレス実行のため Agg バックエンドを使う（GUI 不要）。
AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # GUI 無し環境で動かすため非対話バックエンドを指定
import matplotlib.pyplot as plt  # noqa: E402 - backend 指定後に import する必要がある
import pandas as pd  # noqa: E402

from analyze import Analysis, analyze, load_sales

# カラーパレット（カテゴリ系統で色を統一）。
COLOR_PRIMARY = "#4C72B0"
COLOR_ACCENT = "#C44E52"
COLOR_GREEN = "#55A868"
COLOR_PURPLE = "#8172B2"


def _plot_revenue_distribution(df: pd.DataFrame, out_path: Path) -> None:
    """注文ごとの売上額の分布をヒストグラムで描く。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(df["revenue"], bins=30, color=COLOR_PRIMARY, edgecolor="white")
    median = float(df["revenue"].median())
    ax.axvline(median, color=COLOR_ACCENT, linestyle="--", linewidth=1.5, label=f"median = {median:,.0f}")
    ax.set_title("Order Revenue Distribution", fontsize=13, fontweight="bold")
    ax.set_xlabel("Revenue per order")
    ax.set_ylabel("Number of orders")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_monthly_revenue(monthly: pd.Series, out_path: Path) -> None:
    """月次売上の推移を折れ線で描く（時系列）。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(monthly.index, monthly.values, marker="o", color=COLOR_GREEN, linewidth=2)
    ax.set_title("Monthly Revenue (time series)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_top_products(top_products: pd.Series, out_path: Path) -> None:
    """商品別売上トップ N を横棒で描く。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    data = top_products[::-1]  # 上位を上に表示するため反転
    ax.barh(data.index.astype(str), data.values, color=COLOR_PURPLE)
    ax.set_title("Top Products by Revenue", fontsize=13, fontweight="bold")
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Product")
    for i, v in enumerate(data.values):
        ax.text(v, i, f" {int(v):,}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_revenue_by_category(by_category: pd.DataFrame, out_path: Path) -> None:
    """カテゴリ別売上を縦棒で描く（グループ集計の可視化）。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(by_category.index.astype(str), by_category["revenue"], color=COLOR_PRIMARY)
    ax.set_title("Revenue by Category", fontsize=13, fontweight="bold")
    ax.set_xlabel("Category")
    ax.set_ylabel("Revenue")
    ax.tick_params(axis="x", rotation=20)
    for i, v in enumerate(by_category["revenue"]):
        ax.text(i, v, f"{int(v):,}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def generate_charts(df: pd.DataFrame, analysis: Analysis, out_dir: Path) -> list[Path]:
    """全グラフを生成して保存し、生成パスのリストを返す。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    dist_png = out_dir / "revenue_distribution.png"
    monthly_png = out_dir / "monthly_revenue.png"
    products_png = out_dir / "top_products.png"
    category_png = out_dir / "revenue_by_category.png"

    _plot_revenue_distribution(df, dist_png)
    _plot_monthly_revenue(analysis.monthly_revenue, monthly_png)
    _plot_top_products(analysis.top_products, products_png)
    _plot_revenue_by_category(analysis.by_category, category_png)

    return [dist_png, monthly_png, products_png, category_png]


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    df = load_sales(out_dir / "sales_sample.csv")
    analysis = analyze(df)
    charts = generate_charts(df, analysis, out_dir)
    print("[done] グラフ生成完了:")
    for p in charts:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
