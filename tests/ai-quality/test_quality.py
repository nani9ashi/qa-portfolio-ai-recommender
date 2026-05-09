"""
品質テスト (AI-Q-001〜003)

対応観点: V-15 (推薦理由の品質)
対応AC: AC外
判定方法 (Phase 1): ルールベース (文字数・キーワード言及・文末形態)

合格基準は「90%以上」(設計書 4.4 より)。
GT-001〜005 を一通り回した結果を集計して率を算出する。

集計式 (AI-Q-003):
    統一率 = (文体統一OKの推薦理由数) / (評価対象の推薦理由数)
    合格基準: 統一率 >= 90%
"""

import pytest

from tests.ai_quality.fixtures.unit_master import find_unit_by_id
from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.assertions import (
    contains_keyword,
    is_consistent_style,
    is_within_char_range,
)


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


def test_AI_Q_001_char_count_within_range(recorder, all_recommendations):
    """
    AI-Q-001: 推薦理由の文字数

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    判定方法: 推薦理由の文字数を集計
    合格基準: 50〜150 字の範囲内が 90% 以上

    集計式:
        合格率 = (文字数50〜150字の推薦理由数) / (全推薦理由数)
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
            "total": total,
            "in_range": in_range,
            "out_of_range": total - in_range,
            "pass_rate": rate,
            "threshold": PASS_RATE_THRESHOLD,
            "out_of_range_examples": out_examples[:5],
        },
    )
    assert passed, (
        f"AI-Q-001: 文字数範囲内率 {rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"範囲外例: {out_examples[:3]}"
    )


def test_AI_Q_002_mention_rate_for_input_units(recorder, all_recommendations):
    """
    AI-Q-002: 推薦理由の品質 (入力単元への言及率)

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    判定方法: 推薦理由に「学年」「苦手単元名」「理解済み単元名」のいずれかが含まれるか
    合格基準: 言及率 90% 以上

    集計式:
        合格率 = (いずれかへの言及がある推薦理由数) / (全推薦理由数)
    """
    total = len(all_recommendations)
    has_mention = 0
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
        if any(contains_keyword(text, c) for c in candidates):
            has_mention += 1
        else:
            no_mention_examples.append({
                "gt_id": entry["gt_id"],
                "unitId": entry["rec"].get("unitId"),
                "candidates_checked": candidates,
            })

    rate = (has_mention / total) if total else 0.0
    passed = rate >= PASS_RATE_THRESHOLD

    recorder.record(
        test_id="AI-Q-002",
        category="quality",
        passed=passed,
        metrics={
            "total": total,
            "has_mention": has_mention,
            "no_mention": total - has_mention,
            "pass_rate": rate,
            "threshold": PASS_RATE_THRESHOLD,
            "no_mention_examples": no_mention_examples[:5],
        },
    )
    assert passed, (
        f"AI-Q-002: 入力単元言及率 {rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"未言及例: {no_mention_examples[:3]}"
    )


def test_AI_Q_003_consistent_writing_style(recorder, all_recommendations):
    """
    AI-Q-003: 推薦理由の品質 (文体統一)

    対応AC: AC外
    観点: V-15: 推薦理由の品質
    判定方法: 各推薦理由の文末が「である調」or「ですます調」で統一されているか
    合格基準: 統一率 90% 以上

    集計式:
        統一率 = (文体統一OKの推薦理由数) / (評価対象の推薦理由数)

    判定基準 (helpers/assertions.is_consistent_style):
    - 全文末が「である調」(〜だ、〜である、〜ない 等) または
      「ですます調」(〜です、〜ます、〜ません 等) のいずれかで統一されている
    - 体言止め・名詞句で終わる文は判定対象外
    - 1文しかない場合は「統一されている」と判定 (A2 採用)
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
            "total": total,
            "consistent": consistent,
            "inconsistent": total - consistent,
            "pass_rate": rate,
            "threshold": PASS_RATE_THRESHOLD,
            "inconsistent_examples": inconsistent_examples[:5],
        },
    )
    assert passed, (
        f"AI-Q-003: 文体統一率 {rate:.2%} (閾値 {PASS_RATE_THRESHOLD:.0%} 以上)\n"
        f"非統一例: {inconsistent_examples[:3]}"
    )
