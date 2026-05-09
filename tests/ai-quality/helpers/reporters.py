"""
結果出力ヘルパー。

Phase 1: pytest 実行終了時にテスト結果を JSON / CSV / HTML で出力する。
Phase 2: rule_based / llm_judge 両方の結果を metrics 内に併存させ、
         CSV にも LLM judge のスコア・理由を別カラムで出力する。

出力先: tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


_RESULTS_BASE = Path(__file__).resolve().parents[1] / "results"


def make_run_dir() -> Path:
    """このセッション用の出力ディレクトリを作成して返す"""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = _RESULTS_BASE / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class ResultRecorder:
    """テストごとの詳細メトリクスを蓄積し、最後にファイル出力する"""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.records: list[dict[str, Any]] = []

    def record(
        self,
        test_id: str,
        category: str,
        passed: bool,
        metrics: dict[str, Any] | None = None,
        notes: str = "",
    ) -> None:
        """
        1つのテストの結果を蓄積する。

        Phase 2 では metrics 内に以下のキーを併存させる:
          - "rule_based": Phase 1 のルールベース判定結果
          - "llm_judge":  Phase 2 の LLM-as-a-judge 結果 (使用したテストのみ)
          - "final_judgment": 判定経路を示す文字列
                             例: "rule alone (passed)", "rule + llm rescued (passed)"
        """
        self.records.append({
            "test_id": test_id,
            "category": category,
            "passed": passed,
            "metrics": metrics or {},
            "notes": notes,
            "ts": datetime.now().isoformat(timespec="seconds"),
        })

    def write_summary(self) -> Path:
        """summary.json を出力 (テスト ID 別の集計)"""
        total = len(self.records)
        passed = sum(1 for r in self.records if r["passed"])
        summary = {
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": (passed / total) if total else 0.0,
            "by_category": self._by_category(),
            "by_judgment_path": self._by_judgment_path(),
            "results": self.records,
        }
        path = self.run_dir / "summary.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_details_csv(self) -> Path:
        """details.csv を出力 (各テストの結果を1行ずつ、Phase 2 の LLM judge カラム付き)"""
        path = self.run_dir / "details.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "test_id",
                "category",
                "passed",
                "final_judgment",
                "rule_based_summary",
                "llm_judge_used",
                "llm_judge_score",
                "llm_judge_passed",
                "llm_judge_reasoning",
                "llm_judge_fallback",
                "metrics_json",
                "notes",
                "ts",
            ])
            for r in self.records:
                metrics = r.get("metrics", {}) or {}
                rule_based = metrics.get("rule_based", {})
                llm_judge = metrics.get("llm_judge")
                # llm_judge がリスト (複数判定) の場合は集計表示
                llm_used, llm_score, llm_passed, llm_reasoning, llm_fallback = _summarize_llm_judge(llm_judge)
                writer.writerow([
                    r["test_id"],
                    r["category"],
                    r["passed"],
                    metrics.get("final_judgment", ""),
                    json.dumps(rule_based, ensure_ascii=False) if rule_based else "",
                    llm_used,
                    llm_score,
                    llm_passed,
                    llm_reasoning,
                    llm_fallback,
                    json.dumps(metrics, ensure_ascii=False),
                    r["notes"],
                    r["ts"],
                ])
        return path

    def _by_category(self) -> dict[str, dict[str, int]]:
        cats: dict[str, dict[str, int]] = {}
        for r in self.records:
            c = r["category"]
            cats.setdefault(c, {"total": 0, "passed": 0})
            cats[c]["total"] += 1
            if r["passed"]:
                cats[c]["passed"] += 1
        return cats

    def _by_judgment_path(self) -> dict[str, int]:
        """final_judgment 文字列の出現数を集計 (Phase 2 の効果可視化)"""
        paths: dict[str, int] = {}
        for r in self.records:
            metrics = r.get("metrics", {}) or {}
            path_label = metrics.get("final_judgment", "(unknown)")
            paths[path_label] = paths.get(path_label, 0) + 1
        return paths


def _summarize_llm_judge(llm_judge: Any) -> tuple[str, str, str, str, str]:
    """
    metrics["llm_judge"] を CSV 用の文字列タプルに変換する。
    - 単一判定 (dict): そのまま展開
    - 複数判定 (list): 件数 + 平均スコア + 合格件数 / フォールバック件数 で要約
    - None: 全フィールド空
    """
    if llm_judge is None:
        return ("False", "", "", "", "")

    if isinstance(llm_judge, dict):
        return (
            "True",
            str(llm_judge.get("score", "")),
            str(llm_judge.get("passed", "")),
            llm_judge.get("reasoning", ""),
            str(llm_judge.get("fallback", "")),
        )

    if isinstance(llm_judge, list):
        n = len(llm_judge)
        if n == 0:
            return ("False", "", "", "", "")
        scores = [int(j.get("score", 0)) for j in llm_judge]
        passed_count = sum(1 for j in llm_judge if j.get("passed"))
        fallback_count = sum(1 for j in llm_judge if j.get("fallback"))
        avg = sum(scores) / n if n else 0
        return (
            f"True ({n}件)",
            f"avg={avg:.2f} (min={min(scores)}, max={max(scores)})",
            f"{passed_count}/{n}",
            "(individual reasonings in metrics_json)",
            f"{fallback_count}/{n}",
        )

    return ("True", str(llm_judge), "", "", "")


def latest_run_dir() -> Path | None:
    """直近のラン結果ディレクトリを返す (存在しなければ None)"""
    if not _RESULTS_BASE.exists():
        return None
    runs = sorted([p for p in _RESULTS_BASE.iterdir() if p.is_dir()], reverse=True)
    return runs[0] if runs else None
