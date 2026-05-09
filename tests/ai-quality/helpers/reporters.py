"""
結果出力ヘルパー。

pytest 実行終了時にテスト結果を JSON / CSV / HTML で出力する。
出力先: tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/
"""

import csv
import json
import os
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


# 各テストから結果を蓄積する (conftest.py の fixture 経由で利用)
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
        """1つのテストの結果を蓄積する"""
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
            "results": self.records,
        }
        path = self.run_dir / "summary.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_details_csv(self) -> Path:
        """details.csv を出力 (各テストの結果を1行ずつ)"""
        path = self.run_dir / "details.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["test_id", "category", "passed", "metrics_json", "notes", "ts"])
            for r in self.records:
                writer.writerow([
                    r["test_id"],
                    r["category"],
                    r["passed"],
                    json.dumps(r["metrics"], ensure_ascii=False),
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


def latest_run_dir() -> Path | None:
    """直近のラン結果ディレクトリを返す (存在しなければ None)"""
    if not _RESULTS_BASE.exists():
        return None
    runs = sorted([p for p in _RESULTS_BASE.iterdir() if p.is_dir()], reverse=True)
    return runs[0] if runs else None
