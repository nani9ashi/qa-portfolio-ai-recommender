"""
LLM-as-a-judge ヘルパー (Phase 2)

Anthropic Claude API を判定 AI として呼び出し、JSON パース・トレース保存・
フォールバック処理を一元化する。

使い方:
    from tests.ai_quality.helpers.llm_judge import judge_with_llm
    from tests.ai_quality.helpers.llm_judge_prompts import ACCURACY_JUDGE_PROMPT

    result = judge_with_llm(
        prompt_template=ACCURACY_JUDGE_PROMPT,
        variables={"grade": "中2", "understood": "...", ...},
        test_id="AI-A-001",
        gt_id="GT-001",
        traces_dir=run_dir / "llm_judge_traces",
    )
    # result = {"score": 4, "passed": True, "reasoning": "...", "raw_response": "...",
    #          "model": "claude-sonnet-4-6", "fallback": False, "error": None}
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any, Optional


# ===== 設定 =====

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_PASS_THRESHOLD = 3
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 500
RETRY_COUNT = 1  # JSON パース失敗時に1回だけリトライ


def _model() -> str:
    return os.environ.get("LLM_JUDGE_MODEL", DEFAULT_MODEL)


def _pass_threshold() -> int:
    return int(os.environ.get("LLM_JUDGE_PASS_THRESHOLD", str(DEFAULT_PASS_THRESHOLD)))


def _temperature() -> float:
    return float(os.environ.get("LLM_JUDGE_TEMPERATURE", str(DEFAULT_TEMPERATURE)))


def _max_tokens() -> int:
    return int(os.environ.get("LLM_JUDGE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))


def _api_key() -> Optional[str]:
    """ANTHROPIC_API_KEY を環境変数から取得 (conftest.py で .env ロード済み)"""
    return os.environ.get("ANTHROPIC_API_KEY")


# ===== 主関数 =====

def judge_with_llm(
    prompt_template: Template,
    variables: dict[str, Any],
    test_id: str,
    gt_id: str = "",
    traces_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """
    LLM-as-a-judge による意味的判定を実行する。

    Args:
        prompt_template: helpers/llm_judge_prompts.py の Template 定数
                        (string.Template、${name} 形式で変数指定)
        variables: プロンプト内 ${key} を置換する辞書 (Template.substitute で展開)
        test_id: 対応テスト ID (例: "AI-A-001")
        gt_id: 関連ゴールデンテスト ID (任意、トレース用)
        traces_dir: トレース JSONL の保存先ディレクトリ (None なら保存しない)

    Returns:
        dict:
          - "score":     int (1-5、フォールバック時は 0)
          - "passed":    bool (score >= LLM_JUDGE_PASS_THRESHOLD)
          - "reasoning": str (判定理由 or フォールバック理由)
          - "raw_response": str (Claude の生レスポンス、フォールバック時は空)
          - "model":     str (使用モデル ID)
          - "fallback":  bool (LLM 呼び出し or JSON パースに失敗したら True)
          - "error":     str | None (フォールバック時のエラーメッセージ)
    """
    api_key = _api_key()
    if not api_key:
        return _fallback_result(
            test_id=test_id,
            gt_id=gt_id,
            traces_dir=traces_dir,
            error="ANTHROPIC_API_KEY が設定されていません。tests/ai-quality/.env または backend/.env を確認してください。",
            prompt_text="",
            variables=variables,
        )

    # プロンプト整形 (string.Template の substitute を使用、JSON の {} と衝突しない)
    try:
        prompt_text = prompt_template.substitute(**variables)
    except KeyError as e:
        return _fallback_result(
            test_id=test_id,
            gt_id=gt_id,
            traces_dir=traces_dir,
            error=f"プロンプトテンプレートの変数 {e} が variables に含まれていません",
            prompt_text=getattr(prompt_template, "template", str(prompt_template)),
            variables=variables,
        )
    except ValueError as e:
        # Template の構文エラー (不正な $ 構文等)
        return _fallback_result(
            test_id=test_id,
            gt_id=gt_id,
            traces_dir=traces_dir,
            error=f"プロンプトテンプレートの構文エラー: {e}",
            prompt_text=getattr(prompt_template, "template", str(prompt_template)),
            variables=variables,
        )

    # LLM 呼び出し (1回 + リトライ最大1回)
    last_error: Optional[str] = None
    last_raw: str = ""
    for attempt in range(RETRY_COUNT + 1):
        try:
            raw = _call_claude(api_key=api_key, prompt_text=prompt_text)
            last_raw = raw
            parsed = _parse_judge_json(raw)
            score = int(parsed.get("score", 0))
            reasoning = str(parsed.get("reasoning", ""))
            passed = score >= _pass_threshold()

            result = {
                "score": score,
                "passed": passed,
                "reasoning": reasoning,
                "raw_response": raw,
                "model": _model(),
                "fallback": False,
                "error": None,
            }
            _write_trace(
                test_id=test_id,
                gt_id=gt_id,
                traces_dir=traces_dir,
                prompt_text=prompt_text,
                variables=variables,
                raw_response=raw,
                parsed=result,
                error=None,
                attempt=attempt,
            )
            return result
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt >= RETRY_COUNT:
                break

    # 全試行失敗 → フォールバック
    return _fallback_result(
        test_id=test_id,
        gt_id=gt_id,
        traces_dir=traces_dir,
        error=last_error or "unknown error",
        prompt_text=prompt_text,
        variables=variables,
        raw_response=last_raw,
    )


# ===== Claude API 呼び出し =====

def _call_claude(api_key: str, prompt_text: str) -> str:
    """Anthropic SDK で Claude を呼び出して生 text を返す"""
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic SDK が import できません。`pip install -r tests/ai-quality/requirements.txt` を実行してください。"
        ) from e

    try:
        client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Anthropic クライアントの初期化に失敗: {e}") from e

    try:
        response = client.messages.create(
            model=_model(),
            max_tokens=_max_tokens(),
            temperature=_temperature(),
            messages=[{"role": "user", "content": prompt_text}],
        )
    except Exception as e:
        msg = str(e)
        if "model" in msg.lower() and ("not found" in msg.lower() or "invalid" in msg.lower()):
            raise RuntimeError(
                f"LLM_JUDGE_MODEL を確認してください。現在の値: '{_model()}'。"
                f"原因: {msg}"
            ) from e
        raise

    text_block = next((b for b in response.content if getattr(b, "type", "") == "text"), None)
    if text_block is None:
        raise RuntimeError("Claude API レスポンスに text ブロックが含まれていません")
    return text_block.text


# ===== JSON パース (寛容版) =====

def _parse_judge_json(raw: str) -> dict[str, Any]:
    """
    LLM の生レスポンスから JSON を抽出してパース。
    1段階目: 素直に JSON.loads
    2段階目: ```json ... ``` ブロック / 最初の {...} ブロックを抽出
    """
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ```json ... ``` ブロックを優先
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    # それでもダメなら最初の {...} ブロックを抽出
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        return json.loads(brace.group(0))

    raise ValueError(f"レスポンスから JSON を抽出できませんでした: {raw[:200]}")


# ===== フォールバック =====

def _fallback_result(
    test_id: str,
    gt_id: str,
    traces_dir: Optional[Path],
    error: str,
    prompt_text: str,
    variables: dict[str, Any],
    raw_response: str = "",
) -> dict[str, Any]:
    """LLM 失敗時のフォールバック結果。テスト側はこれを見て『ルールベース結果を最終判定として採用』を判断する"""
    sys.stderr.write(f"\n[llm_judge] フォールバック発動 ({test_id}, {gt_id}): {error}\n")
    result = {
        "score": 0,
        "passed": False,
        "reasoning": f"[フォールバック] LLM judge 実行不可: {error}",
        "raw_response": raw_response,
        "model": _model(),
        "fallback": True,
        "error": error,
    }
    _write_trace(
        test_id=test_id,
        gt_id=gt_id,
        traces_dir=traces_dir,
        prompt_text=prompt_text,
        variables=variables,
        raw_response=raw_response,
        parsed=result,
        error=error,
        attempt=RETRY_COUNT + 1,
    )
    return result


# ===== トレース保存 =====

def _write_trace(
    test_id: str,
    gt_id: str,
    traces_dir: Optional[Path],
    prompt_text: str,
    variables: dict[str, Any],
    raw_response: str,
    parsed: dict[str, Any],
    error: Optional[str],
    attempt: int,
) -> None:
    """テスト ID 別の JSONL ファイルに 1行追記する"""
    if traces_dir is None:
        return
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        trace_file = traces_dir / f"{test_id}.jsonl"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "test_id": test_id,
            "gt_id": gt_id,
            "model": parsed.get("model", _model()),
            "attempt": attempt,
            "criteria": variables,
            "target_text": variables.get("reason") or variables.get("all_runs_text") or "",
            "prompt": prompt_text,
            "raw_response": raw_response,
            "parsed_score": parsed.get("score", 0),
            "parsed_reasoning": parsed.get("reasoning", ""),
            "passed": parsed.get("passed", False),
            "fallback": parsed.get("fallback", False),
            "error": error,
        }
        with trace_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"\n[llm_judge] トレース保存失敗 ({test_id}): {e}\n")
