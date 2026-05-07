/**
 * E2E 正常系テスト (E2E-N-001〜007)
 * 対応: docs/test-design.md 3.1
 */
import { expect, test } from "@playwright/test";
import { installFixedMock } from "./fixtures/mocks";
import { inputs, canonical } from "./fixtures/testdata";
import {
  backToForm,
  checkUnderstood,
  checkWeak,
  getRecommendationNames,
  getRecommendationReasons,
  getRecommendationSnapshot,
  recommendationCards,
  selectGrade,
  submitRecommendation,
} from "./fixtures/helpers";

test.describe("E2E 正常系", () => {
  /**
   * 対応AC: AC-1 (基本的なレコメンド)
   * 観点: V-01 (基本的なレコメンド表示)
   */
  test("E2E-N-001: 基本的なレコメンド表示 (中1)", async ({ page }) => {
    await installFixedMock(page, "N001");
    await page.goto("/");

    await selectGrade(page, inputs.N001.grade);
    for (const n of inputs.N001.understood) await checkUnderstood(page, n);
    for (const n of inputs.N001.weak) await checkWeak(page, n);
    await submitRecommendation(page);

    const cards = recommendationCards(page);
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
    expect(count).toBeLessThanOrEqual(3);

    const names = await getRecommendationNames(page);
    const reasons = await getRecommendationReasons(page);
    for (const name of names) expect(name).not.toBe("");
    for (const reason of reasons) {
      expect(reason).not.toBe("");
      // 日本語を含む (ひらがな・カタカナ・漢字のいずれか)
      expect(reason).toMatch(/[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/);
    }
  });

  /**
   * 対応AC: AC-1 (基本的なレコメンド)
   * 観点: V-01 (基本的なレコメンド表示)
   */
  test("E2E-N-002: 基本的なレコメンド表示 (高3)", async ({ page }) => {
    await installFixedMock(page, "N002");
    await page.goto("/");

    await selectGrade(page, inputs.N002.grade);
    for (const n of inputs.N002.understood) await checkUnderstood(page, n);
    for (const n of inputs.N002.weak) await checkWeak(page, n);
    await submitRecommendation(page);

    const cards = recommendationCards(page);
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
    expect(count).toBeLessThanOrEqual(3);

    const names = await getRecommendationNames(page);
    const reasons = await getRecommendationReasons(page);
    for (const name of names) expect(name).not.toBe("");
    for (const reason of reasons) expect(reason).not.toBe("");
  });

  /**
   * 対応AC: AC-2 (前提条件の尊重)
   * 観点: V-02 (理解済み単元の除外)
   */
  test("E2E-N-003: 理解済み単元の除外", async ({ page }) => {
    await installFixedMock(page, "N003");
    await page.goto("/");

    await selectGrade(page, inputs.N003.grade);
    for (const n of inputs.N003.understood) await checkUnderstood(page, n);
    for (const n of inputs.N003.weak) await checkWeak(page, n);
    await submitRecommendation(page);

    // 推薦結果エリアに「一次関数」が含まれないこと (アサートは結果エリア限定)
    const results = page.locator("#recommendations");
    await expect(results).not.toContainText(canonical("一次関数"));
  });

  /**
   * 対応AC: AC-2 (前提条件の尊重)
   * 観点: V-03 (前提知識の尊重)
   */
  test("E2E-N-004: 前提知識の尊重 (比例が理解済みであることが反映)", async ({ page }) => {
    await installFixedMock(page, "N004");
    await page.goto("/");

    await selectGrade(page, inputs.N004.grade);
    for (const n of inputs.N004.understood) await checkUnderstood(page, n);
    await submitRecommendation(page);

    // (c) 両方アサート
    // 1. 一次関数が推薦結果に含まれる
    const names = await getRecommendationNames(page);
    expect(names).toContain(canonical("一次関数"));

    // 2. 推薦理由テキストに「比例」が含まれる (end-to-end データ疎通確認)
    const reasons = await getRecommendationReasons(page);
    const anyMentionsHirei = reasons.some(r => r.includes("比例"));
    expect(anyMentionsHirei).toBe(true);
  });

  /**
   * 対応AC: AC-2 (前提条件の尊重)
   * 観点: V-03 (前提知識の尊重)
   */
  test("E2E-N-005: 前提未習のため二次関数(中3)が推薦されない", async ({ page }) => {
    await installFixedMock(page, "N005");
    await page.goto("/");

    await selectGrade(page, inputs.N005.grade);
    for (const n of inputs.N005.understood) await checkUnderstood(page, n);
    await submitRecommendation(page);

    // 推薦結果エリアに限定して「二次関数(中3)」が含まれないことを確認
    const results = page.locator("#recommendations");
    await expect(results).not.toContainText("二次関数(中3)");
  });

  /**
   * 対応AC: AC-3 (苦手単元の優先)
   * 観点: V-04 (苦手関連単元の推薦)
   */
  test("E2E-N-006: 苦手関連単元の推薦", async ({ page }) => {
    await installFixedMock(page, "N006");
    await page.goto("/");

    await selectGrade(page, inputs.N006.grade);
    for (const n of inputs.N006.understood) await checkUnderstood(page, n);
    for (const n of inputs.N006.weak) await checkWeak(page, n);
    await submitRecommendation(page);

    const names = await getRecommendationNames(page);
    // 連立方程式または関連基礎単元 (文字式・一元一次方程式・式の計算) のいずれかが含まれる
    const relatedBases = [
      canonical("連立方程式"),
      canonical("文字式"),
      canonical("一元一次方程式"),
      canonical("式の計算"),
    ];
    const hasRelated = names.some(n => relatedBases.includes(n));
    expect(hasRelated).toBe(true);
  });

  /**
   * 対応AC: AC-1 (基本的なレコメンド)
   * 観点: V-05 (推薦単元の一貫性)
   *
   * 同一入力を3回連続で送信し、UI 層の決定性を検証する。
   * モックは固定レスポンスのため、毎回同一の表示となるはず。
   */
  test("E2E-N-007: 推薦単元の一貫性 (3回連続送信)", async ({ page }) => {
    await installFixedMock(page, "N007");
    await page.goto("/");

    const snapshots: string[] = [];

    for (let i = 0; i < 3; i++) {
      await selectGrade(page, inputs.N007.grade);
      for (const n of inputs.N007.understood) await checkUnderstood(page, n);
      for (const n of inputs.N007.weak) await checkWeak(page, n);
      await submitRecommendation(page);

      snapshots.push(await getRecommendationSnapshot(page));

      if (i < 2) {
        await backToForm(page);
      }
    }

    // 3回の表示が完全一致
    expect(snapshots[1]).toBe(snapshots[0]);
    expect(snapshots[2]).toBe(snapshots[0]);
  });
});
