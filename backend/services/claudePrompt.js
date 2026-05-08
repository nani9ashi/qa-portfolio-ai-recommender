/**
 * Claude API 呼び出し + プロンプト構築
 *
 * 推薦単元と入力情報を受け取り、各単元の推薦理由を生成する。
 * - JSON 厳格出力をプロンプトで指示し、後処理で JSON.parse
 * - パース失敗時は {...} 抽出のフォールバック → 最終失敗時は例外を投げる
 */

const Anthropic = require("@anthropic-ai/sdk");

// モデル名は将来切り替えやすいよう定数として切り出し
const MODEL = process.env.CLAUDE_MODEL || "claude-haiku-4-5-20251001";
const MAX_TOKENS = 500; // 推薦理由50〜150字×3件 + JSON構造で十分
const TEMPERATURE = 0.3; // 一貫性テスト (AI-C-001) を考慮した低温度

const SYSTEM_PROMPT = `あなたは中高生向け数学学習レコメンダーの推薦理由生成役です。
生徒の学年・理解済み単元・苦手単元・推薦単元のリストを受け取り、
各推薦単元に対する推薦理由を日本語で生成してください。

要件:
- 各理由は50〜150字程度
- 学習指導要領の単元体系に沿った内容
- 既に理解している単元との繋がりを示す
- 苦手単元がある場合はそれとの関連も触れる
- 中高生に分かりやすい言葉で
- 出力は厳密に JSON 形式のみ、他の文章は含めない`;

/**
 * Claude API を呼び出し、推薦単元ごとの理由文を生成する。
 *
 * @param {Object} params
 * @param {string} params.grade           - 例: "中2"
 * @param {Array<{id, name}>} params.understoodUnits - 理解済み単元 (オブジェクト配列)
 * @param {Array<{id, name}>} params.weakUnits       - 苦手単元
 * @param {Array<{id, name, grade}>} params.recommendedUnits - 推薦単元
 * @returns {Promise<Object>} unitId をキーとした理由文のオブジェクト
 */
async function generateReasons({ grade, understoodUnits, weakUnits, recommendedUnits }) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error("ANTHROPIC_API_KEY が設定されていません");
  }
  if (!recommendedUnits || recommendedUnits.length === 0) {
    return {};
  }

  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const userPrompt = buildUserPrompt({ grade, understoodUnits, weakUnits, recommendedUnits });

  const response = await client.messages.create({
    model: MODEL,
    max_tokens: MAX_TOKENS,
    temperature: TEMPERATURE,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userPrompt }],
  });

  // レスポンスの最初の text ブロックを取り出す
  const textBlock = response.content.find(b => b.type === "text");
  if (!textBlock) {
    throw new Error("Claude API レスポンスに text ブロックが含まれていません");
  }

  const parsed = parseJsonResponse(textBlock.text);
  if (!parsed.reasons || typeof parsed.reasons !== "object") {
    throw new Error("Claude API レスポンスに 'reasons' オブジェクトが含まれていません");
  }
  return parsed.reasons;
}

/** ユーザープロンプトを整形 */
function buildUserPrompt({ grade, understoodUnits, weakUnits, recommendedUnits }) {
  const fmtList = arr => (arr.length === 0 ? "(なし)" : arr.map(u => `「${u.name}」`).join("、"));
  const recommendedList = recommendedUnits
    .map(u => `- unitId="${u.id}", name="${u.name}", grade="${u.grade}"`)
    .join("\n");

  return `学年: ${grade}
理解済み単元: ${fmtList(understoodUnits)}
苦手単元: ${fmtList(weakUnits)}

推薦単元 (各々について理由を生成してください):
${recommendedList}

出力形式 (厳密に以下の JSON のみ、コードブロックなし):
{
  "reasons": {
    "<unitId>": "理由文 (50〜150字)",
    ...
  }
}`;
}

/**
 * Claude のレスポンスから JSON をパース。
 * 直接 JSON.parse → 失敗時に {...} 抽出してリトライ。
 */
function parseJsonResponse(text) {
  // 1段階目: 素直に JSON.parse
  try {
    return JSON.parse(text.trim());
  } catch {
    // 2段階目: ```json ... ``` ブロックや前後テキストを除去して再試行
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch (e) {
        throw new Error(`Claude API レスポンスの JSON パース失敗 (抽出後): ${e.message}`);
      }
    }
    throw new Error("Claude API レスポンスから JSON を抽出できませんでした");
  }
}

module.exports = {
  generateReasons,
  // テスト用に内部関数もエクスポート (現時点ではバックエンドのテストは未実装)
  __internal: { buildUserPrompt, parseJsonResponse, MODEL, MAX_TOKENS, TEMPERATURE },
};
