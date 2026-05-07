# E2E テスト

AI学習レコメンド機能のE2Eテスト (Playwright + TypeScript)。

## 実装対象

`docs/test-design.md` セクション3のE2Eテストケース全17件:

| ファイル | テストID | 件数 |
|---|---|---|
| `e2e/normal.spec.ts` | E2E-N-001〜007 | 7 |
| `e2e/error.spec.ts` | E2E-E-001〜005 | 5 |
| `e2e/ui.spec.ts` | E2E-U-001〜004 | 4 |
| `e2e/performance.spec.ts` | E2E-P-001 | 1 |

## 初回セットアップ

```bash
# プロジェクトルートで
npm install
npx playwright install chromium
```

## 実行

```bash
# プロジェクトルートから
npm run test:e2e              # 全テスト実行
npm run test:e2e:ui           # UI モード (デバッグ用)
npm run test:e2e:report       # 前回のHTMLレポート表示

# 特定ファイル
npx playwright test e2e/normal.spec.ts --config tests/playwright.config.ts

# 特定テストID
npx playwright test -g "E2E-N-003" --config tests/playwright.config.ts
```

※ `package.json` の `test:e2e` は `playwright test` を `tests/` ディレクトリから実行する構成。`playwright.config.ts` が `testDir: "./e2e"` を指すため、プロジェクトルートから `npm run test:e2e` でも動作する (設定読み込みがルートから `tests/playwright.config.ts` を探す)。直接コマンドを打つ場合は `--config tests/playwright.config.ts` を付けること。

## アーキテクチャ

### モック戦略

- `page.route('**/api/recommend', ...)` で AI API 呼び出しをインターセプト
- 入力ペイロード (grade / understoodIds / weakIds) に応じて分岐したレスポンスを返す
- モック定義は `e2e/fixtures/mocks.ts`、入力データは `e2e/fixtures/testdata.ts` に集約

### セレクタ戦略

- 現状: `#id` + `data-unit-id` 属性を使用
- `getByText()` は UI テスト (E2E-U-*) のみ使用
- `data-testid` への移行は技術的負債として認識しているが、現セレクタで十分機能しているため優先度低

### トレーサビリティ

各テストは:
- タイトル先頭にテストID (例: `E2E-N-001: 基本的なレコメンド表示`)
- JSDoc に対応AC・観点ID

を明示しているため、`docs/test-design.md` と行き来できる。

## 制約事項

- 各テストは独立動作 (テスト間状態共有なし)
- 環境依存のハードコード禁止 (`baseURL` は `playwright.config.ts`)
- アプリ本体のロジック・UI は変更しない
