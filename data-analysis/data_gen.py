"""分析対象の合成サンプル売上データを生成する（ポートフォリオ用）。

⚠️ 重要: ここで生成されるのは **合成（シミュレーション）サンプルデータ** です。
実在の企業・顧客・取引ではありません。外部の商用データを無断取得したものでも
ありません。データ分析パイプラインのデモを「自己完結」かつ「ToS セーフ」に行う
ための、明示的なサンプルです。

決定論的に生成するため乱数シードを固定しています（既定 seed=42）。同じシードなら
何度実行しても同一の CSV が得られます（再現性の担保）。

データモデル: 架空オンラインストアの 1 年分（2025 年）の注文明細。
- order_date     注文日
- region         地域（North / South / East / West）
- category       商品カテゴリ（Electronics / Home / Apparel / Books / Sports）
- product        商品名（カテゴリ配下の代表 SKU）
- quantity       数量
- unit_price     単価（カテゴリ帯ごとに価格レンジが異なる）
- discount_pct   割引率（%）
- revenue        売上額 = quantity * unit_price * (1 - discount_pct/100)

revenue を数量・単価から導出しているため、相関分析で「数量・単価が売上に効く」
という構造が（合成データ上で）実際に観測できるようにしてあります。

AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CategorySpec:
    """カテゴリごとの単価分布パラメータと代表商品（イミュータブル）。"""

    price_mu: float  # 単価（対数正規）の log 平均
    price_sigma: float  # 単価（対数正規）の log 標準偏差
    products: tuple[str, ...]  # カテゴリ配下の代表 SKU


# カテゴリごとの価格帯（単価の対数正規分布パラメータ）と代表商品。
# 価格レンジを変えることで「カテゴリ間で平均単価が異なる」構造を作る。
CATEGORY_CATALOG: dict[str, CategorySpec] = {
    "Electronics": CategorySpec(9.6, 0.5, ("Laptop", "Headphones", "Camera", "Smartwatch")),
    "Home": CategorySpec(8.4, 0.5, ("Cookware Set", "Vacuum", "Lamp", "Bedding")),
    "Apparel": CategorySpec(8.0, 0.4, ("Jacket", "Sneakers", "T-Shirt", "Jeans")),
    "Books": CategorySpec(7.2, 0.3, ("Novel", "Textbook", "Cookbook", "Comic")),
    "Sports": CategorySpec(8.6, 0.5, ("Yoga Mat", "Dumbbell", "Tent", "Bicycle")),
}

REGIONS: list[str] = ["North", "South", "East", "West"]

# 月ごとの需要係数（季節性）。年末商戦（11-12 月）と初夏（6-7 月）を高めに設定し、
# 時系列グラフで「山」が見えるようにする。index 0=1 月 ... 11=12 月。
SEASONALITY: list[float] = [0.85, 0.80, 0.95, 1.00, 1.05, 1.15, 1.20, 1.05, 1.00, 1.10, 1.35, 1.50]

DISCOUNT_CHOICES: list[int] = [0, 5, 10, 15, 20]
# 割引なし〜小割引が多く、大割引は稀という実務的な分布。
DISCOUNT_WEIGHTS: list[float] = [0.45, 0.25, 0.15, 0.10, 0.05]


def generate_sales(seed: int = 42, n_rows: int = 800, year: int = 2025) -> pd.DataFrame:
    """合成売上データを決定論的に生成して DataFrame で返す。"""
    rng = np.random.default_rng(seed)
    categories = list(CATEGORY_CATALOG.keys())

    # 各注文の日付を、季節性に比例する重みで 1 年の各月へ配分する。
    months = np.arange(1, 13)
    month_probs = np.array(SEASONALITY) / np.sum(SEASONALITY)
    chosen_months = rng.choice(months, size=n_rows, p=month_probs)
    # 月内の日付は一様（28 日までに丸めて月末超過を避ける）。
    chosen_days = rng.integers(1, 29, size=n_rows)
    order_dates = pd.to_datetime(
        {"year": np.full(n_rows, year), "month": chosen_months, "day": chosen_days}
    )

    regions = rng.choice(REGIONS, size=n_rows)
    chosen_categories = rng.choice(categories, size=n_rows)

    products = np.empty(n_rows, dtype=object)
    unit_prices = np.empty(n_rows, dtype=float)
    for i, cat in enumerate(chosen_categories):
        spec = CATEGORY_CATALOG[cat]
        products[i] = rng.choice(spec.products)
        # 対数正規で単価を引き、現実的な範囲にクリップして丸める。
        price = float(rng.lognormal(mean=spec.price_mu, sigma=spec.price_sigma))
        unit_prices[i] = round(min(max(price, 300.0), 500_000.0), 0)

    quantities = rng.integers(1, 11, size=n_rows)
    discounts = rng.choice(DISCOUNT_CHOICES, size=n_rows, p=DISCOUNT_WEIGHTS)
    revenue = np.round(quantities * unit_prices * (1.0 - discounts / 100.0), 0)

    df = pd.DataFrame(
        {
            "order_id": [f"ORD-{year}-{i + 1:04d}" for i in range(n_rows)],
            "order_date": order_dates.dt.strftime("%Y-%m-%d"),
            "region": regions,
            "category": chosen_categories,
            "product": products,
            "quantity": quantities.astype(int),
            "unit_price": unit_prices.astype(int),
            "discount_pct": discounts.astype(int),
            "revenue": revenue.astype(int),
        }
    )
    # 日付昇順に並べ替えて時系列分析を自然にする。
    return df.sort_values("order_date").reset_index(drop=True)


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = generate_sales()
    out_path = out_dir / "sales_sample.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"[done] 合成サンプルデータ生成: {len(df)} 行 -> {out_path.name}")
    print("  ※ これは実在しない合成（サンプル）データです。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
