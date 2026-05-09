"""
一貫性テスト (AI-C-001〜003)

対応観点: V-13 (推薦理由の一貫性)
対応AC: AC外
判定方法: 同一入力で N 回 (デフォルト 10) 連続呼び出し → 結果の一致を判定

実行時間が長いため pytest mark で `slow` を付与。
ローカル開発時に省略したい場合は `pytest -m "not slow"` で除外可能。
"""

import os

import pytest

from tests.ai_quality.conftest import get_consistency_runs, get_consistency_sleep_sec
from tests.ai_quality.helpers.api_client import recommend_n_times
from tests.ai_quality.helpers.assertions import (
    extract_unit_mentions,
    is_within_char_range,
)


pytestmark = [pytest.mark.consistency, pytest.mark.slow]


# AI-C-001〜003 で共通する入力 (中2、理解済み=[一次関数]、苦手=[連立方程式])
_INPUT_GRADE = "中2"
_INPUT_UNDERSTOOD = ["m2_ichijikansuu"]
_INPUT_WEAK = ["m2_renritsu"]


@pytest.fixture(scope="module")
def consistency_runs():
    """同一入力で N 回呼び出した結果を module スコープでキャッシュ"""
    n = get_consistency_runs()
    sleep_sec = get_consistency_sleep_sec()
    return recommend_n_times(_INPUT_GRADE, _INPUT_UNDERSTOOD, _INPUT_WEAK, n=n, sleep_sec=sleep_sec)


def test_AI_C_001_recommendation_units_identical(recorder, consistency_runs):
    """
    AI-C-001: 推薦単元リストの一貫性

    入力: 中2、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-13: 推薦理由の一貫性
    実行回数: 10回 (CONSISTENCY_RUNS で変更可)
    合格基準: 全回で推薦単元リスト (unitId の集合) が完全一致
    """
    sets = [
        tuple(sorted(r.get("unitId", "") for r in run["recommendations"]))
        for run in consistency_runs
    ]
    unique = set(sets)
    passed = len(unique) == 1

    recorder.record(
        test_id="AI-C-001",
        category="consistency",
        passed=passed,
        metrics={
            "n_runs": len(consistency_runs),
            "n_unique_unit_sets": len(unique),
            "unique_unit_sets": [list(s) for s in unique],
        },
    )
    assert passed, (
        f"AI-C-001: 推薦単元リストが {len(unique)} 通り出現。全回で完全一致が必要。\n"
        f"出現セット: {sorted(unique)}"
    )


def test_AI_C_002_reason_char_count_within_range(recorder, consistency_runs):
    """
    AI-C-002: 推薦理由の文字数の一貫性

    入力: 中2、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-13: 推薦理由の一貫性
    実行回数: 10回
    合格基準: 全回で文字数が 50〜150 字の範囲内 (100% in range)
    """
    out_of_range: list[dict] = []
    total_reasons = 0
    for run_idx, run in enumerate(consistency_runs):
        for r in run["recommendations"]:
            total_reasons += 1
            reason = r.get("reason", "")
            if not is_within_char_range(reason, 50, 150):
                out_of_range.append({
                    "run": run_idx,
                    "unitId": r.get("unitId"),
                    "char_count": len(reason),
                })
    passed = len(out_of_range) == 0

    recorder.record(
        test_id="AI-C-002",
        category="consistency",
        passed=passed,
        metrics={
            "total_reasons": total_reasons,
            "out_of_range_count": len(out_of_range),
            "out_of_range_examples": out_of_range[:5],
        },
    )
    assert passed, (
        f"AI-C-002: {len(out_of_range)}/{total_reasons} 件の推薦理由が 50〜150 字の範囲外。\n"
        f"例: {out_of_range[:3]}"
    )


def test_AI_C_003_mentioned_units_identical_across_runs(recorder, consistency_runs):
    """
    AI-C-003: 推薦理由内で言及される単元の一貫性

    入力: 中2、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-13: 推薦理由の一貫性
    実行回数: 10回
    合格基準: 全回で「言及される単元名の集合」(順序問わず) が一致

    注: 推薦理由内の文章表現は揺れるが、言及される単元は一貫している想定
    (例: 「比例」と書かれる回と「比例・反比例」と書かれる回があってよいが、
     unitMapping で同一単元として扱う)
    """
    from tests.ai_quality.fixtures.unit_master import UNIT_NAME_ALIASES

    def normalize(names: list[str]) -> set[str]:
        ids = set()
        for n in names:
            uid = UNIT_NAME_ALIASES.get(n)
            if uid:
                ids.add(uid)
        return ids

    mention_sets: list[frozenset[str]] = []
    for run in consistency_runs:
        all_text = "\n".join(r.get("reason", "") for r in run["recommendations"])
        mentions = extract_unit_mentions(all_text)
        mention_sets.append(frozenset(normalize(mentions)))

    unique = set(mention_sets)
    passed = len(unique) == 1

    recorder.record(
        test_id="AI-C-003",
        category="consistency",
        passed=passed,
        metrics={
            "n_runs": len(consistency_runs),
            "n_unique_mention_sets": len(unique),
            "unique_mention_sets": [sorted(s) for s in unique],
        },
    )
    assert passed, (
        f"AI-C-003: 言及単元集合が {len(unique)} 通り。全回で一致が必要。\n"
        f"出現セット: {[sorted(s) for s in unique]}"
    )
