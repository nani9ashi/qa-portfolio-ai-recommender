"""
pytest 共通設定 / フィクスチャ。

責務:
- .env から BACKEND_URL 等の設定を読み込む
- セッション開始時にバックエンドのヘルスチェック (失敗時は全テスト fail)
- ゴールデンテストセットの読み込み
- 結果出力 (Reporter) のセッションスコープ管理
"""

import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import pytest
from dotenv import load_dotenv

# tests/ai-quality をモジュールルートに追加 (helpers / fixtures 配下を import 可能にする)
_AI_QUALITY_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AI_QUALITY_ROOT.parent.parent))  # リポジトリルート


def _register_ai_quality_package() -> None:
    """tests.ai_quality.* で fixtures / helpers を import 可能にする (ハイフン名対策)"""
    pkg_root = _AI_QUALITY_ROOT
    spec = importlib.machinery.ModuleSpec("tests.ai_quality", loader=None, is_package=True)
    spec.submodule_search_locations = [str(pkg_root)]
    module = importlib.util.module_from_spec(spec)
    module.__path__ = [str(pkg_root)]
    sys.modules["tests.ai_quality"] = module

    if "tests" not in sys.modules:
        tests_root = pkg_root.parent
        tests_spec = importlib.machinery.ModuleSpec("tests", loader=None, is_package=True)
        tests_spec.submodule_search_locations = [str(tests_root)]
        tests_module = importlib.util.module_from_spec(tests_spec)
        tests_module.__path__ = [str(tests_root)]
        sys.modules["tests"] = tests_module


_register_ai_quality_package()

# .env 読み込み (tests/ai-quality/.env を最優先)
load_dotenv(_AI_QUALITY_ROOT / ".env")

from tests.ai_quality.helpers.api_client import health_check  # noqa: E402
from tests.ai_quality.helpers.reporters import ResultRecorder, make_run_dir  # noqa: E402


# ===== グローバル recorder (sessionfinish フックから出力するため) =====

_RECORDER_HOLDER: dict[str, Optional[ResultRecorder]] = {"recorder": None}


# ===== セッションスコープのフィクスチャ =====

@pytest.fixture(scope="session", autouse=True)
def _ensure_backend_running():
    """全テスト開始前にバックエンドのヘルスチェックを実施する"""
    if not health_check():
        pytest.exit(
            "\n[FATAL] バックエンドが起動していません。\n"
            "  対処: `npm run start:backend` でバックエンドを起動してから pytest を実行してください。\n"
            f"  接続先: {os.environ.get('BACKEND_URL', 'http://localhost:3001')}\n"
            "  ヘルスチェック: GET /health に成功する必要があります。",
            returncode=2,
        )


@pytest.fixture(scope="session")
def golden_test_set() -> list[dict[str, Any]]:
    """ゴールデンテストセットの読み込み"""
    path = _AI_QUALITY_ROOT / "fixtures" / "golden_test_set.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def golden_by_id(golden_test_set) -> dict[str, dict[str, Any]]:
    """GT-XXX 形式の ID で引けるようにした辞書"""
    return {gt["id"]: gt for gt in golden_test_set}


@pytest.fixture(scope="session")
def run_dir() -> Path:
    """このセッションの出力ディレクトリ"""
    return make_run_dir()


@pytest.fixture(scope="session")
def recorder(run_dir) -> ResultRecorder:
    """全テストで共有する ResultRecorder (sessionfinish で書き出す)"""
    rec = ResultRecorder(run_dir)
    _RECORDER_HOLDER["recorder"] = rec
    return rec


# ===== セッション終了時に集計を出力 =====

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """テスト終了時に Reporter を出力する (recorder fixture が使われた場合のみ)"""
    rec = _RECORDER_HOLDER.get("recorder")
    if rec is None or not rec.records:
        return
    try:
        summary_path = rec.write_summary()
        details_path = rec.write_details_csv()
        sys.stderr.write(f"\n[reporters] summary  : {summary_path}\n")
        sys.stderr.write(f"[reporters] details  : {details_path}\n")
    except Exception as e:
        sys.stderr.write(f"\n[reporters] 結果出力に失敗: {e}\n")


# ===== 環境変数アクセス用のヘルパー =====

def get_consistency_runs() -> int:
    """一貫性テストの実行回数 (デフォルト 10)"""
    return int(os.environ.get("CONSISTENCY_RUNS", "10"))


def get_consistency_sleep_sec() -> float:
    """一貫性テストの呼び出し間 sleep (秒、デフォルト 1.0)"""
    return float(os.environ.get("CONSISTENCY_SLEEP_SEC", "1.0"))
