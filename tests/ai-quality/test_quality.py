"""
品質テスト (AI-Q-001〜003)

対応観点: V-15 (推薦理由の品質)
対応AC: AC外
合格基準: 90%以上 (設計書 4.4 より)

判定方法:
- AI-Q-001: ルールベースのみ (Phase 1、文字数判定)
- AI-Q-002: ルールベース + LLM-as-a-judge による「個別再判定 → 再集計」(Phase 2)
- AI-Q-003: ルールベースのみ (Phase 1、文体統一判定)

AI-Q-002 の Phase 2 統合 (個別再判定 → 再集計):
- 各推薦理由について、まずルールベースで「学年/苦手/理解済み単元のキーワード含有」をチェック
- 含有なし → LLM judge で「文脈的に踏まえているか」を判定
- LLM judge が「踏まえている」と判断したら「言及あり」扱いに格上げ
- 全推薦理由で「言及あり」率を再計算し、90%以上で合格
"""

import pytest

from tests.ai_quality.fixtures.unit_master import find_unit_by_id
from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.assertions import (
    contains_keyword,
    is_consistent_style,
    is_within_char_range,
)
from tests.ai_quality.helpers.llm_judge import judge_with_llm
from tests.ai_quality.helpers.llm_judge_prompts import INPUT_REFERENCE_JUDGE_PROMPT


pytestmark = pytest.mark.quality


PASS_RATE_THRESHOLD = 0.90


@pytest.fixture(scope="module")
def all_recommendations(golden_test_set) -> list[dict]:
    """GT-001〜005 を実行した推薦単元のフラットリスト"""
    results = []
    for gt in golden_test_set:
        response = recommend(
            gt["input"]["grade"],
            gt["input"].get("understoodIds", []),
            gt["input"].get("weakIds", []),
        )
        for rec in response["recommendations"]:
            results.append({
                "gt_id": gt["id"],
                "input": gt["input"],
                "rec": rec,
            })
    return results


def _format_units_for_prompt(unit_ids: list[str]) -> str:
    if not unit_ids:
        return "(なし)"
    parts = []
    for uid in unit_ids:
        u = find_unit_by_id(uid)
        if u:
            parts.append(f"「{u['name']}」")
    return "、".join(parts) if parts else "(なし)"


def test_AI_Q_001_char_count_within_range(recorder, all_recommendations):
    """
    AI-Q-001: 推薦理由の文字数 (Phase 1 のみ)

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    判定方法: 推薦理由の文字数を集計
    合格基準: 50〜150 字の範囲内が 90% 以上
    """
    total = len(all_recommendations)
    in_range = 0
    out_examples: list[dict] = []
    for entry in all_recommendations:
        reason = entry["rec"].get("reason", "")
        if is_within_char_range(reason, 50, 150):
            in_range += 1
        else:
            out_examples.append({
                "gt_id": entry["gt_id"],
                "unitId": entry["rec"].get("unitId"),
                "char_count": len(reason),
            })

    rate = (in_range / total) if total else 0.0
    passed = rate >= PASS_RATE_THRESHOLD

    recorder.record(
        test_id="AI-Q-001",
        category="quality",
        passed=passed,
        metrics={
            "rule_based": {
                "total": total,
                "in_range": in_range,
                "out_of_range": total - in_range,
                "pass_rate": rate,
                "threshold": PASS_RATE_THRESHOLD,
                "out_of_range_examples": out_examples[:5],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-Q-001: 文字数範囲内率 {rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"範囲外例: {out_examples[:3]}"
    )


def test_AI_Q_002_mention_rate_for_input_units(recorder, all_recommendations, llm_traces_dir):
    """
    AI-Q-002: 推薦理由の品質 (入力単元への言及率) — Phase 2 個別再判定型

    Phase 1: 学年/苦手/理解済み単元名のキーワード文字列マッチ
    Phase 2: マッチなしの推薦理由について LLM judge で「文脈的に踏まえているか」を判定

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    合格基準: 言及率 90% 以上
    """
    total = len(all_recommendations)
    rule_has_mention = 0
    llm_results: list[dict] = []
    rescued_count = 0  # ルールベースで言及なし → LLM で「あり」と再判定された数
    final_has_mention = 0
    no_mention_examples: list[dict] = []

    for entry in all_recommendations:
        text = entry["rec"].get("reason", "")
        grade = entry["input"]["grade"]
        understood_names = [
            (find_unit_by_id(uid) or {}).get("name", "")
            for uid in entry["input"].get("understoodIds", [])
        ]
        weak_names = [
            (find_unit_by_id(uid) or {}).get("name", "")
            for uid in entry["input"].get("weakIds", [])
        ]
        candidates = [grade] + understood_names + weak_names
        candidates = [c for c in candidates if c]

        # ===== Phase 1: ルールベース =====
        rule_passed = any(contains_keyword(text, c) for c in candidates)

        if rule_passed:
            rule_has_mention += 1
            final_has_mention += 1
            continue

        # ===== Phase 2: LLM judge で文脈的言及を確認 =====
        rec = entry["rec"]
        rec_unit = find_unit_by_id(rec.get("unitId", "")) or {}
        llm = judge_with_llm(
            prompt_template=INPUT_REFERENCE_JUDGE_PROMPT,
            variables={
                "grade": grade,
                "understood": _format_units_for_prompt(entry["input"].get("understoodIds", [])),
                "weak": _format_units_for_prompt(entry["input"].get("weakIds", [])),
                "recommended_unit_name": rec.get("unitName", ""),
                "recommended_unit_grade": rec_unit.get("grade", rec.get("grade", "")),
                "reason": text,
            },
            test_id="AI-Q-002",
            gt_id=entry["gt_id"],
            traces_dir=llm_traces_dir,
        )
        llm_results.append({
            "gt_id": entry["gt_id"],
            "unitId": rec.get("unitId"),
            "candidates_checked": candidates,
            "llm_passed": llm["passed"],
            "llm_score": llm["score"],
            "llm_reasoning": llm["reasoning"],
            "fallback": llm["fallback"],
        })

        # フォールバック時はルールベース結果 (=mention なし) を採用、保守的に未言及扱い
        if not llm["fallback"] and llm["passed"]:
            rescued_count += 1
            final_has_mention += 1
        else:
            no_mention_examples.append({
                "gt_id": entry["gt_id"],
                "unitId": rec.get("unitId"),
                "candidates_checked": candidates,
                "llm_score": llm.get("score", 0),
            })

    rule_rate = (rule_has_mention / total) if total else 0.0
    final_rate = (final_has_mention / total) if total else 0.0
    final_passed = final_rate >= PASS_RATE_THRESHOLD

    rule_based = {
        "total": total,
        "rule_has_mention": rule_has_mention,
        "rule_no_mention": total - rule_has_mention,
        "rule_pass_rate": rule_rate,
        "threshold": PASS_RATE_THRESHOLD,
    }

    if final_passed:
        if rescued_count > 0:
            final_judgment = f"rule + llm rescued (passed: {rescued_count} reclassified as mentioned)"
        else:
            final_judgment = "rule alone (passed)"
    else:
        final_judgment = f"rule + llm agreed (failed: final rate {final_rate:.0%} < {PASS_RATE_THRESHOLD:.0%})"

    recorder.record(
        test_id="AI-Q-002",
        category="quality",
        passed=final_passed,
        metrics={
            "rule_based": rule_based,
            "llm_judge": llm_results if llm_results else None,
            "final_judgment": final_judgment,
            "final_has_mention": final_has_mention,
            "final_rate": final_rate,
            "rescued_count": rescued_count,
            "no_mention_examples_after_llm": no_mention_examples[:5],
        },
    )
    assert final_passed, (
        f"AI-Q-002: 入力単元言及率 {final_rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"  ルールベース率: {rule_rate:.2%}, LLM 救済: {rescued_count} 件\n"
        f"  最終未言及例: {no_mention_examples[:3]}"
    )


def test_AI_Q_003_consistent_writing_style(recorder, all_recommendations):
    """
    AI-Q-003: 推薦理由の品質 (文体統一) — Phase 1 のみ

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    判定方法: 各推薦理由の文末が「である調」or「ですます調」で統一されているか
    合格基準: 統一率 90% 以上

    集計式:
        統一率 = (文体統一OKの推薦理由数) / (評価対象の推薦理由数)
    """
    total = len(all_recommendations)
    consistent = 0
    inconsistent_examples: list[dict] = []
    for entry in all_recommendations:
        text = entry["rec"].get("reason", "")
        if is_consistent_style(text):
            consistent += 1
        else:
            inconsistent_examples.append({
                "gt_id": entry["gt_id"],
                "unitId": entry["rec"].get("unitId"),
                "reason_excerpt": text[:80],
            })

    rate = (consistent / total) if total else 0.0
    passed = rate >= PASS_RATE_THRESHOLD

    recorder.record(
        test_id="AI-Q-003",
        category="quality",
        passed=passed,
        metrics={
            "rule_based": {
                "total": total,
                "consistent": consistent,
                "inconsistent": total - consistent,
                "pass_rate": rate,
                "threshold": PASS_RATE_THRESHOLD,
                "inconsistent_examples": inconsistent_examples[:5],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-Q-003: 文体統一率 {rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"非統一例: {inconsistent_examples[:3]}"
    )
