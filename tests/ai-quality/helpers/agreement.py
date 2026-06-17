"""
判定一致率 (agreement rate) 算出スクリプト。

「judge (測定器) の判定が、人手で独立に定めた正解 (ground truth) とどれだけ一致するか」を計測する。
これは合格率 (pass rate) とは別指標である:

  - 合格率       : judge が「合格」と返した割合。判定を甘くするだけでも上がりうる。
  - 判定一致率   : judge の判定が人手正解 (GT) と一致した割合。測定器が「正しく」なったことを示す。

【設計: judge を測る (SUT を測るのではない) → 判定対象を凍結する】
judge は測定器であり、測定器の正しさは「固定された人手ラベル付き基準集合」に対する正解率で測る。
SUT (Claude Haiku) の出力は毎回揺らぐため、基準実行時点で judge が実際に見た出力を凍結コーパス
(judge_eval_set.json) として固定し、GT をそれに紐づける。これにより人手ラベルは恒久化し、判定一致率は
再実行で同じ表が出る (judge を改良したら同じコーパスに当て直して再計測できる)。
SUT の毎回の揺れ自体は別軸 (一貫性テスト AI-C-*) が担当し、本指標には混ぜない。

【Phase の定義】
  - Phase 1 verdict : ルールベースのみの最終判定。
  - Phase 2 verdict : ルールベース + 選択的 LLM-as-a-judge の最終判定 (summary.json の results[i].passed)。

【一致率】 = (verdict == GT のケース数) / 13。全体とカテゴリ別を出す。

--------------------------------------------------------------------------------
2 モード:

  1) 凍結 (一度きり)。results/ は .gitignore 対象なので、基準実行の判定対象を固定ファイルに凍結する:
       python tests/ai-quality/helpers/agreement.py --extract \
           tests/ai-quality/results/2026-05-09_12-06-15/summary.json
     → fixtures/judge_eval_set.json を生成 (コミット対象)。

  2) 算出 (引数なし)。凍結コーパス + 人手 GT を突合し一致率を出す:
       python tests/ai-quality/helpers/agreement.py
     → agreement/agreement_matrix.{csv,json} を出力し、サマリを標準出力。
       fixtures/ground_truth_verdicts.json (人手 GT) が必要。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

_AIQ_ROOT = Path(__file__).resolve().parents[1]          # tests/ai-quality
_FIXTURES = _AIQ_ROOT / "fixtures"
_JUDGE_EVAL_SET = _FIXTURES / "judge_eval_set.json"
_GROUND_TRUTH = _FIXTURES / "ground_truth_verdicts.json"
_AGREEMENT_DIR = _AIQ_ROOT / "agreement"

_CATEGORY_ORDER = ["accuracy", "consistency", "safety", "quality"]


# ---------------------------------------------------------------------------
# Phase 1 verdict の導出 (2 通りで導いてクロスチェックする)
# ---------------------------------------------------------------------------

def _phase1_from_rule(case_id: str, rb: dict[str, Any]) -> str:
    """rule_based メトリクスから、ルール単独 (Phase 1) の判定を再現する。

    各テストが Phase 1 で適用していた合否ゲートをそのまま使う。閾値もメトリクス側に
    記録されている値を用い、ハードコードしない。
    """
    if case_id.startswith("AI-A-"):                      # 正確性: キーワード照合
        return "PASS" if rb["rule_passed"] else "FAIL"
    if case_id == "AI-C-001":                            # 一貫性: 推薦単元集合
        return "PASS" if rb["n_unique_unit_sets"] == 1 else "FAIL"
    if case_id == "AI-C-002":                            # 一貫性: 文字数範囲
        return "PASS" if rb["out_of_range_count"] == 0 else "FAIL"
    if case_id == "AI-C-003":                            # 一貫性: 言及単元集合
        return "PASS" if rb["rule_passed"] else "FAIL"
    if case_id == "AI-S-001":                            # 安全性: ハルシネーション率
        return "PASS" if rb["hallucination_rate"] <= rb["threshold"] else "FAIL"
    if case_id == "AI-S-002":                            # 安全性: 前提関係 (フラグ0件で合格)
        return "PASS" if rb["rule_invalid_count"] == 0 else "FAIL"
    if case_id == "AI-S-003":                            # 安全性: 無関係情報率
        return "PASS" if rb["off_topic_rate"] <= rb["threshold"] else "FAIL"
    if case_id == "AI-Q-001":                            # 品質: 文字数適合率
        return "PASS" if rb["pass_rate"] >= rb["threshold"] else "FAIL"
    if case_id == "AI-Q-002":                            # 品質: 入力言及率
        return "PASS" if rb["rule_pass_rate"] >= rb["threshold"] else "FAIL"
    if case_id == "AI-Q-003":                            # 品質: 文体統一率
        return "PASS" if rb["pass_rate"] >= rb["threshold"] else "FAIL"
    raise SystemExit(f"[FATAL] 未知の case_id: {case_id}")


def _phase1_from_judgment(final_judgment: str, phase2: str) -> str:
    """final_judgment 文字列 (判定経路) から Phase 1 判定を導く。クロスチェック用。"""
    fj = final_judgment
    if fj.startswith("rule alone"):
        return "PASS" if "(passed" in fj else "FAIL"
    if fj.startswith("rule + llm agreed"):
        return "PASS" if "(passed" in fj else "FAIL"
    if fj.startswith("rule passed but llm rejected"):
        return "PASS"                                    # ルールは合格、LLM が格下げ
    if fj.startswith("rule + llm rescued"):
        return "FAIL"                                    # ルールは不合格、LLM が格上げ
    if fj.startswith("rule + llm fallback"):
        return phase2                                    # LLM 不調、ルール判定を採用
    raise SystemExit(f"[FATAL] 未知の final_judgment パターン: {final_judgment!r}")


# ---------------------------------------------------------------------------
# 凍結 (--extract)
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _frozen_output(case_id: str, metrics: dict[str, Any], traces_dir: Path) -> dict[str, Any]:
    """そのケースで judge が実際に見た判定対象を凍結する。

    - LLM judge を使ったケース: トレースから target_text (生テキスト) を凍結。
    - ルール専用ケース: 基準実行で生テキストが永続化されていないため、ルール集計値を凍結。
    """
    llm = metrics.get("llm_judge")
    trace_path = traces_dir / f"{case_id}.jsonl"

    if llm is not None and trace_path.exists():
        items = []
        for ln in _read_jsonl(trace_path):
            items.append({
                "gt_id": ln.get("gt_id", ""),
                "criteria": ln.get("criteria", {}),
                "target_text": ln.get("target_text", ""),
                "llm_score": ln.get("parsed_score"),
                "llm_passed": ln.get("passed"),
            })
        return {
            "input": items[0]["criteria"] if items else {},
            "output": {
                "type": "text",
                "source_trace": f"llm_judge_traces/{case_id}.jsonl",
                "evaluated_items": items,
            },
        }

    # ルール専用ケース (生テキストは基準実行に残っていない → 集計値を凍結)
    return {
        "input": {"note": "ゴールデンセット GT-001〜005 の推薦理由を入力とした集計 (ルール専用ケース)"},
        "output": {
            "type": "metrics",
            "note": "基準実行で生テキストは永続化されていないため、ルール集計値を凍結素材とする",
            "rule_based": metrics.get("rule_based", {}),
        },
    }


def extract(summary_path: Path) -> None:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    run_dir = summary_path.resolve().parent
    traces_dir = run_dir / "llm_judge_traces"
    source_run = run_dir.name

    cases: list[dict[str, Any]] = []
    for r in data["results"]:
        case_id = r["test_id"]
        metrics = r.get("metrics", {}) or {}
        rb = metrics.get("rule_based", {})
        final_judgment = metrics.get("final_judgment", "")
        phase2 = "PASS" if r["passed"] else "FAIL"

        p1_rule = _phase1_from_rule(case_id, rb)
        p1_judg = _phase1_from_judgment(final_judgment, phase2)
        if p1_rule != p1_judg:
            raise SystemExit(
                f"[FATAL] {case_id}: Phase1 導出が不一致 "
                f"(rule_based={p1_rule} / final_judgment={p1_judg})"
            )

        frozen = _frozen_output(case_id, metrics, traces_dir)
        cases.append({
            "case_id": case_id,
            "category": r["category"],
            "phase1_verdict": p1_rule,
            "phase2_verdict": phase2,
            "final_judgment": final_judgment,
            "input": frozen["input"],
            "frozen_output": frozen["output"],
            "rule_based_metrics": rb,
            "source_run": source_run,
        })

    payload = {
        "_about": (
            "judge 評価用に凍結した判定対象コーパス (judge が実際に見た SUT 出力)。"
            "判定一致率の計測でこれを固定し、人手 GT を紐づける。SUT の毎回の揺れは含めない。"
        ),
        "source_run": source_run,
        "n": len(cases),
        "cases": cases,
    }
    _JUDGE_EVAL_SET.parent.mkdir(parents=True, exist_ok=True)
    _JUDGE_EVAL_SET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 凍結コーパスを生成: {_JUDGE_EVAL_SET}  (n={len(cases)}, source_run={source_run})")


# ---------------------------------------------------------------------------
# 算出 (引数なし)
# ---------------------------------------------------------------------------

def _load_ground_truth() -> dict[str, str]:
    if not _GROUND_TRUTH.exists():
        raise SystemExit(
            f"[FATAL] 人手 GT が見つかりません: {_GROUND_TRUTH}\n"
            "        13ケースの人手正解 (PASS/FAIL + 根拠) を記録してから再実行してください。"
        )
    gt_list = json.loads(_GROUND_TRUTH.read_text(encoding="utf-8"))
    gt: dict[str, str] = {}
    for g in gt_list:
        verdict = str(g["gt_verdict"]).upper()
        if verdict not in ("PASS", "FAIL"):
            raise SystemExit(f"[FATAL] {g.get('case_id')}: gt_verdict は PASS/FAIL のみ ({verdict!r})")
        gt[g["case_id"]] = verdict
    return gt


def _rate(num: int, den: int) -> str:
    pct = (num / den * 100) if den else 0.0
    return f"{pct:.2f}% ({num}/{den})"


def compute() -> None:
    if not _JUDGE_EVAL_SET.exists():
        raise SystemExit(
            f"[FATAL] 凍結コーパスが見つかりません: {_JUDGE_EVAL_SET}\n"
            "        先に --extract で凍結してください。"
        )
    eval_set = json.loads(_JUDGE_EVAL_SET.read_text(encoding="utf-8"))
    gt = _load_ground_truth()

    rows: list[dict[str, Any]] = []
    for c in eval_set["cases"]:
        cid = c["case_id"]
        if cid not in gt:
            raise SystemExit(f"[FATAL] GT に {cid} の正解がありません")
        g = gt[cid]
        p1, p2 = c["phase1_verdict"], c["phase2_verdict"]
        rows.append({
            "case_id": cid,
            "category": c["category"],
            "gt": g,
            "phase1_verdict": p1,
            "phase2_verdict": p2,
            "phase1_match": p1 == g,
            "phase2_match": p2 == g,
        })

    n = len(rows)
    p1_match = sum(1 for r in rows if r["phase1_match"])
    p2_match = sum(1 for r in rows if r["phase2_match"])

    by_cat: dict[str, dict[str, int]] = {}
    for r in rows:
        cat = by_cat.setdefault(r["category"], {"total": 0, "p1": 0, "p2": 0})
        cat["total"] += 1
        cat["p1"] += int(r["phase1_match"])
        cat["p2"] += int(r["phase2_match"])

    summary = {
        "n": n,
        "source_run": eval_set.get("source_run"),
        "phase1_agreement": {"match": p1_match, "total": n, "rate": p1_match / n if n else 0.0},
        "phase2_agreement": {"match": p2_match, "total": n, "rate": p2_match / n if n else 0.0},
        "by_category": {
            cat: {
                "total": by_cat[cat]["total"],
                "phase1_match": by_cat[cat]["p1"],
                "phase2_match": by_cat[cat]["p2"],
            }
            for cat in sorted(by_cat, key=lambda c: _CATEGORY_ORDER.index(c) if c in _CATEGORY_ORDER else 99)
        },
        "phase1_disagreements": [r["case_id"] for r in rows if not r["phase1_match"]],
        "phase2_disagreements": [r["case_id"] for r in rows if not r["phase2_match"]],
    }

    _write_csv(rows)
    _write_json(rows, summary)
    _print_summary(rows, summary)


def _write_csv(rows: list[dict[str, Any]]) -> None:
    _AGREEMENT_DIR.mkdir(parents=True, exist_ok=True)
    path = _AGREEMENT_DIR / "agreement_matrix.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "category", "gt", "phase1_verdict",
                         "phase2_verdict", "phase1_match", "phase2_match"])
        for r in rows:
            writer.writerow([r["case_id"], r["category"], r["gt"],
                             r["phase1_verdict"], r["phase2_verdict"],
                             r["phase1_match"], r["phase2_match"]])


def _write_json(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    _AGREEMENT_DIR.mkdir(parents=True, exist_ok=True)
    path = _AGREEMENT_DIR / "agreement_matrix.json"
    path.write_text(
        json.dumps({"summary": summary, "matrix": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _print_summary(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    n = summary["n"]
    print("=" * 64)
    print(f"判定一致率 (人手正解との一致)   n={n}   source_run={summary['source_run']}")
    print("=" * 64)
    print(f"  Phase 1 (ルールベースのみ)         : {_rate(summary['phase1_agreement']['match'], n)}")
    print(f"  Phase 2 (ルール + 選択的 LLM judge): {_rate(summary['phase2_agreement']['match'], n)}")
    print("-" * 64)
    print("  カテゴリ別:")
    for cat, v in summary["by_category"].items():
        print(f"    {cat:<12} P1 {_rate(v['phase1_match'], v['total'])}   "
              f"P2 {_rate(v['phase2_match'], v['total'])}")
    print("-" * 64)
    if summary["phase1_disagreements"]:
        print(f"  Phase 1 で GT と不一致: {', '.join(summary['phase1_disagreements'])}")
    if summary["phase2_disagreements"]:
        print(f"  Phase 2 で GT と不一致: {', '.join(summary['phase2_disagreements'])}")
    print("-" * 64)
    print(f"  {'case_id':<10} {'cat':<12} {'GT':<5} {'P1':<5} {'P2':<5} P1=GT  P2=GT")
    for r in rows:
        print(f"  {r['case_id']:<10} {r['category']:<12} {r['gt']:<5} "
              f"{r['phase1_verdict']:<5} {r['phase2_verdict']:<5} "
              f"{'  Y' if r['phase1_match'] else '  -'}    {'  Y' if r['phase2_match'] else '  -'}")
    print("=" * 64)
    print(f"  出力: {_AGREEMENT_DIR / 'agreement_matrix.csv'}")
    print(f"        {_AGREEMENT_DIR / 'agreement_matrix.json'}")


# ---------------------------------------------------------------------------

def main() -> None:
    # Windows コンソール (cp932) 等での文字化け・クラッシュを避けるため、可能なら UTF-8 に切り替える
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="判定一致率 (人手正解との一致) の凍結・算出")
    parser.add_argument(
        "--extract", metavar="SUMMARY_JSON",
        help="基準実行の summary.json から判定対象を凍結し judge_eval_set.json を生成する",
    )
    args = parser.parse_args()

    if args.extract:
        summary_path = Path(args.extract)
        if not summary_path.exists():
            raise SystemExit(f"[FATAL] summary.json が見つかりません: {summary_path}")
        extract(summary_path)
    else:
        compute()


if __name__ == "__main__":
    main()
