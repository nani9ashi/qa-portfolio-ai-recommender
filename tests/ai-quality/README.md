# AI 出力品質テスト (Phase 1 + Phase 2)

`docs/test-design.md` セクション4 で定義された AI 出力品質テスト 13ケースを Python + pytest で実装。

| ファイル | 対応テスト | 件数 |
|---|---|---|
| [test_accuracy.py](./test_accuracy.py) | AI-A-001〜004 (正確性) | 4 |
| [test_consistency.py](./test_consistency.py) | AI-C-001〜003 (一貫性、各10回連続呼び出し) | 3 |
| [test_safety.py](./test_safety.py) | AI-S-001〜003 (安全性、ハルシネーション/前提関係/無関係情報) | 3 |
| [test_quality.py](./test_quality.py) | AI-Q-001〜003 (品質、文字数/言及/文体) | 3 |

## 判定方式の構成

| Phase | 対象 | 方式 |
|---|---|---|
| **Phase 1** | 全13テストの基礎判定 | ルールベース (キーワード照合・前提チェーン照合・文字数・文体パターン) |
| **Phase 2** | AI-A-001〜004 / AI-S-002 / AI-Q-002 / AI-C-003 | LLM-as-a-judge (`claude-sonnet-4-6`) を選択的に追加 |

LLM-as-a-judge を**全テストに適用しない理由**: ルールベースで十分機能するテストにまで LLM を呼ぶとコストとレビュー対象が膨大化する。Phase 1 ベースラインで「ルールベースの構造的限界」が露出した4テストにのみ選択的導入することで、コスト効率と判定精度を両立。

### Phase 2 の統合パターン

| テスト | 統合パターン | 動作 |
|---|---|---|
| AI-A-001〜004 | 格下げ型 | ルールベース合格 → 判定 AI で再評価 (現状合格の不合格への格下げが起こりうる)。0件マッチは早期 fail で LLM 呼ばず |
| AI-S-002 | 格上げ型 | ルールベース合格 → そのまま合格。フラグあり → LLM が「教育的に妥当な未来言及か」判定し、合格に格上げ |
| AI-Q-002 | 個別再判定型 | 推薦理由ごとにルールベースで言及チェック。マッチなしの理由について LLM が「文脈的に踏まえているか」判定し再集計 |
| AI-C-003 | 同趣旨型 | 全10ランの言及単元集合が一致 → 合格。不一致 → LLM が全ランを1回でまとめて「同じ趣旨か」判定 |

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
| Phase 2 ベースライン | 2026-05-09 | **92.3% (12/13)** | LLM-as-a-judge 追加（Sonnet 4.6） |

## Phase 2 ベースライン結果

初回実行日: 2026-05-09

### 全体結果

| 指標 | Phase 1 | Phase 2 | 変化 |
|---|---|---|---|
| 合格率 | 76.9% (10/13) | **92.3% (12/13)** | **+15.4pt** |
| 正確性 (accuracy) | 4/4 (100%) | 3/4 (75%) | -1 (判定 AI による格下げ) |
| 一貫性 (consistency) | 2/3 (67%) | 3/3 (100%) | +1 (判定 AI による格上げ) |
| 安全性 (safety) | 2/3 (67%) | 3/3 (100%) | +1 (判定 AI による格上げ) |
| 品質 (quality) | 2/3 (67%) | 3/3 (100%) | +1 (判定 AI による格上げ) |

### 判定一致率（人手正解との一致）

上表の合格率とは別に、判定 AI の判定が**人手で独立に定めた正解 (GT) と一致した割合**を計測した（手法の詳細は [docs/test-report.md](../../docs/test-report.md) §4.4）。基準実行の判定対象を凍結し（[fixtures/judge_eval_set.json](./fixtures/judge_eval_set.json)）、判定 AI の合否を伏せたままブラインドで人手正解を付与（[fixtures/ground_truth_verdicts.json](./fixtures/ground_truth_verdicts.json)）、[helpers/agreement.py](./helpers/agreement.py) で突合した（出力: `agreement/agreement_matrix.csv`）。

| 指標 | Phase 1 | Phase 2 | 差 |
|---|---|---|---|
| 合格率 | 76.9% (10/13) | 92.3% (12/13) | +15.4pt |
| **判定一致率** | **61.5% (8/13)** | **92.3% (12/13)** | **+30.8pt** |

合格率と判定一致率がともに上がった。LLM-as-a-judge がルールから最終判定を動かした4件——AI-C-003・AI-Q-002・AI-S-002 の合格への格上げと AI-A-002 の不合格への格下げ——はいずれも人手正解と一致した（「平面図形 → 二次関数」のような一見関連の薄い結び付けも、対称性は中1平面図形の内容で放物線も軸対称であり妥当な横断的言及だった）。残る不一致は、ルール・LLM の両 Phase がともに見逃した AI-A-003 の1件のみ（理解済みと入力された単元の前提へ遡る推薦理由）。合格率は判定を甘くするだけでも上がりうるが、独立した人手正解との一致率も同時に上がったことから、Phase 2 の改善は判定 AI が実際に正しくなった結果だと裏付けられた。n=13・単一ラベラーの点推定（一般化にはコーパス・ラベラーの拡張が必要）。

### 判定経路の集計

| 経路 | 件数 | 該当テスト |
|---|---|---|
| rule alone (passed) | 6 | Phase 1 のみで判定（AI-C-001/002、AI-S-001/003、AI-Q-001/003） |
| rule + llm agreed (passed) | 3 | AI-A-001、AI-A-003、AI-A-004 |
| **rule passed but llm rejected (failed)** | **1** | **AI-A-002（LLM による不合格への格下げ）** |
| **rule + llm rescued (same intent)** | **1** | **AI-C-003（同趣旨判定で合格に格上げ、Issue #5 解決）** |
| **rule + llm rescued (6 reclassified)** | **1** | **AI-Q-002（文脈再分類で合格に格上げ、Issue #6 解決）** |
| **rule + llm rescued (7 valid)** | **1** | **AI-S-002（未来言及として再判定し合格に格上げ、Issue #7 解決）** |

### 不合格テストの分析（更新版）

| テスト | 不合格の原因 | Phase 2 での改善方針 | Phase 2 結果 | Issue |
|---|---|---|---|---|
| AI-C-003 (一貫性: 言及単元) | temperature=0.3 でも残る生成テキストの揺らぎ | 意味的一貫性判定で「同じ趣旨か」レベルに変更 | ✅ 合格に格上げ | [#5](../../issues/5) |
| AI-Q-002 (品質: 言及率) | 初学者ケースで判定ロジックが false negative | 文脈理解による「入力を踏まえているか」の判定 | ✅ 合格に格上げ | [#6](../../issues/6) |
| AI-S-002 (安全性: 前提関係) | 前提チェーンへの厳密一致のみを許容、将来単元への言及を false positive として検出 | 教育的妥当性の意味的判定 | ✅ 合格に格上げ | [#7](../../issues/7) |

### Phase 2 で新たに発見された課題

LLM-as-a-judge による不合格への格下げ判定により、Phase 1 では捕捉できなかった新たな課題が判明した:

| テスト | 発見内容 | 関連 Issue |
|---|---|---|
| AI-A-002 (正確性) | 推薦単元と入力情報の教育的関連付けが弱いケースがある（バックエンドプロンプト精度の課題） | #8 |

これは LLM-as-a-judge が想定通り機能している証拠であり、Phase 1 のキーワード含有判定では検出不可能だった種類の課題。バックエンドプロンプトの改善で対処予定。

### 判定 AI の判定理由の品質

判定 AI（Sonnet 4.6）が出力した判定理由は具体的かつ教育的観点に基づいており、メタ評価の観点でも信頼できる水準だった。例:

**AI-S-002 で合格に格上げされた言及の判定例:**
> 「『図形の性質』は推薦単元『平面図形（中1）』の内包概念であり、前提チェーンの祖先ではないがルールベースでフラグされた。しかし教育的には、平面図形で学ぶ対称性の概念が二次関数の軸対称性の直感的理解を補助するという横断的・補完的言及として妥当」

**AI-A-002 で不合格に格下げされた理由の例:**
> 「『データの分布』に至っては比例・反比例や一次関数との繋がりが極めて希薄で、傾向線の言及も中2段階では不適切。全体的に生徒の苦手克服という文脈から逸れた単元が含まれており、推薦理由が後付けの印象が強い」

判定理由は `tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/llm_judge_traces/` に JSONL 形式で完全に保存されており、後からのメタ評価が可能な構造としている。

### 設計の正当性

- Phase 1 の不合格 3 件すべてが Phase 2 で合格に格上げされた
- Phase 1 では検出できない新規課題が Phase 2 で1件発見された (不合格への格下げ)
- 「ルールベース → 判定 AI」の段階的設計により、ルール単独では起こりえない双方向（合格への格上げ・不合格への格下げ）の判定の動きが生じた

> 【追記】上記は合格率・判定経路の観点での整理である。人手正解との一致（前掲「判定一致率」）で見ると、格上げ3件・格下げ1件はいずれも人手正解と一致しており、LLM 層の介入は判定 AI を人手正解に近づけていた。段階設計の価値は、LLM が判定 AI の正しさを高めたことに加え「双方の判定を独立した人手正解と突合し、どこで誰が正しいかを定量化できる」点にもあり、本プロジェクトではこの突合により、LLM 層が判定を人手正解に近づけたことと、両 Phase が見逃した AI-A-003 の残課題の双方を検出できた。

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
│   ├── judge_eval_set.json         # 判定一致率用に凍結した判定対象コーパス (判定 AI が見た出力)
│   ├── ground_truth_verdicts.json  # 13ケースの人手正解の判定 (ブラインド独立判定)
│   └── unit_master.py              # backend/services/units.js を Python 化
├── helpers/
│   ├── api_client.py               # POST /api/recommend 呼び出し
│   ├── assertions.py               # 文字数・キーワード・前提関係・文体判定
│   ├── agreement.py                # 判定一致率の凍結・算出 (人手正解との突合)
│   └── reporters.py                # JSON/CSV 結果出力
├── agreement/                      # 判定一致率の突合表 (agreement_matrix.csv / .json)
└── results/                        # 実行ごとに作成 (.gitignore で除外)
```

## Phase 2 実装内容

判定ロジックは Phase 2 で以下のように拡張済み:

| ファイル | 役割 |
|---|---|
| [helpers/llm_judge.py](./helpers/llm_judge.py) | `judge_with_llm()` 関数 + JSON パース + リトライ + フォールバック + トレース保存 |
| [helpers/llm_judge_prompts.py](./helpers/llm_judge_prompts.py) | 4種類の判定プロンプト (ACCURACY / PREREQUISITE / INPUT_REFERENCE / CONSISTENCY) |
| [helpers/reporters.py](./helpers/reporters.py) | `metrics` 内に `rule_based` / `llm_judge` / `final_judgment` を併存させる出力 |
| [helpers/assertions.py](./helpers/assertions.py) | Phase 1 のルールベース判定をそのまま保持 (回帰防止) |

### 設定 (環境変数)

`tests/ai-quality/.env` で以下を上書き可能 (デフォルト値は `.env.example` 参照):

| 環境変数 | デフォルト | 用途 |
|---|---|---|
| `LLM_JUDGE_MODEL` | `claude-sonnet-4-6` | 判定 AI モデル ID |
| `LLM_JUDGE_PASS_THRESHOLD` | `3` | スコア閾値 (この値以上で合格) |
| `LLM_JUDGE_TEMPERATURE` | `0` | 判定の安定性最大化 |
| `LLM_JUDGE_MAX_TOKENS` | `500` | 最大出力トークン数 |
| `ANTHROPIC_API_KEY` | (`backend/.env` から自動継承) | Claude API キー |

### 判定 AI トレース

各 判定 AI 呼び出しの完全な履歴 (プロンプト・生レスポンス・パース結果・タイムスタンプ・モデル ID) が以下に保存されます。

```
tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/llm_judge_traces/
├── AI-A-001.jsonl
├── AI-A-002.jsonl
├── AI-S-002.jsonl
├── AI-Q-002.jsonl
└── AI-C-003.jsonl
```

各 JSONL の1行 = 1判定。`gt_id` フィールドで横断分析、`fallback` フィールドで LLM 失敗時の挙動も追跡可能。

### フォールバック動作

判定 AI の呼び出しが失敗 (API キー未設定 / モデル未存在 / JSON パース失敗 / ネットワーク等) した場合:

1. 1回だけリトライ
2. それでも失敗したら `fallback: true` の結果を返す
3. テスト側はフォールバック結果を見て**ルールベース判定の結果を最終判定として採用** (Phase 1 と同じ動作、安全側)
4. トレースには `error` フィールドにエラーメッセージを記録

これにより、判定 AI の不調がテスト全体を止めることはありません。

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
