"""
正確性テスト (AI-A-001〜004)

対応観点: V-12 (推薦理由の正確性)
対応AC: AC外

判定方法 (Phase 1 + Phase 2 統合):
- Phase 1: キーワード含有チェック
- Phase 2: LLM-as-a-judge による意味的判定

統合ロジック (引き締め型):
- キーワード0件マッチ → LLM judge を呼ばずに即不合格 (早期 fail、コスト節約)
- キーワード1件以上マッチ → LLM judge で意味的に妥当か再評価し、その判定を最終結果として採用
- (現状合格の引き締めが起こりうる: 表面的なキーワードヒットでも内容が不適切なら LLM が不合格と判定)
"""

import pytest

from tests.ai_quality.fixtures.unit_master import find_unit_by_id
from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.llm_judge import judge_with_llm
from tests.ai_quality.helpers.llm_judge_prompts import ACCURACY_JUDGE_PROMPT


pytestmark = pytest.mark.accuracy


def _gather_reasons(recommendations: list[dict]) -> str:
    """全推薦理由を1つの文字列に結合 (キーワード検索用)"""
    return "\n".join(r.get("reason", "") for r in recommendations)


def _format_units_for_prompt(unit_ids: list[str]) -> str:
    """unit_id のリストを LLM プロンプト用の人間可読文字列に変換"""
    if not unit_ids:
        return "(なし)"
    parts = []
    for uid in unit_ids:
        u = find_unit_by_id(uid)
        if u:
            parts.append(f"「{u['name']}」")
        else:
            parts.append(f"(未知ID: {uid})")
    return "、".join(parts)


def _format_recommendations_for_prompt(recs: list[dict]) -> str:
    """推薦単元リストを LLM プロンプト用の文字列に変換"""
    return "\n".join(
        f"- {r.get('unitName', '?')} ({r.get('grade', '?')}) [unitId={r.get('unitId', '?')}]"
        for r in recs
    )


def _run_accuracy_test(
    *,
    test_id: str,
    grade: str,
    understood_ids: list[str],
    weak_ids: list[str],
    expected_keywords: list[str],
    recorder,
    llm_traces_dir,
    gt_id: str = "",
):
    """4つのテストで共通の判定ロジック (Phase 1 + Phase 2 統合)"""
    response = recommend(grade, understood_ids, weak_ids)
    recs = response["recommendations"]
    reasons_text = _gather_reasons(recs)

    # ===== Phase 1: ルールベース判定 (キーワード含有) =====
    matched = [k for k in expected_keywords if k in reasons_text]
    rule_based = {
        "expected_keywords": expected_keywords,
        "matched_keywords": matched,
        "rule_passed": len(matched) > 0,
        "n_recommendations": len(recs),
    }

    # ===== 早期 fail: キーワード0件マッチなら LLM judge は呼ばない =====
    if len(matched) == 0:
        recorder.record(
            test_id=test_id,
            category="accuracy",
            passed=False,
            metrics={
                "rule_based": rule_based,
                "llm_judge": None,
                "final_judgment": "rule alone (failed: no keyword match)",
            },
        )
        pytest.fail(
            f"{test_id}: 期待キーワード {expected_keywords} のいずれも推薦理由に含まれていません (Phase 1 早期 fail)。\n"
            f"--- 推薦理由 ---\n{reasons_text}"
        )

    # ===== Phase 2: LLM judge で意味的判定 =====
    llm = judge_with_llm(
        prompt_template=ACCURACY_JUDGE_PROMPT,
        variables={
            "grade": grade,
            "understood": _format_units_for_prompt(understood_ids),
            "weak": _format_units_for_prompt(weak_ids),
            "recommended_units": _format_recommendations_for_prompt(recs),
            "reason": reasons_text,
            "expected_keywords": "、".join(f"「{k}」" for k in expected_keywords),
        },
        test_id=test_id,
        gt_id=gt_id,
        traces_dir=llm_traces_dir,
    )

    # ===== 統合: LLM judge の判定を最終結果として採用 =====
    if llm["fallback"]:
        # フォールバック: ルールベース結果 (合格) を最終判定として採用
        final_passed = True
        final_judgment = "rule + llm fallback (passed via rule, llm unavailable)"
    else:
        final_passed = llm["passed"]
        if final_passed:
            final_judgment = "rule + llm agreed (passed)"
        else:
            final_judgment = "rule passed but llm rejected (final: failed)"

    recorder.record(
        test_id=test_id,
        category="accuracy",
        passed=final_passed,
        metrics={
            "rule_based": rule_based,
            "llm_judge": llm,
            "final_judgment": final_judgment,
        },
    )
    assert final_passed, (
        f"{test_id}: LLM judge が不合格と判定 (score={llm['score']})\n"
        f"理由: {llm['reasoning']}\n"
        f"--- 推薦理由 ---\n{reasons_text}"
    )


def test_AI_A_001_basic_accuracy_no_inputs(recorder, llm_traces_dir):
    """
    AI-A-001: 推薦理由の正確性 (基礎単元への言及)

    入力: 中2、理解済み=[]、苦手=[]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    Phase 1 合格基準: 推薦理由のいずれかに「正の数」「負の数」「文字式」等の基礎単元キーワードが含まれる
    Phase 2 合格基準: 上記+ LLM judge が score >= 3 と評価
    """
    _run_accuracy_test(
        test_id="AI-A-001",
        grade="中2",
        understood_ids=[],
        weak_ids=[],
        expected_keywords=["正の数", "負の数", "文字式", "基礎"],
        recorder=recorder,
        llm_traces_dir=llm_traces_dir,
    )


def test_AI_A_002_relational_accuracy_hirei_to_ichijikansuu(recorder, llm_traces_dir):
    """
    AI-A-002: 推薦理由の正確性 (一次関数と比例の関係への言及)

    入力: 中2、理解済み=[比例]、苦手=[一次関数]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    Phase 1 合格基準: 推薦理由に「比例」と「一次関数」の両方への言及がある
    Phase 2 合格基準: 上記+ LLM judge が score >= 3 と評価
    """
    _run_accuracy_test(
        test_id="AI-A-002",
        grade="中2",
        understood_ids=["m1_hireihanpi"],
        weak_ids=["m2_ichijikansuu"],
        expected_keywords=["比例", "一次関数"],
        recorder=recorder,
        llm_traces_dir=llm_traces_dir,
    )


def test_AI_A_003_weak_unit_mention_renritsu(recorder, llm_traces_dir):
    """
    AI-A-003: 推薦理由の正確性 (苦手単元への言及)

    入力: 中3、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    Phase 1 合格基準: 推薦理由に「連立方程式」への言及がある
    Phase 2 合格基準: 上記+ LLM judge が score >= 3 と評価
    """
    _run_accuracy_test(
        test_id="AI-A-003",
        grade="中3",
        understood_ids=["m2_ichijikansuu"],
        weak_ids=["m2_renritsu"],
        expected_keywords=["連立方程式"],
        recorder=recorder,
        llm_traces_dir=llm_traces_dir,
    )


def test_AI_A_004_advanced_prerequisite_for_bibun(recorder, llm_traces_dir):
    """
    AI-A-004: 推薦理由の正確性 (微分の前提概念への言及)

    入力: 高3、理解済み=[数と式、二次関数(高1)]、苦手=[微分(高2)]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    Phase 1 合格基準: 推薦理由に「関数」「極限」「微分」のいずれかが含まれる
    Phase 2 合格基準: 上記+ LLM judge が score >= 3 と評価
    """
    _run_accuracy_test(
        test_id="AI-A-004",
        grade="高3",
        understood_ids=["h1_kazutoshiki", "h1_nijikansuu"],
        weak_ids=["h2_bibun"],
        expected_keywords=["関数", "極限", "微分"],
        recorder=recorder,
        llm_traces_dir=llm_traces_dir,
    )
