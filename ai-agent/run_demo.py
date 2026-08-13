"""
マルチエージェントパイプライン デモ実行スクリプト

--mock  フラグでモックモード（API キー不要）、
なければ ANTHROPIC_API_KEY 環境変数を使う。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from agent import (
    PipelineResult,
    make_anthropic_caller,
    make_mock_caller,
    run_pipeline,
)


# ─────────────────────────────────────────────────────────────
# デモ入力
# ─────────────────────────────────────────────────────────────

DEMO_INPUTS = [
    {
        "label": "分析ケース（売上データ）",
        "text": (
            "先月の売上データです。"
            "製品A: 1,200,000円（前月比 +8%）、"
            "製品B: 850,000円（前月比 -3%）、"
            "製品C: 2,100,000円（前月比 +22%）。"
            "合計 4,150,000円でした。"
        ),
    },
    {
        "label": "要約ケース（ニュース記事）",
        "text": (
            "大手テクノロジー企業が本日、新しい AI アシスタント製品を発表しました。"
            "この製品は自然言語処理技術を活用し、ユーザーの業務効率を大幅に改善することを"
            "目指しています。価格は月額 2,980 円から提供される予定です。"
            "発売は来月を予定しており、まず法人向けに先行リリースされます。"
        ),
    },
    {
        "label": "不明ケース（分類外）",
        "text": "今日の天気はどうですか？",
    },
    {
        "label": "入力ゲートブロック（空文字）",
        "text": "",
    },
]

# ─────────────────────────────────────────────────────────────
# モック応答（実際のLLM挙動を模倣）
# ─────────────────────────────────────────────────────────────

MOCK_RESPONSES = {
    "リクエスト分類": "analysis",     # ルーターへの応答（先頭がanalysisケースの場合）
    "データ分析": (
        "- 製品C が最大の売上（210万円・+22%）で全体成長を牽引\n"
        "- 製品B のみ前月比マイナス（-3%）で要注意\n"
        "- 合計 415万円、前月比（推定）+10〜12% 成長"
    ),
    "サマリー": (
        "大手テクノロジー企業が AI アシスタント製品を発表した。"
        "月額 2,980 円から提供予定で、来月に法人向け先行リリースを予定している。"
        "業務効率の改善を主な目的としている。"
    ),
}


def _mock_caller(system: str, inp) -> str:  # type: ignore[override]
    """ルーターとアナライザー/サマライザーを入力テキストの内容で切り替えるモック。"""
    if "リクエスト分類" in system:
        # 数値集計・売上データ → analysis（「売上データ」「前月比」で識別）
        if "売上" in inp.text and ("前月比" in inp.text or "合計" in inp.text):
            return "analysis"
        # ニュース・記事・説明 → summary（「企業」「発表」で識別）
        if "企業" in inp.text or "発表" in inp.text:
            return "summary"
        return "unknown"
    if "データ分析" in system:
        return MOCK_RESPONSES["データ分析"]
    if "サマリー" in system:
        return MOCK_RESPONSES["サマリー"]
    return "[モック] 対応なし"


# ─────────────────────────────────────────────────────────────
# 出力フォーマット
# ─────────────────────────────────────────────────────────────

def format_result(label: str, result: PipelineResult) -> str:
    lines = [f"\n{'='*60}", f"入力: {label}", f"{'='*60}"]
    if result.error:
        lines.append(f"[GATE BLOCKED] {result.error}")
        return "\n".join(lines)
    lines.append(f"ルーティング先: {result.route}")
    if result.analysis:
        a = result.analysis
        lines.append(f"\n[分析エージェント] confidence={a.confidence:.2f}{' (fallback)' if a.fallback_used else ''}")
        lines.append(a.content)
    elif result.summary:
        s = result.summary
        lines.append(f"\n[要約エージェント] confidence={s.confidence:.2f}{' (fallback)' if s.fallback_used else ''}")
        lines.append(s.content)
    else:
        lines.append("専門エージェントが割り当てられませんでした（unknown ルート）")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="マルチエージェントパイプライン デモ")
    parser.add_argument("--mock", action="store_true", help="モックモード（API キー不要）")
    args = parser.parse_args()

    if args.mock:
        caller = _mock_caller
        print("[モックモード] API キーなしで動作します\n")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("エラー: ANTHROPIC_API_KEY が設定されていません。")
            print("  export ANTHROPIC_API_KEY=sk-... を設定するか、--mock を使ってください。")
            sys.exit(1)
        caller = make_anthropic_caller(api_key)
        print("[実 API モード] Anthropic API を使用します\n")

    for demo in DEMO_INPUTS:
        result = run_pipeline(demo["text"], caller)
        print(format_result(demo["label"], result))

    print(f"\n{'='*60}")
    print("デモ完了")


if __name__ == "__main__":
    main()
