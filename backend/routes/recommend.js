/**
 * POST /api/recommend ハンドラ
 *
 * フロー:
 *   1. クエリパラメータによるシミュレーション処理 (?simulate=error / slow)
 *   2. リクエストボディのバリデーション
 *   3. ルールベースで推薦単元を選定
 *   4. Claude API で各単元の推薦理由を生成
 *   5. 整形してレスポンス
 *
 * レスポンス形式 (E2E モックと互換):
 *   {
 *     "recommendations": [
 *       { "unitId", "unitName", "grade", "reason", "score" }, ...
 *     ]
 *   }
 */

const express = require("express");
const { recommend } = require("../services/recommender");
const { generateReasons } = require("../services/claudePrompt");

const router = express.Router();

router.post("/recommend", async (req, res) => {
  // --- 1. シミュレーション処理 (デバッグ用) ---
  const simulate = parseSimulateQuery(req.query.simulate);
  if (simulate.has("error")) {
    return res.status(500).json({ error: "Simulated server error" });
  }
  if (simulate.has("slow")) {
    await sleep(12_000); // フロントの想定: 12秒遅延 (AC-5 違反を再現)
  }

  // --- 2. バリデーション ---
  const { grade, understoodIds, weakIds } = req.body || {};
  if (typeof grade !== "string" || grade.length === 0) {
    return res.status(400).json({ error: "'grade' is required and must be a non-empty string" });
  }
  if (!Array.isArray(understoodIds) || !Array.isArray(weakIds)) {
    return res.status(400).json({ error: "'understoodIds' and 'weakIds' must be arrays" });
  }

  try {
    // --- 3. ルールベース選定 ---
    const scored = recommend({ grade, understoodIds, weakIds });

    // 推薦候補が0件 (中1全単元理解済み等の境界) → そのまま空配列で返す
    if (scored.length === 0) {
      return res.json({ recommendations: [] });
    }

    // --- 4. Claude API で理由生成 ---
    const recommendedUnits = scored.map(s => s.unit);
    const understoodUnits = (understoodIds || [])
      .map(id => findUnitInfo(id))
      .filter(Boolean);
    const weakUnits = (weakIds || [])
      .map(id => findUnitInfo(id))
      .filter(Boolean);

    const reasons = await generateReasons({
      grade,
      understoodUnits,
      weakUnits,
      recommendedUnits,
    });

    // --- 5. 整形してレスポンス ---
    const recommendations = scored.map(s => ({
      unitId: s.unit.id,
      unitName: s.unit.name,
      grade: s.unit.grade,
      reason: reasons[s.unit.id] || "推薦理由を生成できませんでした",
      score: s.score,
    }));

    res.json({ recommendations });
  } catch (e) {
    console.error("[/api/recommend] エラー:", e.message);
    res.status(500).json({ error: e.message || "Internal Server Error" });
  }
});

/** クエリパラメータ ?simulate=error&simulate=slow を Set として受け取る */
function parseSimulateQuery(raw) {
  const set = new Set();
  if (!raw) return set;
  // 単一値 or 配列 (express は同名クエリを配列で受け取る)
  const values = Array.isArray(raw) ? raw : [raw];
  for (const v of values) {
    // カンマ区切りも許容 (例: ?simulate=error,slow)
    String(v).split(",").forEach(token => {
      const t = token.trim();
      if (t) set.add(t);
    });
  }
  return set;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** ID から unit 情報を取得するヘルパ (units.js を参照) */
function findUnitInfo(id) {
  const { findUnitById } = require("../services/units");
  return findUnitById(id);
}

module.exports = router;
