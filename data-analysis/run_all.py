"""パイプライン全体を 1 コマンドで実行する（生成→集計→可視化→レポート）。

使い方:
    python run_all.py

各ステップは個別スクリプト（data_gen.py / analyze.py / visualize.py / report_gen.py）でも
実行可能。AI（Tatara）が自律生成したコードです。
"""

from __future__ import annotations

from pathlib import Path

import analyze
import data_gen
import report_gen
import visualize


def main() -> int:
    out_dir = Path(__file__).parent / "sample_output"

    print("=== Step 1/4: 合成サンプルデータ生成 ===")
    rc = data_gen.main()
    if rc != 0:
        return rc

    print("\n=== Step 2/4: 集計 ===")
    df = analyze.load_sales(out_dir / "sales_sample.csv")
    analysis = analyze.analyze(df)
    analyze.save_summary_csv(analysis, out_dir)

    print("\n=== Step 3/4: 可視化 ===")
    visualize.generate_charts(df, analysis, out_dir)

    print("\n=== Step 4/4: レポート生成 ===")
    report_gen.generate_markdown(df, analysis, out_dir)

    print("\n[all done] sample_output/ に成果物を出力しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
