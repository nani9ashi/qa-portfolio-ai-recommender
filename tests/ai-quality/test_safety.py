"""
安全性テスト (AI-S-001〜003)

対応観点: V-14 (推薦理由の安全性)
対応AC: AC外
合格基準: 検出率5%未満 (設計書 4.3 より)

判定方法:
- AI-S-001: ルールベースのみ (Phase 1 のまま、十分機能している)
- AI-S-002: ルールベース + LLM-as-a-judge による「救済型」判定 (Phase 2)
- AI-S-003: ルールベースのみ (Phase 1 のまま)

AI-S-002 の Phase 2 統合 (救済型):
- ルールベースで invalid_count = 0 → そのまま合格 (LLM 不要)
- invalid_count > 0 → LLM judge で「教育的に妥当な未来言及か」を判定し、
  全フラグが LLM 合格判定なら最終合格に格上げ。1件でも不合格と判定されれば不合格。
"""

import pytest

from tests.ai_quality.fixtures.unit_master import find_unit_by_id
from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.assertions import (
    extract_unit_mentions,
    has_math_context,
    is_known_unit,
    validate_prerequisite_mention,
)
from tests.ai_quality.helpers.llm_judge import judge_with_llm
from tests.ai_quality.helpers.llm_judge_prompts import PREREQUISITE_JUDGE_PROMPT


pytestmark = pytest.mark.safety


DETECTION_RATE_THRESHOLD = 0.05


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


def test_AI_S_001_no_hallucinated_unit_names(recorder, all_recommendations):
    """
    AI-S-001: 推薦理由内の単元名がハルシネーションでないか (Phase 1 のみ)

    判定方法: 推薦理由から抽出された単元名を units.js + 別名辞書と照合
    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: ハルシネーション検出率 5%未満
    """
    total_mentions = 0
    hallucinated: list[dict] = []
    for entry in all_recommendations:
        text = entry["rec"].get("reason", "")
        mentions = extract_unit_mentions(text)
        for m in mentions:
            total_mentions += 1
            if not is_known_unit(m):
                hallucinated.append({
                    "gt_id": entry["gt_id"],
                    "unitId": entry["rec"].get("unitId"),
                    "mention": m,
                })

    rate = (len(hallucinated) / total_mentions) if total_mentions else 0.0
    passed = rate < DETECTION_RATE_THRESHOLD

    recorder.record(
        test_id="AI-S-001",
        category="safety",
        passed=passed,
        metrics={
            "rule_based": {
                "total_mentions": total_mentions,
                "hallucinated_count": len(hallucinated),
                "hallucination_rate": rate,
                "threshold": DETECTION_RATE_THRESHOLD,
                "hallucinated_examples": hallucinated[:5],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-S-001: ハルシネーション率 {rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"検出例: {hallucinated[:3]}"
    )


def test_AI_S_002_prerequisite_relationship(recorder, all_recommendations, llm_traces_dir):
    """
    AI-S-002: 推薦理由の安全性 (前提関係誤認) — Phase 2 救済型

    Phase 1 (ルールベース): 推薦単元の prerequisite chain・推薦単元自身・入力単元のいずれにも
                          該当しない単元への言及を「誤った関係」としてフラグ。
    Phase 2 (LLM-as-a-judge): フラグされた言及について、LLM が「教育的に妥当な未来言及か」
                              を判定。全フラグが LLM 合格と判定されれば最終合格に格上げ。

    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: 誤った関係の検出率 5%未満
    """
    # ===== Phase 1: ルールベース判定 =====
    total_mentions = 0
    flagged_entries: list[dict] = []  # ルールベースでフラグされたエントリ詳細

    for entry in all_recommendations:
        rec = entry["rec"]
        mentions = extract_unit_mentions(rec.get("reason", ""))
        result = validate_prerequisite_mention(
            recommended_unit_id=rec.get("unitId", ""),
            mentioned_unit_names=mentions,
            understood_ids=entry["input"].get("understoodIds", []),
            weak_ids=entry["input"].get("weakIds", []),
        )
        total_mentions += result["valid_count"] + result["invalid_count"]
        if result["invalid_mentions"]:
            flagged_entries.append({
                "entry": entry,
                "invalid_mentions": result["invalid_mentions"],
            })

    rule_based = {
        "total_mentions": total_mentions,
        "rule_invalid_count": sum(len(f["invalid_mentions"]) for f in flagged_entries),
        "rule_invalid_rate": (
            sum(len(f["invalid_mentions"]) for f in flagged_entries) / total_mentions
        ) if total_mentions else 0.0,
        "threshold": DETECTION_RATE_THRESHOLD,
        "flagged_entries_count": len(flagged_entries),
    }

    # ===== Phase 1 合格 (フラグなし) → そのまま合格、LLM judge 不要 =====
    if not flagged_entries:
        recorder.record(
            test_id="AI-S-002",
            category="safety",
            passed=True,
            metrics={
                "rule_based": rule_based,
                "llm_judge": None,
                "final_judgment": "rule alone (passed: no flagged mentions)",
            },
        )
        return

    # ===== Phase 2: フラグされたエントリ毎に LLM judge で「教育的に妥当な未来言及か」判定 =====
    llm_results: list[dict] = []
    truly_invalid_count = 0
    for flagged in flagged_entries:
        entry = flagged["entry"]
        rec = entry["rec"]
        rec_unit = find_unit_by_id(rec.get("unitId", "")) or {}
        llm = judge_with_llm(
            prompt_template=PREREQUISITE_JUDGE_PROMPT,
            variables={
                "grade": entry["input"]["grade"],
                "understood": _format_units_for_prompt(entry["input"].get("understoodIds", [])),
                "weak": _format_units_for_prompt(entry["input"].get("weakIds", [])),
                "recommended_unit_id": rec.get("unitId", ""),
                "recommended_unit_name": rec.get("unitName", ""),
                "recommended_unit_grade": rec_unit.get("grade", rec.get("grade", "")),
                "flagged_mentions": "、".join(f"「{m}」" for m in flagged["invalid_mentions"]),
                "reason": rec.get("reason", ""),
            },
            test_id="AI-S-002",
            gt_id=entry["gt_id"],
            traces_dir=llm_traces_dir,
        )
        llm_results.append({
            "gt_id": entry["gt_id"],
            "unitId": rec.get("unitId"),
            "flagged_mentions": flagged["invalid_mentions"],
            "llm_passed": llm["passed"],
            "llm_score": llm["score"],
            "llm_reasoning": llm["reasoning"],
            "fallback": llm["fallback"],
        })
        # フォールバック時は「誤った関係」として保守的にカウント
        if llm["fallback"] or not llm["passed"]:
            truly_invalid_count += len(flagged["invalid_mentions"])

    final_rate = (truly_invalid_count / total_mentions) if total_mentions else 0.0
    final_passed = final_rate < DETECTION_RATE_THRESHOLD

    rescued_count = (
        rule_based["rule_invalid_count"] - truly_invalid_count
    )

    if final_passed:
        if rescued_count > 0:
            final_judgment = f"rule + llm rescued (passed: {rescued_count} mentions reclassified as valid)"
        else:
            final_judgment = "rule + llm agreed (passed)"
    else:
        final_judgment = f"rule + llm agreed (failed: {truly_invalid_count}/{total_mentions} truly invalid)"

    recorder.record(
        test_id="AI-S-002",
        category="safety",
        passed=final_passed,
        metrics={
            "rule_based": rule_based,
            "llm_judge": llm_results,
            "final_judgment": final_judgment,
            "final_invalid_count": truly_invalid_count,
            "final_invalid_rate": final_rate,
            "rescued_count": rescued_count,
        },
    )
    assert final_passed, (
        f"AI-S-002: 最終的な誤った前提関係率 {final_rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"LLM judge 後の真の不合格数: {truly_invalid_count}/{total_mentions}"
    )


def test_AI_S_003_no_off_topic_information(recorder, all_recommendations):
    """
    AI-S-003: 推薦理由の安全性 (無関係情報の混入) — Phase 1 のみ

    判定方法: 数学関連語彙の含有数で判定
    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: 無関係情報の混入率 5%未満
    """
    total = len(all_recommendations)
    off_topic: list[dict] = []
    for entry in all_recommendations:
        text = entry["rec"].get("reason", "")
        if not has_math_context(text, threshold=3):
            off_topic.append({
                "gt_id": entry["gt_id"],
                "unitId": entry["rec"].get("unitId"),
                "reason": text,
            })

    rate = (len(off_topic) / total) if total else 0.0
    passed = rate < DETECTION_RATE_THRESHOLD

    recorder.record(
        test_id="AI-S-003",
        category="safety",
        passed=passed,
        metrics={
            "rule_based": {
                "total_reasons": total,
                "off_topic_count": len(off_topic),
                "off_topic_rate": rate,
                "threshold": DETECTION_RATE_THRESHOLD,
                "off_topic_examples": off_topic[:3],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-S-003: 無関係情報混入率 {rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"検出例: {off_topic[:2]}"
    )
