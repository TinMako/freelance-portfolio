"""収集した引用文 CSV を pandas で集計・統計する（ポートフォリオ用）。

scraper.py が出力した quotes.csv を入力に、
- 総件数 / ユニーク著者数 / ユニークタグ数
- 著者別の引用件数（トップ N）
- タグ別の出現頻度（トップ N）
- 引用文の文字数統計（平均 / 中央値 / 最大 / 最小）
を計算し、機械可読な集計 CSV と Python オブジェクトとして返す。

AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Analysis:
    """分析結果のスナップショット（イミュータブル）。"""

    total_quotes: int
    unique_authors: int
    unique_tags: int
    top_authors: pd.Series  # index=著者, value=件数
    top_tags: pd.Series  # index=タグ, value=出現数
    text_length_stats: dict[str, float] = field(default_factory=dict)


def load_quotes(csv_path: Path) -> pd.DataFrame:
    """quotes.csv を DataFrame として読み込む。"""
    if not csv_path.exists():
        raise FileNotFoundError(f"入力 CSV が見つかりません: {csv_path}（先に scraper.py を実行してください）")
    df = pd.read_csv(csv_path, dtype={"text": str, "author": str, "tags": str})
    df["tags"] = df["tags"].fillna("")
    if df.empty:
        raise ValueError("入力 CSV が空です（スクレイピングが失敗している可能性があります）")
    return df


def explode_tags(df: pd.DataFrame) -> pd.Series:
    """パイプ区切りの tags 列を 1 タグ 1 行に展開した Series を返す。"""
    tags = (
        df["tags"]
        .str.split("|")
        .explode()
        .str.strip()
    )
    return tags[tags != ""]


def analyze(df: pd.DataFrame, top_n: int = 10) -> Analysis:
    """DataFrame から各種統計を計算する。"""
    tags_series = explode_tags(df)
    text_lengths = df["text"].str.len()
    return Analysis(
        total_quotes=int(len(df)),
        unique_authors=int(df["author"].nunique()),
        unique_tags=int(tags_series.nunique()),
        top_authors=df["author"].value_counts().head(top_n),
        top_tags=tags_series.value_counts().head(top_n),
        text_length_stats={
            "mean": round(float(text_lengths.mean()), 1),
            "median": float(text_lengths.median()),
            "max": int(text_lengths.max()),
            "min": int(text_lengths.min()),
        },
    )


def save_summary_csv(analysis: Analysis, out_dir: Path) -> list[Path]:
    """集計結果を機械可読な CSV 群として保存する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    overview_path = out_dir / "summary_overview.csv"
    # value 列を文字列で保持し、整数指標が 100.0 のように float 化されるのを防ぐ
    pd.DataFrame(
        [
            {"metric": "total_quotes", "value": str(analysis.total_quotes)},
            {"metric": "unique_authors", "value": str(analysis.unique_authors)},
            {"metric": "unique_tags", "value": str(analysis.unique_tags)},
            {"metric": "text_length_mean", "value": str(analysis.text_length_stats["mean"])},
            {"metric": "text_length_median", "value": str(analysis.text_length_stats["median"])},
            {"metric": "text_length_max", "value": str(analysis.text_length_stats["max"])},
            {"metric": "text_length_min", "value": str(analysis.text_length_stats["min"])},
        ]
    ).to_csv(overview_path, index=False, encoding="utf-8")
    written.append(overview_path)

    authors_path = out_dir / "top_authors.csv"
    analysis.top_authors.rename_axis("author").reset_index(name="quote_count").to_csv(
        authors_path, index=False, encoding="utf-8"
    )
    written.append(authors_path)

    tags_path = out_dir / "top_tags.csv"
    analysis.top_tags.rename_axis("tag").reset_index(name="occurrences").to_csv(
        tags_path, index=False, encoding="utf-8"
    )
    written.append(tags_path)

    return written


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    df = load_quotes(out_dir / "quotes.csv")
    analysis = analyze(df)
    written = save_summary_csv(analysis, out_dir)
    print(f"[done] 集計完了: 引用 {analysis.total_quotes} 件 / 著者 {analysis.unique_authors} 名 / タグ {analysis.unique_tags} 種")
    for p in written:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
