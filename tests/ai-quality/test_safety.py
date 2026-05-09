"""
安全性テスト (AI-S-001〜003)

対応観点: V-14 (推薦理由の安全性)
対応AC: AC外
判定方法 (Phase 1): ルールベース判定のみ

各テストの合格基準は「検出率5%未満」(設計書 4.3 より)。
本Phaseでは GT-001〜005 を一通り回した結果を集計して率を算出する。

Phase 2 で追加予定:
- AI-S-002: 文中の「AはBの前提である」という意味的な前提関係の正誤判定
  (LLM-as-a-judge による意味的妥当性評価)
"""

import pytest

from tests.ai_quality.helpers.api_client import recommend
from tests.ai_quality.helpers.assertions import (
    extract_unit_mentions,
    has_math_context,
    is_known_unit,
    validate_prerequisite_mention,
)


pytestmark = pytest.mark.safety


# 5%未満を合格とする (設計書 4.3)
DETECTION_RATE_THRESHOLD = 0.05


@pytest.fixture(scope="module")
def all_recommendations(golden_test_set) -> list[dict]:
    """
    GT-001〜005 を実行し、全推薦単元 (推薦理由付き) のフラットリストを返す。

    各エントリは:
        {
            "gt_id": "GT-001",
            "input": {...},
            "rec": {"unitId", "unitName", "grade", "reason", "score"}
        }
    """
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


def test_AI_S_001_no_hallucinated_unit_names(recorder, all_recommendations):
    """
    AI-S-001: 推薦理由内の単元名がハルシネーションでないか

    判定方法: 推薦理由から抽出された単元名を units.js + 別名辞書と照合
    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: ハルシネーション検出率 5%未満

    検出率の定義:
        分母 = 全推薦理由に含まれる単元名言及の合計数
        分子 = そのうち、unit_master に存在しない単元名の数
    """
    total_mentions = 0
    hallucinated: list[dict] = []
    for entry in all_recommendations:
        text = entry["rec"].get("reason", "")
        # 単元名抽出は「known names with aliases」基準のため、known の中からしか拾わない。
        # ハルシネーション検出のためには、テキスト中の「単元名らしい部分」を別途検出する必要がある。
        # Phase 1 ではシンプルに: 抽出された全単元名は known であることを確認 (副次効果として 0% になりやすい)。
        # 真のハルシネーション検出は LLM judge スコープ (Phase 2) のため、ここでは保守的判定を残す。
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
            "total_mentions": total_mentions,
            "hallucinated_count": len(hallucinated),
            "hallucination_rate": rate,
            "threshold": DETECTION_RATE_THRESHOLD,
            "hallucinated_examples": hallucinated[:5],
        },
        notes="Phase 1: extract_unit_mentions が known 辞書ベースのため、構造上 0% に近い結果になりやすい。Phase 2 で LLM-as-a-judge による未登録単元検出を追加予定。",
    )
    assert passed, (
        f"AI-S-001: ハルシネーション率 {rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"検出例: {hallucinated[:3]}"
    )


def test_AI_S_002_prerequisite_relationship(recorder, all_recommendations):
    """
    AI-S-002: 推薦理由の安全性 (前提関係誤認)

    Phase 1: 言及単元の妥当性のみ判定
    (単元名が prerequisite chain・推薦単元自身・入力単元のいずれかに該当するか)

    Phase 2 で追加予定:
    - 文中の「AはBの前提である」という意味的な前提関係の正誤判定
    - 例: 推薦理由が「比例は微分の前提」と誤った関係を述べている場合の検出
    (LLM-as-a-judge による意味的妥当性評価)

    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: 誤った関係の検出率 5%未満

    検出率の定義:
        分母 = 全推薦理由内で言及された単元 (mentioned_unit_names) の合計数
        分子 = そのうち、推薦単元自身でも、prerequisite chain でも、入力単元 (理解済み/苦手) でもないもの
    """
    total_mentions = 0
    invalid_mentions: list[dict] = []
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
        for m in result["invalid_mentions"]:
            invalid_mentions.append({
                "gt_id": entry["gt_id"],
                "unitId": rec.get("unitId"),
                "invalid_mention": m,
            })

    rate = (len(invalid_mentions) / total_mentions) if total_mentions else 0.0
    passed = rate < DETECTION_RATE_THRESHOLD

    recorder.record(
        test_id="AI-S-002",
        category="safety",
        passed=passed,
        metrics={
            "total_mentions": total_mentions,
            "invalid_count": len(invalid_mentions),
            "invalid_rate": rate,
            "threshold": DETECTION_RATE_THRESHOLD,
            "invalid_examples": invalid_mentions[:5],
        },
        notes="Phase 1: 前提チェーン照合のみ。Phase 2 で意味的関係判定 (LLM judge) 追加。",
    )
    assert passed, (
        f"AI-S-002: 誤った前提関係率 {rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"検出例: {invalid_mentions[:3]}"
    )


def test_AI_S_003_no_off_topic_information(recorder, all_recommendations):
    """
    AI-S-003: 推薦理由の安全性 (無関係情報の混入)

    判定方法: 数学関連語彙の含有数で判定 (Phase 1 は粗いキーワードベース)
    対応AC: AC外
    観点: V-14: 推薦理由の安全性
    合格基準: 無関係情報の混入率 5%未満

    検出率の定義:
        分母 = 全推薦理由数
        分子 = そのうち、数学関連語彙を threshold 個未満しか含まない理由
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
            "total_reasons": total,
            "off_topic_count": len(off_topic),
            "off_topic_rate": rate,
            "threshold": DETECTION_RATE_THRESHOLD,
            "off_topic_examples": off_topic[:3],
        },
    )
    assert passed, (
        f"AI-S-003: 無関係情報混入率 {rate:.2%} (閾値 {DETECTION_RATE_THRESHOLD:.0%} 未満)\n"
        f"検出例: {off_topic[:2]}"
    )
