/**
 * 共通ヘルパ (入力操作・結果取得)
 *
 * セレクタ戦略: 現状 data-testid が未整備のため、#id + data-unit-id + ラベルの
 * <input value="unitId"> を頼りに操作する。将来の data-testid 移行時はここを差し替える。
 */
import { expect, Locator, Page } from "@playwright/test";
import { unitMapping } from "./testdata";

/** 学年ドロップダウンで学年を選択 */
export async function selectGrade(page: Page, grade: string): Promise<void> {
  await page.locator("#grade").selectOption(grade);
}

/**
 * 指定した単元 (設計書表記の名前) のチェックボックスを理解済みセクションでチェック
 */
export async function checkUnderstood(page: Page, unitName: string): Promise<void> {
  const m = unitMapping[unitName];
  if (!m) throw new Error(`unitMapping に未登録: "${unitName}"`);
  await page.locator(`#understood-units input[value="${m.unitId}"]`).check();
}

/** 指定した単元を苦手セクションでチェック */
export async function checkWeak(page: Page, unitName: string): Promise<void> {
  const m = unitMapping[unitName];
  if (!m) throw new Error(`unitMapping に未登録: "${unitName}"`);
  await page.locator(`#weak-units input[value="${m.unitId}"]`).check();
}

/** 「推薦を受ける」ボタンを押してローディング完了を待つ */
export async function submitRecommendation(page: Page): Promise<void> {
  await page.locator("#submit-btn").click();
  await expect(page.locator("#result-screen")).toBeVisible({ timeout: 15_000 });
}

/** 推薦カードのロケータ */
export function recommendationCards(page: Page): Locator {
  return page.locator("#recommendations .rec-card");
}

/** 推薦カードの単元名テキスト一覧を取得 */
export async function getRecommendationNames(page: Page): Promise<string[]> {
  const cards = recommendationCards(page);
  const count = await cards.count();
  const names: string[] = [];
  for (let i = 0; i < count; i++) {
    const h3 = cards.nth(i).locator("h3");
    const raw = (await h3.textContent()) ?? "";
    // 「第N位」の接頭辞を除去
    names.push(raw.replace(/^第\d+位/, "").trim());
  }
  return names;
}

/** 推薦カードの理由テキスト一覧を取得 */
export async function getRecommendationReasons(page: Page): Promise<string[]> {
  const cards = recommendationCards(page);
  const count = await cards.count();
  const reasons: string[] = [];
  for (let i = 0; i < count; i++) {
    const p = cards.nth(i).locator(".reason");
    reasons.push(((await p.textContent()) ?? "").trim());
  }
  return reasons;
}

/** 推薦カード全体 (単元名+理由) の連結スナップショットを取得 (E2E-N-007 用) */
export async function getRecommendationSnapshot(page: Page): Promise<string> {
  const names = await getRecommendationNames(page);
  const reasons = await getRecommendationReasons(page);
  return names.map((n, i) => `${n}||${reasons[i]}`).join("\n");
}

/** 結果画面からフォームに戻る (E2E-N-007 連続送信用) */
export async function backToForm(page: Page): Promise<void> {
  await page.locator("#retry-btn").click();
  await expect(page.locator("#input-screen")).toBeVisible();
}
