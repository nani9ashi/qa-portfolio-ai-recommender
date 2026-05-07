/**
 * E2E 非機能テスト (E2E-P-001)
 * 対応: docs/test-design.md 3.4
 */
import { expect, test } from "@playwright/test";
import { installFixedMock } from "./fixtures/mocks";
import { checkUnderstood, checkWeak, selectGrade } from "./fixtures/helpers";
import { inputs } from "./fixtures/testdata";

const TIMEOUT_MS = 10_000; // AC-5 の閾値

test.describe("E2E 非機能テスト", () => {
  /**
   * 対応AC: AC-5 (レスポンス10秒以内)
   * 観点: V-11 (レスポンスタイム)
   *
   * 「推薦を受ける」ボタン押下から結果表示までの時間を計測。
   * モック遅延を段階的に入れ、いずれも10秒以内に表示されることを確認する。
   */
  test("E2E-P-001 (即時): モック遅延なしで結果表示までの時間が10秒以内", async ({ page }) => {
    await installFixedMock(page, "N003", { delayMs: 0 });
    await page.goto("/");

    await selectGrade(page, inputs.N003.grade);
    for (const n of inputs.N003.understood) await checkUnderstood(page, n);
    for (const n of inputs.N003.weak) await checkWeak(page, n);

    const t0 = Date.now();
    await page.locator("#submit-btn").click();
    await expect(page.locator("#result-screen")).toBeVisible({ timeout: TIMEOUT_MS });
    const elapsed = Date.now() - t0;

    expect(elapsed).toBeLessThanOrEqual(TIMEOUT_MS);
  });

  /**
   * 対応AC: AC-5 (レスポンス10秒以内)
   * 観点: V-11 (レスポンスタイム)
   *
   * モック側に 2 秒の遅延を挿入。合計時間が 10 秒以内であることを確認する。
   * (即時応答だけで合格とみなすのは不十分、という指針に対応)
   */
  test("E2E-P-001 (遅延2秒): モック遅延2秒でも結果表示までの時間が10秒以内", async ({ page }) => {
    await installFixedMock(page, "N003", { delayMs: 2_000 });
    await page.goto("/");

    await selectGrade(page, inputs.N003.grade);
    for (const n of inputs.N003.understood) await checkUnderstood(page, n);
    for (const n of inputs.N003.weak) await checkWeak(page, n);

    const t0 = Date.now();
    await page.locator("#submit-btn").click();
    await expect(page.locator("#result-screen")).toBeVisible({ timeout: TIMEOUT_MS });
    const elapsed = Date.now() - t0;

    expect(elapsed).toBeGreaterThanOrEqual(2_000); // 遅延が効いている
    expect(elapsed).toBeLessThanOrEqual(TIMEOUT_MS);
  });
});
