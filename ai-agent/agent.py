"""
マルチエージェント業務自動化サンプル

ルーター → アナライザー → サマライザー の 3 エージェント構成。
各エージェントは独立した責務を持ち、多段安全ゲート（入力検証・出力バリデーション・
フォールバック）を通じてハルシネーションを後続へ流さない。

使用方法:
  export ANTHROPIC_API_KEY=sk-...  # 実 API 使用時
  python run_demo.py               # モックモードで API キー不要
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Callable, Literal


# ─────────────────────────────────────────────────────────────
# 型定義（イミュータブル設計）
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentInput:
    text: str
    max_tokens: int = 512
    temperature: float = 0.0


@dataclass(frozen=True)
class AgentOutput:
    content: str
    agent_name: str
    confidence: float       # 0.0〜1.0
    fallback_used: bool = False


@dataclass(frozen=True)
class PipelineResult:
    route: str              # "analysis" | "summary" | "unknown"
    analysis: AgentOutput | None
    summary: AgentOutput | None
    error: str | None


# ─────────────────────────────────────────────────────────────
# 安全ゲート（純粋関数）
# ─────────────────────────────────────────────────────────────

_BLOCKED_PATTERNS = re.compile(
    r"(個人情報|クレジットカード番号|マイナンバー|パスワード)", re.IGNORECASE
)

def validate_input(text: str) -> tuple[bool, str]:
    """入力テキストの安全性チェック。(ok, reason) を返す。"""
    if not text or not text.strip():
        return False, "入力テキストが空です"
    if len(text) > 5000:
        return False, f"入力が長すぎます（{len(text)} 文字 > 5000）"
    if _BLOCKED_PATTERNS.search(text):
        return False, "個人情報・機密情報を含む可能性があるテキストは処理しません"
    return True, ""


def validate_output(output: str, min_length: int = 10) -> tuple[bool, str]:
    """LLM 出力の最小検証。空・極端に短い出力を拒否。"""
    stripped = output.strip() if output else ""
    if not stripped or len(stripped) < min_length:
        return False, f"出力が短すぎます（{len(stripped)} 文字 < {min_length}）"
    return True, ""


# ─────────────────────────────────────────────────────────────
# LLM 呼び出し抽象（実 API / モック を差し替え可能）
# ─────────────────────────────────────────────────────────────

LlmCaller = Callable[[str, AgentInput], str]


def make_anthropic_caller(api_key: str) -> LlmCaller:
    """実 Anthropic API を使う caller を返す。"""
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("pip install anthropic が必要です") from e

    client = anthropic.Anthropic(api_key=api_key)

    def call(system: str, inp: AgentInput) -> str:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=inp.max_tokens,
            temperature=inp.temperature,
            system=system,
            messages=[{"role": "user", "content": inp.text}],
        )
        return msg.content[0].text

    return call


def make_mock_caller(responses: dict[str, str]) -> LlmCaller:
    """テスト用モック caller。system プロンプトの先頭キーワードで応答を選択する。"""
    def call(system: str, inp: AgentInput) -> str:
        for key, response in responses.items():
            if key.lower() in system.lower():
                return response
        return f"[モック応答] 入力: {inp.text[:80]}..."
    return call


# ─────────────────────────────────────────────────────────────
# エージェント（各 1 責務）
# ─────────────────────────────────────────────────────────────

ROUTE_SYSTEM = """あなたはリクエスト分類エージェントです。
ユーザーの入力を読み、以下のいずれかに分類してください：
- "analysis": データ分析・統計・数値処理が主目的
- "summary": 要約・翻訳・説明が主目的
- "unknown": 上記に当てはまらない

必ず 1 語（analysis / summary / unknown）だけを返してください。"""

ANALYSIS_SYSTEM = """あなたはデータ分析エージェントです。
与えられたテキストから数値・傾向・パターンを抽出し、
3 点以内の箇条書きで簡潔にまとめてください。
確信が持てない数値には「（推定）」を付けてください。"""

SUMMARY_SYSTEM = """あなたはサマリーエージェントです。
与えられたテキストを 3 文以内で日本語にまとめてください。
事実のみを述べ、あなた自身の意見は加えないでください。"""


def _run_agent(
    name: str,
    system: str,
    inp: AgentInput,
    caller: LlmCaller,
    fallback_message: str,
    min_output_length: int = 10,
) -> AgentOutput:
    """単一エージェントを実行し AgentOutput を返す。失敗時はフォールバック。"""
    try:
        raw = caller(system, inp)
        ok, reason = validate_output(raw, min_length=min_output_length)
        if not ok:
            return AgentOutput(
                content=fallback_message,
                agent_name=name,
                confidence=0.0,
                fallback_used=True,
            )
        # 信頼度: 出力長で簡易推定（本番では LLM に確信度を返させる）
        confidence = min(1.0, len(raw.strip()) / 200)
        return AgentOutput(content=raw.strip(), agent_name=name, confidence=confidence)
    except Exception as exc:  # noqa: BLE001
        return AgentOutput(
            content=f"{fallback_message}（エラー: {exc}）",
            agent_name=name,
            confidence=0.0,
            fallback_used=True,
        )


# ─────────────────────────────────────────────────────────────
# パイプライン（ルーター → 専門エージェント）
# ─────────────────────────────────────────────────────────────

def run_pipeline(text: str, caller: LlmCaller) -> PipelineResult:
    """
    3 段パイプライン:
      ① 入力ゲート → ② ルーター → ③ 専門エージェント
    どのステップでも失敗した場合は error フィールドに理由を記録して返す。
    """
    # ① 入力ゲート
    ok, reason = validate_input(text)
    if not ok:
        return PipelineResult(route="unknown", analysis=None, summary=None, error=reason)

    base_input = AgentInput(text=text)

    # ② ルーター（分類ラベルは短い語のため min_length=5 で検証）
    route_output = _run_agent(
        name="router",
        system=ROUTE_SYSTEM,
        inp=replace(base_input, max_tokens=10),
        caller=caller,
        fallback_message="unknown",
        min_output_length=5,
    )
    route = route_output.content.strip().lower()
    if route not in ("analysis", "summary", "unknown"):
        route = "unknown"

    # ③ 専門エージェント
    analysis: AgentOutput | None = None
    summary: AgentOutput | None = None

    if route == "analysis":
        analysis = _run_agent(
            name="analyzer",
            system=ANALYSIS_SYSTEM,
            inp=base_input,
            caller=caller,
            fallback_message="分析に失敗しました。入力データを確認してください。",
        )
    elif route == "summary":
        summary = _run_agent(
            name="summarizer",
            system=SUMMARY_SYSTEM,
            inp=base_input,
            caller=caller,
            fallback_message="要約に失敗しました。入力テキストを確認してください。",
        )

    return PipelineResult(route=route, analysis=analysis, summary=summary, error=None)
