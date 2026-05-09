# AI 出力品質テスト (Phase 1)

`docs/test-design.md` セクション4 で定義された AI 出力品質テスト 13ケースを Python + pytest で実装。

| ファイル | 対応テスト | 件数 |
|---|---|---|
| [test_accuracy.py](./test_accuracy.py) | AI-A-001〜004 (正確性) | 4 |
| [test_consistency.py](./test_consistency.py) | AI-C-001〜003 (一貫性、各10回連続呼び出し) | 3 |
| [test_safety.py](./test_safety.py) | AI-S-001〜003 (安全性、ハルシネーション/前提関係/無関係情報) | 3 |
| [test_quality.py](./test_quality.py) | AI-Q-001〜003 (品質、文字数/言及/文体) | 3 |

## Phase 1 のスコープ

- ルールベース判定のみ実装
- ゴールデンテストセット ([fixtures/golden_test_set.json](./fixtures/golden_test_set.json)) GT-001〜005 を入力として実行
- 各テストの結果を JSON / CSV / pytest-html で出力

**Phase 2 (LLM-as-a-judge) で追加予定:**
- AI-A-* の意味的判定強化
- AI-S-002 の前提関係の意味的妥当性判定

## 前提条件

- Python 3.11+
- バックエンドが port 3001 で起動していること (`npm run start:backend`)
- バックエンドの `backend/.env` に有効な `ANTHROPIC_API_KEY` が設定されていること

## ローカル実行

### 1. Python 仮想環境作成 (初回のみ)

```bash
# プロジェクトルートで
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate
```

### 2. 依存パッケージインストール (初回のみ)

```bash
pip install -r tests/ai-quality/requirements.txt
```

### 3. テスト用 .env 作成 (初回のみ)

```bash
cp tests/ai-quality/.env.example tests/ai-quality/.env
```

デフォルト設定 (BACKEND_URL=http://localhost:3001) で問題なければ編集不要です。

### 4. バックエンド起動

別ターミナルで:

```bash
npm run start:backend
```

起動メッセージ `[backend] Listening on http://localhost:3001` を確認。

### 5. pytest 実行

```bash
# 全テスト実行 (約2〜3分: 一貫性テストの 10×3 回呼び出しで時間がかかる)
pytest tests/ai-quality

# 一貫性テストを除外 (高速、1分程度)
pytest tests/ai-quality -m "not slow"

# 特定カテゴリのみ実行
pytest tests/ai-quality -m accuracy   # AI-A-* のみ
pytest tests/ai-quality -m safety     # AI-S-* のみ
pytest tests/ai-quality -m quality    # AI-Q-* のみ

# 特定テストID で実行
pytest tests/ai-quality -k "AI_A_001"

# HTML レポート出力 (要 pytest-html)
pytest tests/ai-quality --html=tests/ai-quality/results/last-run.html --self-contained-html
```

## 結果の確認

実行後、以下のディレクトリに結果が出力されます:

```
tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/
├── summary.json   # 全テストの合格率・カテゴリ別集計
└── details.csv    # 各テストの詳細メトリクス (Excel等で開ける)
```

### `summary.json` の主要フィールド

```jsonc
{
  "run_at": "2026-05-08T19:00:00",
  "total": 13,
  "passed": 11,
  "failed": 2,
  "pass_rate": 0.846,
  "by_category": {
    "accuracy":    { "total": 4, "passed": 4 },
    "consistency": { "total": 3, "passed": 2 },
    "safety":      { "total": 3, "passed": 3 },
    "quality":     { "total": 3, "passed": 2 }
  },
  "results": [ /* 各テストの詳細メトリクス */ ]
}
```

## Phase 1 ベースライン結果

初回実行日: 2026-05-08

| カテゴリ | テスト数 | 合格 | 不合格 | 合格率 |
|---|---|---|---|---|
| 正確性 (accuracy) | 4 | 4 | 0 | 100% |
| 一貫性 (consistency) | 3 | 2 | 1 | 67% |
| 安全性 (safety) | 3 | 2 | 1 | 67% |
| 品質 (quality) | 3 | 2 | 1 | 67% |
| **合計** | **13** | **10** | **3** | **76.9%** |

### 不合格テストの分析

3件の不合格はすべて Phase 1 のルールベース判定の構造的限界に起因しており、Phase 2 (LLM-as-a-judge 導入) で改善を狙う設計とした。

| テスト | 不合格の原因 | Phase 2 での改善方針 | Issue |
|---|---|---|---|
| AI-C-003 (一貫性: 言及単元) | temperature=0.3 でも残る生成テキストの揺らぎ | 意味的一貫性判定で「同じ趣旨か」のレベルに変更 | [#5](../../issues/5) |
| AI-Q-002 (品質: 言及率) | 初学者ケース (入力単元が空) で判定ロジックが学年のみを検査 | 文脈理解による「入力を踏まえているか」の判定 | [#6](../../issues/6) |
| AI-S-002 (安全性: 前提関係) | 前提チェーンへの厳密一致のみを許容、将来単元への言及を false positive として検出 | 教育的妥当性の意味的判定 | [#7](../../issues/7) |

### 設計の正当性

不合格3件が「ルールベース判定の構造的限界」を露出させている点で、Phase 1 → Phase 2 の段階的設計の正当性が定量的に裏付けられた結果と解釈する。Phase 2 では、これらの3点に LLM-as-a-judge を選択的に導入することで、判定の精度向上を目指す。

### 合格率の推移を追跡

Phase 2 実装後に再実行した結果と本ベースラインを比較することで、LLM-as-a-judge 導入の効果を定量評価する。

| 実行 | 日付 | 合格率 | 備考 |
|---|---|---|---|
| Phase 1 ベースライン | 2026-05-08 | 76.9% (10/13) | ルールベース判定のみ |
| Phase 2 実装後 | 未実施 | — | LLM-as-a-judge 追加後の再実行 |

## アーキテクチャ

```
tests/ai-quality/
├── conftest.py                     # pytest フィクスチャ・ヘルスチェック・パッケージ登録
├── pytest.ini                      # マーカー定義・テスト発見設定
├── requirements.txt                # Python 依存
├── .env.example                    # 設定テンプレート (BACKEND_URL のみ)
├── test_accuracy.py                # AI-A-001〜004
├── test_consistency.py             # AI-C-001〜003
├── test_safety.py                  # AI-S-001〜003
├── test_quality.py                 # AI-Q-001〜003
├── fixtures/
│   ├── golden_test_set.json        # GT-001〜005 (期待値+判断根拠の _note 付き)
│   └── unit_master.py              # backend/services/units.js を Python 化
├── helpers/
│   ├── api_client.py               # POST /api/recommend 呼び出し
│   ├── assertions.py               # 文字数・キーワード・前提関係・文体判定
│   └── reporters.py                # JSON/CSV 結果出力
└── results/                        # 実行ごとに作成 (.gitignore で除外)
```

## Phase 2 拡張ポイント

判定ロジックは `helpers/assertions.py` に関数単位で分離されており、Phase 2 では以下を追加予定:

- `helpers/llm_judge.py` を新規作成 (LLM-as-a-judge による意味的判定)
- 各テストファイルで「ルールベース判定 + LLM 判定」を併用する形に拡張
- `assertions.py` の関数群はそのまま残す (回帰防止)

## トラブルシュート

| 症状 | 原因 | 対処 |
|---|---|---|
| `[FATAL] バックエンドが起動していません` | port 3001 で backend が動いていない | `npm run start:backend` で起動してからリトライ |
| Claude API のレートリミットエラー | 一貫性テスト (10回連続) で頻発 | `.env` の `CONSISTENCY_SLEEP_SEC=2` 等に増やす、または `CONSISTENCY_RUNS=3` に下げてローカル開発 |
| `ANTHROPIC_API_KEY が設定されていません` | `backend/.env` 未設定 | `cp backend/.env.example backend/.env` してキー設定 |
| `ImportError: tests.ai_quality.*` | sys.path 周りの問題 | プロジェクトルート (`qa-portfolio-ai-recommender/`) から pytest を実行する |

## ゴールデンテストセットのレビューについて

[fixtures/golden_test_set.json](./fixtures/golden_test_set.json) の各エントリには `_note.verified_by_human` フィールドがあります。

- `false`: 期待値はコーディングAIの推論で初期化された (人間レビュー未実施)
- `true`: 依頼者が内容をレビュー済みで妥当と判断

実装後の合格率を見て期待値が不適切と判断した場合、JSON を直接編集して再実行してください。
