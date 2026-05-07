/**
 * E2E 異常系・境界値テスト (E2E-E-001〜005)
 * 対応: docs/test-design.md 3.2
 */
import { expect, test } from "@playwright/test";
import { installErrorMock, installFixedMock } from "./fixtures/mocks";
import { inputs } from "./fixtures/testdata";
import {
  checkUnderstood,
  checkWeak,
  recommendationCards,
  selectGrade,
} from "./fixtures/helpers";

test.describe("E2E 異常系・境界値", () => {
  /**
   * 対応AC: AC-4 (エラーハンドリング)
   * 観点: V-06 (必須入力のエラー処理)
   */
  test("E2E-E-001: 学年未選択で「推薦を受ける」→ エラーメッセージ", async ({ page }) => {
    await page.goto("/");

    // 学年未選択のまま送信
    await page.locator("#submit-btn").click();

    // エラーメッセージが表示される
    const gradeError = page.locator("#grade-error");
    await expect(gradeError).toBeVisible();
    await expect(gradeError).toContainText("学年を選択してください");

    // 結果画面には遷移していない
    await expect(page.locator("#result-screen")).toBeHidden();
  });

  /**
   * 対応AC: AC-4 (エラーハンドリング)
   * 観点: V-08 (入力の境界値)
   */
  test("E2E-E-002: 単元未選択でも推薦が返る", async ({ page }) => {
    await installFixedMock(page, "E002");
    await page.goto("/");

    await selectGrade(page, inputs.E002.grade);
    // 理解済み・苦手ともに未選択のまま送信
    await page.locator("#submit-btn").click();

    await expect(page.locator("#result-screen")).toBeVisible({ timeout: 15_000 });
    // 推薦カードまたは 0件メッセージのいずれかが表示される
    const cards = recommendationCards(page);
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  /**
   * 対応AC: AC-4 (エラーハンドリング)
   * 観点: V-07 (推薦候補0件の境界)
   *
   * ※v1 スコープとして現仕様 (0件メッセージ表示) を受け入れる。
   *   上位学年推薦は Issue #4 参照。
   */
  test("E2E-E-003: 推薦候補0件の境界 (中1全単元理解済み)", async ({ page }) => {
    await installFixedMock(page, "E003");
    await page.goto("/");

    await selectGrade(page, inputs.E003.grade);
    for (const n of inputs.E003.understood) await checkUnderstood(page, n);
    await page.locator("#submit-btn").click();

    await expect(page.locator("#result-screen")).toBeVisible({ timeout: 15_000 });

    // 0件メッセージが表示される
    const results = page.locator("#recommendations");
    await expect(results).toContainText("推薦できる単元が見つかりませんでした");
  });

  /**
   * 対応AC: AC-4 (エラーハンドリング)
   * 観点: V-08 (入力の境界値)
   */
  test("E2E-E-004: 中2全単元を苦手で推薦が返る", async ({ page }) => {
    await installFixedMock(page, "E004");
    await page.goto("/");

    await selectGrade(page, inputs.E004.grade);
    for (const n of inputs.E004.weak) await checkWeak(page, n);
    await page.locator("#submit-btn").click();

    await expect(page.locator("#result-screen")).toBeVisible({ timeout: 15_000 });

    const cards = recommendationCards(page);
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  /**
   * 対応AC: AC-4 (エラーハンドリング)
   * 観点: V-09 (API接続失敗)
   *
   * page.route() で 500 を返し、エラー画面の表示とリトライ案内を確認する。
   */
  test("E2E-E-005: API 接続失敗でエラー画面とリトライ案内", async ({ page }) => {
    await installErrorMock(page, 500);
    await page.goto("/");

    await selectGrade(page, inputs.E005.grade);
    for (const n of inputs.E005.understood) await checkUnderstood(page, n);
    for (const n of inputs.E005.weak) await checkWeak(page, n);
    await page.locator("#submit-btn").click();

    // エラー画面が表示される
    const errorScreen = page.locator("#error-screen");
    await expect(errorScreen).toBeVisible({ timeout: 15_000 });
    await expect(errorScreen).toContainText("AI APIへの接続に失敗しました");

    // リトライボタンが存在する
    const retryBtn = page.locator("#retry-api-btn");
    await expect(retryBtn).toBeVisible();
    await expect(retryBtn).toBeEnabled();
  });
});
