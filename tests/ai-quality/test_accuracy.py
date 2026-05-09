"""
正確性テスト (AI-A-001〜004)

対応観点: V-12 (推薦理由の正確性)
対応AC: AC外
判定方法 (Phase 1): キーワード含有チェックのみ

Phase 2 で追加予定:
- LLM-as-a-judge による意味的判定 (推薦理由が「正しく」入力単元を扱っているかを評価)
- 例: AI-A-002 で「比例と一次関数の関係」が単に語句として出るだけでなく、
  論理的に妥当な関係を述べているかをチェック
"""

import pytest

from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.assertions import contains_any_keyword


pytestmark = pytest.mark.accuracy


def _gather_reasons(recommendations: list[dict]) -> str:
    """全推薦理由を1つの文字列に結合 (キーワード検索用)"""
    return "\n".join(r.get("reason", "") for r in recommendations)


def test_AI_A_001_basic_accuracy_no_inputs(recorder):
    """
    AI-A-001: 推薦理由の正確性 (基礎単元への言及)

    入力: 中2、理解済み=[]、苦手=[]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    合格基準: 推薦理由のいずれかに「正の数」「負の数」「文字式」等の基礎単元キーワードが含まれる
    """
    response = recommend("中2", [], [])
    reasons_text = _gather_reasons(response["recommendations"])
    expected_keywords = ["正の数", "負の数", "文字式", "基礎"]
    matched = [k for k in expected_keywords if k in reasons_text]
    passed = len(matched) > 0

    recorder.record(
        test_id="AI-A-001",
        category="accuracy",
        passed=passed,
        metrics={
            "expected_keywords": expected_keywords,
            "matched_keywords": matched,
            "n_recommendations": len(response["recommendations"]),
        },
    )
    assert passed, (
        f"AI-A-001: 期待キーワード {expected_keywords} のいずれも推薦理由に含まれていません。\n"
        f"--- 推薦理由 ---\n{reasons_text}"
    )


def test_AI_A_002_relational_accuracy_hirei_to_ichijikansuu(recorder, golden_by_id):
    """
    AI-A-002: 推薦理由の正確性 (一次関数と比例の関係への言及)

    入力: 中2、理解済み=[比例]、苦手=[一次関数]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    合格基準: 推薦理由に「比例」と「一次関数」の両方への言及がある
    """
    response = recommend("中2", ["m1_hireihanpi"], ["m2_ichijikansuu"])
    reasons_text = _gather_reasons(response["recommendations"])
    has_hirei = "比例" in reasons_text
    has_ichiji = "一次関数" in reasons_text
    passed = has_hirei and has_ichiji

    recorder.record(
        test_id="AI-A-002",
        category="accuracy",
        passed=passed,
        metrics={"has_hirei": has_hirei, "has_ichijikansuu": has_ichiji},
    )
    assert passed, (
        f"AI-A-002: 「比例」「一次関数」両方への言及が必要。"
        f"hirei={has_hirei}, ichiji={has_ichiji}\n--- 推薦理由 ---\n{reasons_text}"
    )


def test_AI_A_003_weak_unit_mention_renritsu(recorder):
    """
    AI-A-003: 推薦理由の正確性 (苦手単元への言及)

    入力: 中3、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    合格基準: 推薦理由に「連立方程式」への言及がある
    """
    response = recommend("中3", ["m2_ichijikansuu"], ["m2_renritsu"])
    reasons_text = _gather_reasons(response["recommendations"])
    passed = "連立方程式" in reasons_text

    recorder.record(
        test_id="AI-A-003",
        category="accuracy",
        passed=passed,
        metrics={"weak_keyword": "連立方程式", "found": passed},
    )
    assert passed, (
        f"AI-A-003: 苦手単元「連立方程式」への言及が必要。\n"
        f"--- 推薦理由 ---\n{reasons_text}"
    )


def test_AI_A_004_advanced_prerequisite_for_bibun(recorder):
    """
    AI-A-004: 推薦理由の正確性 (微分の前提概念への言及)

    入力: 高2、理解済み=[数と式、二次関数(高1)]、苦手=[微分(高2)]
    対応AC: AC外
    観点: V-12: 推薦理由の正確性
    合格基準: 推薦理由に「関数」「極限」「微分」のいずれかが含まれる
    """
    response = recommend("高3", ["h1_kazutoshiki", "h1_nijikansuu"], ["h2_bibun"])
    reasons_text = _gather_reasons(response["recommendations"])
    expected_keywords = ["関数", "極限", "微分"]
    matched = [k for k in expected_keywords if k in reasons_text]
    passed = len(matched) > 0

    recorder.record(
        test_id="AI-A-004",
        category="accuracy",
        passed=passed,
        metrics={"expected_keywords": expected_keywords, "matched_keywords": matched},
    )
    assert passed, (
        f"AI-A-004: 期待キーワード {expected_keywords} のいずれも推薦理由に含まれていません。\n"
        f"--- 推薦理由 ---\n{reasons_text}"
    )
