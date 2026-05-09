"""
一貫性テスト (AI-C-001〜003)

対応観点: V-13 (推薦理由の一貫性)
対応AC: AC外
判定方法: 同一入力で N 回 (デフォルト 10) 連続呼び出し → 結果の一致を判定

判定方式:
- AI-C-001: ルールベースのみ (Phase 1、推薦単元リストの完全一致)
- AI-C-002: ルールベースのみ (Phase 1、文字数全件50〜150字内)
- AI-C-003: ルールベース + LLM-as-a-judge による「同趣旨型」判定 (Phase 2)

実行時間が長いため pytest mark で `slow` を付与。
"""

import pytest

from tests.ai_quality.conftest import get_consistency_runs, get_consistency_sleep_sec
from tests.ai_quality.fixtures.unit_master import UNIT_NAME_ALIASES, find_unit_by_id
from tests.ai_quality.helpers.api_client import recommend_n_times
from tests.ai_quality.helpers.assertions import (
    extract_unit_mentions,
    is_within_char_range,
)
from tests.ai_quality.helpers.llm_judge import judge_with_llm
from tests.ai_quality.helpers.llm_judge_prompts import CONSISTENCY_JUDGE_PROMPT


pytestmark = [pytest.mark.consistency, pytest.mark.slow]


# AI-C-001〜003 で共通する入力 (中2、理解済み=[一次関数]、苦手=[連立方程式])
_INPUT_GRADE = "中2"
_INPUT_UNDERSTOOD = ["m2_ichijikansuu"]
_INPUT_WEAK = ["m2_renritsu"]


def _format_units_for_prompt(unit_ids: list[str]) -> str:
    if not unit_ids:
        return "(なし)"
    parts = []
    for uid in unit_ids:
        u = find_unit_by_id(uid)
        if u:
            parts.append(f"「{u['name']}」")
    return "、".join(parts) if parts else "(なし)"


@pytest.fixture(scope="module")
def consistency_runs():
    """同一入力で N 回呼び出した結果を module スコープでキャッシュ"""
    n = get_consistency_runs()
    sleep_sec = get_consistency_sleep_sec()
    return recommend_n_times(_INPUT_GRADE, _INPUT_UNDERSTOOD, _INPUT_WEAK, n=n, sleep_sec=sleep_sec)


def test_AI_C_001_recommendation_units_identical(recorder, consistency_runs):
    """
    AI-C-001: 推薦単元リストの一貫性 (Phase 1 のみ)

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
            "rule_based": {
                "n_runs": len(consistency_runs),
                "n_unique_unit_sets": len(unique),
                "unique_unit_sets": [list(s) for s in unique],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-C-001: 推薦単元リストが {len(unique)} 通り出現。全回で完全一致が必要。\n"
        f"出現セット: {sorted(unique)}"
    )


def test_AI_C_002_reason_char_count_within_range(recorder, consistency_runs):
    """
    AI-C-002: 推薦理由の文字数の一貫性 (Phase 1 のみ)

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
            "rule_based": {
                "total_reasons": total_reasons,
                "out_of_range_count": len(out_of_range),
                "out_of_range_examples": out_of_range[:5],
            },
            "llm_judge": None,
            "final_judgment": "rule alone (passed)" if passed else "rule alone (failed)",
        },
        notes="Phase 1 のみ実装 (ルールベースで十分機能、Phase 2 対象外)",
    )
    assert passed, (
        f"AI-C-002: {len(out_of_range)}/{total_reasons} 件の推薦理由が 50〜150 字の範囲外。\n"
        f"例: {out_of_range[:3]}"
    )


def test_AI_C_003_mentioned_units_identical_across_runs(recorder, consistency_runs, llm_traces_dir):
    """
    AI-C-003: 推薦理由内で言及される単元の一貫性 — Phase 2 同趣旨型

    Phase 1: 全10ランで「言及単元の集合 (unitId 正規化後)」が完全一致
    Phase 2: 集合不一致でも、LLM judge で「全回が同じ趣旨か」を判定し、
            妥当 (score >= 3) と判断されれば最終合格に格上げ

    入力: 中2、理解済み=[一次関数]、苦手=[連立方程式]
    対応AC: AC外
    観点: V-13: 推薦理由の一貫性
    実行回数: 10回
    """
    def normalize(names: list[str]) -> set[str]:
        ids = set()
        for n in names:
            uid = UNIT_NAME_ALIASES.get(n)
            if uid:
                ids.add(uid)
        return ids

    mention_sets: list[frozenset[str]] = []
    all_runs_text_parts = []
    for run_idx, run in enumerate(consistency_runs):
        all_text = "\n".join(r.get("reason", "") for r in run["recommendations"])
        mentions = extract_unit_mentions(all_text)
        mention_sets.append(frozenset(normalize(mentions)))
        all_runs_text_parts.append(f"--- Run {run_idx + 1} ---\n{all_text}")

    unique = set(mention_sets)
    rule_passed = len(unique) == 1

    rule_based = {
        "n_runs": len(consistency_runs),
        "n_unique_mention_sets": len(unique),
        "unique_mention_sets": [sorted(s) for s in unique],
        "rule_passed": rule_passed,
    }

    # ===== Phase 1 合格 → そのまま合格 =====
    if rule_passed:
        recorder.record(
            test_id="AI-C-003",
            category="consistency",
            passed=True,
            metrics={
                "rule_based": rule_based,
                "llm_judge": None,
                "final_judgment": "rule alone (passed: identical mention sets)",
            },
        )
        return

    # ===== Phase 2: LLM judge で「同じ趣旨か」を1回で判定 =====
    all_runs_text = "\n\n".join(all_runs_text_parts)
    llm = judge_with_llm(
        prompt_template=CONSISTENCY_JUDGE_PROMPT,
        variables={
            "grade": _INPUT_GRADE,
            "understood": _format_units_for_prompt(_INPUT_UNDERSTOOD),
            "weak": _format_units_for_prompt(_INPUT_WEAK),
            "all_runs_text": all_runs_text,
            "n_unique_sets": len(unique),
        },
        test_id="AI-C-003",
        gt_id="(consistency-runs)",
        traces_dir=llm_traces_dir,
    )

    if llm["fallback"]:
        # フォールバック: ルールベース結果を採用 (= 不合格)
        final_passed = False
        final_judgment = "rule + llm fallback (failed via rule, llm unavailable)"
    elif llm["passed"]:
        final_passed = True
        final_judgment = f"rule + llm rescued (passed: same intent across {len(consistency_runs)} runs despite set diff)"
    else:
        final_passed = False
        final_judgment = "rule + llm agreed (failed: not same intent)"

    recorder.record(
        test_id="AI-C-003",
        category="consistency",
        passed=final_passed,
        metrics={
            "rule_based": rule_based,
            "llm_judge": llm,
            "final_judgment": final_judgment,
        },
    )
    assert final_passed, (
        f"AI-C-003: 言及単元集合が {len(unique)} 通り、LLM judge も同趣旨と判定せず (score={llm['score']})\n"
        f"理由: {llm['reasoning']}"
    )
