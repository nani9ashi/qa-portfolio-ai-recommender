# セットアップと起動

ローカル環境でアプリを起動したり、テストを実行したりするための手順書です。

> README からの分離版です。動作証明は CI バッジ ([E2E Tests](https://github.com/nani9ashi/qa-portfolio-ai-recommender/actions/workflows/e2e-tests.yml) / [AI Quality Tests](https://github.com/nani9ashi/qa-portfolio-ai-recommender/actions/workflows/ai-quality-tests.yml)) と [テスト完了レポート](./test-report.md) で確認できますので、必須ではありません。

---

## 1. 依存パッケージのインストール

```bash
npm install
```

## 2. API キーの設定 (バックエンド使用時のみ)

```bash
cp backend/.env.example backend/.env
```

`backend/.env` を開き、`ANTHROPIC_API_KEY=...` の値を [Anthropic Console](https://console.anthropic.com/) で取得した API キーに置き換えてください。

## 3. 起動

```bash
# フロントエンド (port 5173) + バックエンド (port 3001) を並列起動
npm run start

# 個別起動も可能
npm run start:frontend   # http://localhost:5173 でアプリ表示
npm run start:backend    # http://localhost:3001/api/recommend で API 提供
```

ブラウザで `http://localhost:5173` を開くとアプリが利用できます。

## 4. E2E テストの実行

```bash
npx playwright install chromium  # 初回のみ
npx playwright test --config tests/playwright.config.ts
```

E2E テストは `page.route()` で `/api/recommend` をモックしているため、**バックエンドの起動・実 API キーがなくても実行できます**。

## 5. AI 出力品質テストの実行 (Python + 実 Claude API)

実際に Claude API を呼び出して、生成された推薦理由の品質を検証するテストです。**バックエンド起動と有効な API キーが必須**です。

### 5-1. 共通準備（初回のみ）

```bash
# 仮想環境の作成
python -m venv .venv
```

仮想環境の有効化（OS別）:

**Windows (PowerShell)**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

依存パッケージとテスト用 `.env` の準備:

```bash
pip install -r tests/ai-quality/requirements.txt
cp tests/ai-quality/.env.example tests/ai-quality/.env
```

### 5-2. 実行（2つのターミナルで並列）

**必ず「2つのターミナル」を使用し、両方で仮想環境を有効にしてください。**

| 手順 | **ターミナル1（バックエンド起動）** | **ターミナル2（テスト実行）** |
| --- | --- | --- |
| 1. ルートへ移動 | `cd qa-portfolio-ai-recommender` | `cd qa-portfolio-ai-recommender` |
| 2. 仮想環境を有効化 | Windows: `.\.venv\Scripts\Activate.ps1`<br>mac/Linux: `source .venv/bin/activate` | Windows: `.\.venv\Scripts\Activate.ps1`<br>mac/Linux: `source .venv/bin/activate` |
| 3. 実行 | `npm run start:backend` | `pytest tests/ai-quality` |

> **Note**: ターミナル2を実行する前に、ターミナル1でバックエンドが正常に起動していることを確認してください。
> 例: `[backend] Listening on http://localhost:3001`

実行結果は `tests/ai-quality/results/YYYY-MM-DD_HH-MM-SS/` 配下に `summary.json` と `details.csv` として出力されます。

詳細は [tests/ai-quality/README.md](../tests/ai-quality/README.md) を参照。

---

[← README に戻る](../README.md)
