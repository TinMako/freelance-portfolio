"""合成売上データを pandas で集計・統計分析する（ポートフォリオ用）。

data_gen.py が出力した sales_sample.csv を入力に、
- 全体サマリ（注文数 / 総売上 / 平均・中央注文額 / 総販売数 / 平均割引率）
- カテゴリ別の集計（注文数 / 売上 / 平均注文額）
- 地域別の集計（注文数 / 売上）
- 月次売上（時系列）
- 商品別売上トップ N
- 数量・単価・割引率・売上の相関行列
を計算し、機械可読な集計 CSV と Python オブジェクトとして返す。

AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# 相関分析の対象となる数値列。
NUMERIC_COLS: list[str] = ["quantity", "unit_price", "discount_pct", "revenue"]


@dataclass(frozen=True)
class Analysis:
    """分析結果のスナップショット（イミュータブル）。"""

    total_orders: int
    total_revenue: int
    mean_order_value: float
    median_order_value: float
    total_units: int
    mean_discount_pct: float
    by_category: pd.DataFrame  # index=category, columns=[orders, revenue, avg_order_value]
    by_region: pd.DataFrame  # index=region, columns=[orders, revenue]
    monthly_revenue: pd.Series  # index=YYYY-MM, value=revenue
    top_products: pd.Series  # index=product, value=revenue
    correlation: pd.DataFrame  # 数値列同士の相関行列
    overview: dict[str, float] = field(default_factory=dict)


def load_sales(csv_path: Path) -> pd.DataFrame:
    """sales_sample.csv を DataFrame として読み込み、型を整える。"""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"入力 CSV が見つかりません: {csv_path}（先に data_gen.py を実行してください）"
        )
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("入力 CSV が空です（データ生成が失敗している可能性があります）")

    required = {"order_date", "region", "category", "product", *NUMERIC_COLS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"必須列が欠落しています: {sorted(missing)}")

    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def analyze(df: pd.DataFrame, top_n: int = 10) -> Analysis:
    """DataFrame から各種統計を計算する。"""
    by_category = (
        df.groupby("category")
        .agg(orders=("order_id", "count"), revenue=("revenue", "sum"))
        .assign(avg_order_value=lambda x: (x["revenue"] / x["orders"]).round(0).astype(int))
        .sort_values("revenue", ascending=False)
    )

    by_region = (
        df.groupby("region")
        .agg(orders=("order_id", "count"), revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )

    monthly_revenue = (
        df.set_index("order_date")
        .resample("MS")["revenue"]
        .sum()
    )
    monthly_revenue.index = monthly_revenue.index.strftime("%Y-%m")

    top_products = (
        df.groupby("product")["revenue"].sum().sort_values(ascending=False).head(top_n)
    )

    # 数値列の相関（売上が数量・単価とどれだけ連動するかを定量化）。
    correlation = df[NUMERIC_COLS].corr().round(3)

    return Analysis(
        total_orders=int(len(df)),
        total_revenue=int(df["revenue"].sum()),
        mean_order_value=round(float(df["revenue"].mean()), 1),
        median_order_value=float(df["revenue"].median()),
        total_units=int(df["quantity"].sum()),
        mean_discount_pct=round(float(df["discount_pct"].mean()), 2),
        by_category=by_category,
        by_region=by_region,
        monthly_revenue=monthly_revenue,
        top_products=top_products,
        correlation=correlation,
        overview={
            "revenue_std": round(float(df["revenue"].std()), 1),
            "revenue_max": int(df["revenue"].max()),
            "revenue_min": int(df["revenue"].min()),
        },
    )


def save_summary_csv(analysis: Analysis, out_dir: Path) -> list[Path]:
    """集計結果を機械可読な CSV 群として保存する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    overview_path = out_dir / "summary_overview.csv"
    # value 列は文字列で保持し、整数指標が float 表記になるのを防ぐ。
    pd.DataFrame(
        [
            {"metric": "total_orders", "value": str(analysis.total_orders)},
            {"metric": "total_revenue", "value": str(analysis.total_revenue)},
            {"metric": "mean_order_value", "value": str(analysis.mean_order_value)},
            {"metric": "median_order_value", "value": str(analysis.median_order_value)},
            {"metric": "total_units", "value": str(analysis.total_units)},
            {"metric": "mean_discount_pct", "value": str(analysis.mean_discount_pct)},
            {"metric": "revenue_std", "value": str(analysis.overview["revenue_std"])},
            {"metric": "revenue_max", "value": str(analysis.overview["revenue_max"])},
            {"metric": "revenue_min", "value": str(analysis.overview["revenue_min"])},
        ]
    ).to_csv(overview_path, index=False, encoding="utf-8")
    written.append(overview_path)

    category_path = out_dir / "by_category.csv"
    analysis.by_category.reset_index().to_csv(category_path, index=False, encoding="utf-8")
    written.append(category_path)

    region_path = out_dir / "by_region.csv"
    analysis.by_region.reset_index().to_csv(region_path, index=False, encoding="utf-8")
    written.append(region_path)

    monthly_path = out_dir / "monthly_revenue.csv"
    analysis.monthly_revenue.rename_axis("month").reset_index(name="revenue").to_csv(
        monthly_path, index=False, encoding="utf-8"
    )
    written.append(monthly_path)

    products_path = out_dir / "top_products.csv"
    analysis.top_products.rename_axis("product").reset_index(name="revenue").to_csv(
        products_path, index=False, encoding="utf-8"
    )
    written.append(products_path)

    correlation_path = out_dir / "correlation.csv"
    analysis.correlation.to_csv(correlation_path, encoding="utf-8")
    written.append(correlation_path)

    return written


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    df = load_sales(out_dir / "sales_sample.csv")
    analysis = analyze(df)
    written = save_summary_csv(analysis, out_dir)
    print(
        f"[done] 集計完了: 注文 {analysis.total_orders} 件 / 総売上 {analysis.total_revenue:,} / "
        f"カテゴリ {len(analysis.by_category)} 種"
    )
    for p in written:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
