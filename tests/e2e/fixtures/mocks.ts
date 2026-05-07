/**
 * API モック定義
 *
 * `page.route('**\/api/recommend', ...)` で使う分岐ロジックと、テストIDごとの
 * 固定レスポンス定義を集約する。
 *
 * - 入力パターン (grade + understoodIds + weakIds) を見て分岐
 * - 各レスポンスは docs/test-design.md の期待結果に沿った内容
 * - モック内容を変更する場合は、対応テストケースの期待結果との整合を確認すること
 */
import type { Page, Route } from "@playwright/test";
import { toIds } from "./testdata";

// --- 型 ---
export interface RecommendationPayload {
  unitId: string;
  unitName: string;
  grade: string;
  reason: string;
  score: number;
}

export interface RecommendResponse {
  recommendations: RecommendationPayload[];
}

interface RequestBody {
  grade: string;
  understoodIds: string[];
  weakIds: string[];
}

// --- テストID別の固定レスポンス ---
// 各レスポンスは対応するテストケースの期待結果を満たすよう設計されている。
export const mockResponses: Record<string, RecommendResponse> = {
  // E2E-N-001: 中1、理解済み=[正負の数]、苦手=[文字式]
  // 期待: 1〜3件、単元名と推薦理由が表示、日本語
  N001: {
    recommendations: [
      {
        unitId: "m1_mojishiki",
        unitName: "文字式",
        grade: "中1",
        reason: "苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。",
        score: 85,
      },
      {
        unitId: "m1_heimen",
        unitName: "平面図形",
        grade: "中1",
        reason: "中1の基礎単元として、まず取り組むのに適しています。",
        score: 52,
      },
    ],
  },

  // E2E-N-002: 高3、理解済み=[数と式、二次関数(高1)]、苦手=[微分(高2)]
  // 期待: 1〜3件、単元名と推薦理由が表示
  N002: {
    recommendations: [
      {
        unitId: "h2_bibun",
        unitName: "微分(高2)",
        grade: "高2",
        reason: "苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。",
        score: 87,
      },
      {
        unitId: "h1_sankakuhi",
        unitName: "三角比",
        grade: "高1",
        reason: "高1の基礎単元として、関連領域の理解を深めるのに適しています。",
        score: 50,
      },
    ],
  },

  // E2E-N-003: 中2、理解済み=[一次関数]、苦手=[連立方程式]
  // 期待: 推薦リストに「一次関数」が含まれない
  // モックは理解済みの「一次関数」を意図的に除外したレスポンスを返す
  N003: {
    recommendations: [
      {
        unitId: "m2_renritsu",
        unitName: "連立方程式",
        grade: "中2",
        reason: "苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。",
        score: 85,
      },
      {
        unitId: "m2_goudou",
        unitName: "合同と証明",
        grade: "中2",
        reason: "理解済みの「平行線と角」を前提とする単元のため、自然に次のステップとして学習を進められます。",
        score: 52,
      },
    ],
  },

  // E2E-N-004: 中2、理解済み=[比例・反比例]、苦手=[]
  // 期待: 一次関数が推薦される場合、比例が理解済みであることが反映
  // モック設計意図: 推薦理由に「比例」を明示的に含めることで end-to-end データ疎通を検証
  // (E2E-N-004 で推薦理由に「比例」が含まれる想定のため、reason に「比例」を含める)
  N004: {
    recommendations: [
      {
        unitId: "m2_ichijikansuu",
        unitName: "一次関数",
        grade: "中2",
        reason: "理解済みの「比例・反比例」を前提とする単元のため、自然に次のステップとして学習を進められます。",
        score: 54,
      },
    ],
  },

  // E2E-N-005: 中3、理解済み=[比例・反比例]、苦手=[]
  // 期待: 二次関数(中3)は推薦されない (前提の一次関数・二次方程式が未習のため)
  N005: {
    recommendations: [
      {
        unitId: "m1_mojishiki",
        unitName: "文字式",
        grade: "中1",
        reason: "理解済みの「正の数と負の数」を前提とする単元のため、自然に次のステップとして学習を進められます。",
        score: 52,
      },
      {
        unitId: "m3_heihoukon",
        unitName: "平方根",
        grade: "中3",
        reason: "理解済みの「正の数と負の数」を前提とする単元のため、自然に次のステップとして学習を進められます。",
        score: 50,
      },
    ],
  },

  // E2E-N-006: 中2、理解済み=[一次関数]、苦手=[連立方程式]
  // 期待: 推薦リストに連立方程式または関連基礎単元が含まれる
  N006: {
    recommendations: [
      {
        unitId: "m2_renritsu",
        unitName: "連立方程式",
        grade: "中2",
        reason: "苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。",
        score: 85,
      },
    ],
  },

  // E2E-N-007: 同一入力3回 → 毎回完全一致 (ルールベースのため)
  // モックは固定レスポンス。3回とも同じ内容を返す。
  N007: {
    recommendations: [
      {
        unitId: "m2_renritsu",
        unitName: "連立方程式",
        grade: "中2",
        reason: "苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。",
        score: 85,
      },
      {
        unitId: "m2_goudou",
        unitName: "合同と証明",
        grade: "中2",
        reason: "理解済みの「平行線と角」を前提とする単元のため、自然に次のステップとして学習を進められます。",
        score: 52,
      },
    ],
  },

  // E2E-E-002: 中2、理解済み=[]、苦手=[]
  // 期待: 推薦が表示される (入力不足でも推薦可能)
  E002: {
    recommendations: [
      {
        unitId: "m1_seifu",
        unitName: "正の数と負の数",
        grade: "中1",
        reason: "中1の基礎単元として、まず取り組むのに適しています。",
        score: 52,
      },
    ],
  },

  // E2E-E-003: 中1、理解済み=[中1の全単元]、苦手=[]
  // 期待: 推薦候補0件のメッセージが表示される
  E003: {
    recommendations: [],
  },

  // E2E-E-004: 中2、理解済み=[]、苦手=[中2の全単元]
  // 期待: 推薦が返される (苦手関連を含む)
  E004: {
    recommendations: [
      {
        unitId: "m1_seifu",
        unitName: "正の数と負の数",
        grade: "中1",
        reason: "苦手と回答された「式の計算」の基礎となる単元のため、ここを固めると次のステップに進みやすくなります。",
        score: 92,
      },
      {
        unitId: "m1_mojishiki",
        unitName: "文字式",
        grade: "中1",
        reason: "苦手と回答された「式の計算」の基礎となる単元のため、ここを固めると次のステップに進みやすくなります。",
        score: 92,
      },
    ],
  },
};

// --- モック応答用のインターセプタ ---
type MockOptions = {
  /** レスポンス遅延 (ms)。E2E-P-001 で使用 */
  delayMs?: number;
  /** HTTP エラーを返す (E2E-E-005 で使用) */
  errorStatus?: number;
};

/**
 * 固定レスポンスを返すモックをインストールする。
 * テストID を指定すると mockResponses[id] の内容を返す。
 */
export async function installFixedMock(
  page: Page,
  testId: keyof typeof mockResponses,
  options: MockOptions = {}
): Promise<void> {
  await page.route("**/api/recommend", async (route: Route) => {
    if (options.errorStatus) {
      await route.fulfill({
        status: options.errorStatus,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal Server Error" }),
      });
      return;
    }

    if (options.delayMs) {
      await new Promise(r => setTimeout(r, options.delayMs));
    }

    const body = mockResponses[testId];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

/**
 * リクエストボディに応じて分岐するモック (複数ケースを1つのテスト内で試す用)
 * 現状は使用されていないが、将来の拡張用に定義。
 */
export async function installDynamicMock(
  page: Page,
  resolver: (body: RequestBody) => RecommendResponse
): Promise<void> {
  await page.route("**/api/recommend", async (route: Route) => {
    const request = route.request();
    const body = request.postDataJSON() as RequestBody;
    const response = resolver(body);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    });
  });
}

/** エラーレスポンス専用のヘルパ (E2E-E-005 用) */
export async function installErrorMock(page: Page, status = 500): Promise<void> {
  await page.route("**/api/recommend", async (route: Route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({ error: "Internal Server Error" }),
    });
  });
}

/** toIds をモック内で参照できるよう再エクスポート (未使用時は削除可) */
export { toIds };
