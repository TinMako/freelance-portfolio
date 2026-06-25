"""分析結果からグラフ画像と Markdown レポートを生成する（ポートフォリオ用）。

analyzer.Analysis を入力に、
- 著者別引用件数の棒グラフ (top_authors.png)
- タグ出現頻度の棒グラフ (top_tags.png)
- Markdown 形式の総合レポート (report.md)
を sample_output/ に出力する。

matplotlib はヘッドレス実行のため Agg バックエンドを使う（GUI 不要）。
AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # GUI 無し環境で動かすため非対話バックエンドを指定
import matplotlib.pyplot as plt  # noqa: E402 - backend 指定後に import する必要がある

from analyzer import Analysis, analyze, load_quotes


def _bar_chart(series, title: str, xlabel: str, ylabel: str, out_path: Path, color: str) -> None:
    """汎用の横棒グラフ生成ヘルパー。"""
    fig, ax = plt.subplots(figsize=(9, 5))
    # 上位を上に表示するため反転
    data = series[::-1]
    ax.barh(data.index.astype(str), data.values, color=color)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    for i, v in enumerate(data.values):
        ax.text(v, i, f" {v}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def generate_charts(analysis: Analysis, out_dir: Path) -> list[Path]:
    """棒グラフ画像を生成して保存する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    authors_png = out_dir / "top_authors.png"
    tags_png = out_dir / "top_tags.png"
    _bar_chart(
        analysis.top_authors,
        title="Top Authors by Quote Count",
        xlabel="Quote count",
        ylabel="Author",
        out_path=authors_png,
        color="#4C72B0",
    )
    _bar_chart(
        analysis.top_tags,
        title="Top Tags by Occurrence",
        xlabel="Occurrences",
        ylabel="Tag",
        out_path=tags_png,
        color="#55A868",
    )
    return [authors_png, tags_png]


def _series_to_md_table(series, col_name: str, value_name: str) -> str:
    """pandas Series を Markdown テーブル文字列に変換する。"""
    lines = [f"| {col_name} | {value_name} |", "|---|---|"]
    for idx, val in series.items():
        lines.append(f"| {idx} | {val} |")
    return "\n".join(lines)


def generate_markdown(analysis: Analysis, out_dir: Path) -> Path:
    """総合レポート (report.md) を生成する。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.md"
    stats = analysis.text_length_stats
    content = f"""# Web スクレイピング分析レポート — quotes.toscrape.com

> 本レポートは **Tatara（AI エージェント）が自律生成** したポートフォリオ成果物です。
> データは練習用公開サイト `https://quotes.toscrape.com` を実際にスクレイピングして取得した実データです（捏造なし）。

## 概要

| 指標 | 値 |
|---|---|
| 総引用件数 | {analysis.total_quotes} |
| ユニーク著者数 | {analysis.unique_authors} |
| ユニークタグ数 | {analysis.unique_tags} |
| 引用文の平均文字数 | {stats['mean']} |
| 引用文の中央文字数 | {stats['median']} |
| 引用文の最大文字数 | {stats['max']} |
| 引用文の最小文字数 | {stats['min']} |

## 著者別 引用件数（トップ {len(analysis.top_authors)}）

{_series_to_md_table(analysis.top_authors, "著者", "引用件数")}

![Top Authors](top_authors.png)

## タグ出現頻度（トップ {len(analysis.top_tags)}）

{_series_to_md_table(analysis.top_tags, "タグ", "出現数")}

![Top Tags](top_tags.png)

## 所見

- 収集した {analysis.total_quotes} 件の引用は {analysis.unique_authors} 名の著者に由来し、最も引用が多いのは **{analysis.top_authors.index[0]}**（{int(analysis.top_authors.iloc[0])} 件）でした。
- タグでは **{analysis.top_tags.index[0]}**（{int(analysis.top_tags.iloc[0])} 回）が最頻出で、引用の主題傾向を示します。
- 引用文の長さは平均 {stats['mean']} 文字（{int(stats['min'])}〜{int(stats['max'])} 文字）に分布しています。

---

*生成パイプライン: `scraper.py`（収集）→ `analyzer.py`（集計）→ `report_gen.py`（可視化・レポート）*
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"
    df = load_quotes(out_dir / "quotes.csv")
    analysis = analyze(df)
    charts = generate_charts(analysis, out_dir)
    report = generate_markdown(analysis, out_dir)
    print("[done] レポート生成完了:")
    for p in [*charts, report]:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
