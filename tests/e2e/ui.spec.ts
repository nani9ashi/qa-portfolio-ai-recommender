/**
 * E2E UIテスト (E2E-U-001〜004)
 * 対応: docs/test-design.md 3.3
 *
 * UI テストは E2E-U-* のみで getByText() などの表示文言依存セレクタを使う。
 */
import { expect, test } from "@playwright/test";
import { installFixedMock } from "./fixtures/mocks";
import { checkUnderstood, selectGrade, submitRecommendation } from "./fixtures/helpers";
import { inputs } from "./fixtures/testdata";

test.describe("E2E UIテスト", () => {
  /**
   * 対応AC: AC外
   * 観点: V-10 (画面の振る舞い)
   *
   * ※現実装の累積表示を正として採用。UX改善は Issue #3 参照。
   * 期待結果: 学年を中1→中2に変更すると、中2 の fieldset が追加で表示される。
   */
  test("E2E-U-001: 学年変更でチェックボックス単元が追加表示される", async ({ page }) => {
    await page.goto("/");

    // 中1 選択
    await selectGrade(page, "中1");
    const understoodArea = page.locator("#understood-units");
    await expect(understoodArea.locator("fieldset.grade-group")).toHaveCount(1);
    await expect(understoodArea.locator("fieldset.grade-group legend")).toHaveText(["中学1年"]);

    // 中2 に変更
    await selectGrade(page, "中2");
    await expect(understoodArea.locator("fieldset.grade-group")).toHaveCount(2);
    await expect(understoodArea.locator("fieldset.grade-group legend")).toHaveText([
      "中学1年",
      "中学2年",
    ]);
  });

  /**
   * 対応AC: AC外
   * 観点: V-10 (画面の振る舞い)
   */
  test("E2E-U-002: 結果画面から「もう一度推薦を受ける」で入力画面に戻る", async ({ page }) => {
    await installFixedMock(page, "N001");
    await page.goto("/");

    await selectGrade(page, inputs.N001.grade);
    for (const n of inputs.N001.understood) await checkUnderstood(page, n);
    await submitRecommendation(page);

    await expect(page.locator("#result-screen")).toBeVisible();

    await page.getByRole("button", { name: "もう一度推薦を受ける" }).click();

    await expect(page.locator("#input-screen")).toBeVisible();
    await expect(page.locator("#result-screen")).toBeHidden();
  });

  /**
   * 対応AC: AC外
   * 観点: V-10 (画面の振る舞い)
   */
  test("E2E-U-003: 推薦単元がカード形式で表示される", async ({ page }) => {
    await installFixedMock(page, "N001");
    await page.goto("/");

    await selectGrade(page, inputs.N001.grade);
    for (const n of inputs.N001.understood) await checkUnderstood(page, n);
    await submitRecommendation(page);

    // カード (.rec-card) が1件以上表示され、各カードに順位表示と単元名がある
    const cards = page.locator("#recommendations .rec-card");
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);

    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      await expect(card.locator(".rank")).toContainText(`第${i + 1}位`);
      await expect(card.locator("h3")).not.toHaveText("");
      await expect(card.locator(".reason")).not.toHaveText("");
    }
  });

  /**
   * 対応AC: AC外
   * 観点: V-10 (画面の振る舞い)
   */
  test("E2E-U-004: 単元が学年ごとに fieldset でグループ化されている", async ({ page }) => {
    await page.goto("/");
    await selectGrade(page, "中2");

    // 理解済みセクション
    const understoodGroups = page.locator("#understood-units fieldset.grade-group");
    await expect(understoodGroups).toHaveCount(2);

    // 各 fieldset に legend が存在する
    const legendTexts = await understoodGroups.locator("legend").allTextContents();
    expect(legendTexts).toEqual(["中学1年", "中学2年"]);

    // 苦手セクション側も同様
    const weakGroups = page.locator("#weak-units fieldset.grade-group");
    await expect(weakGroups).toHaveCount(2);
  });
});
