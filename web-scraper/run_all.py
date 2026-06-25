"""パイプライン全体を 1 コマンドで実行する（収集→集計→レポート）。

使い方:
    python run_all.py

各ステップは個別スクリプト（scraper.py / analyzer.py / report_gen.py）でも実行可能。
AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from pathlib import Path

import analyzer
import report_gen
import scraper


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"

    print("=== Step 1/3: スクレイピング ===")
    rc = scraper.main()
    if rc != 0:
        return rc

    print("\n=== Step 2/3: 集計 ===")
    df = analyzer.load_quotes(out_dir / "quotes.csv")
    analysis = analyzer.analyze(df)
    analyzer.save_summary_csv(analysis, out_dir)

    print("\n=== Step 3/3: レポート生成 ===")
    report_gen.generate_charts(analysis, out_dir)
    report_gen.generate_markdown(analysis, out_dir)

    print("\n[all done] sample_output/ に成果物を出力しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
