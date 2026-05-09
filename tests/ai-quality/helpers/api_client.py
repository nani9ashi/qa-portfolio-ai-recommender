"""
バックエンド API 呼び出しヘルパー。

backend/routes/recommend.js (POST /api/recommend) を呼ぶ。
直接 Anthropic API は叩かない (バックエンド経由)。
"""

import os
import time
from typing import Optional

import requests


DEFAULT_BACKEND_URL = "http://localhost:3001"
DEFAULT_TIMEOUT_SEC = 30  # Claude API のレスポンスを含めて余裕を持つ


def _backend_url() -> str:
    """環境変数から BACKEND_URL を取得 (未設定ならデフォルト)"""
    return os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def health_check() -> bool:
    """
    バックエンドのヘルスチェック。
    backend/server.js の `GET /health` が { status: "ok", ... } を返す前提。
    """
    try:
        r = requests.get(f"{_backend_url()}/health", timeout=5)
        return r.ok and r.json().get("status") == "ok"
    except Exception:
        return False


def recommend(grade: str, understoodIds: list[str], weakIds: list[str]) -> dict:
    """
    POST /api/recommend を1回呼び出して結果を返す。

    Returns:
        dict: { "recommendations": [{"unitId", "unitName", "grade", "reason", "score"}, ...] }

    Raises:
        requests.HTTPError: バックエンドが 4xx/5xx を返した場合
        requests.RequestException: ネットワークエラー (リトライしない)
    """
    payload = {
        "grade": grade,
        "understoodIds": understoodIds,
        "weakIds": weakIds,
    }
    r = requests.post(
        f"{_backend_url()}/api/recommend",
        json=payload,
        timeout=DEFAULT_TIMEOUT_SEC,
    )
    r.raise_for_status()
    return r.json()


def recommend_n_times(
    grade: str,
    understoodIds: list[str],
    weakIds: list[str],
    n: int = 10,
    sleep_sec: float = 1.0,
) -> list[dict]:
    """
    AI-C-001〜003 用: 同一入力で n 回呼び出した結果を返す。

    レート制限対策で各呼び出し間に sleep_sec の待機を入れる。
    リトライは行わず、途中で失敗したらそこで例外を投げる
    (テスト計画書 8 のリスク方針: 自動リトライしない)。
    """
    results = []
    for i in range(n):
        results.append(recommend(grade, understoodIds, weakIds))
        if i < n - 1:
            time.sleep(sleep_sec)
    return results
