/**
 * ルールベース単元選定エンジン (バックエンド用)
 *
 * src/recommender.js のロジックを Node.js 用に移植したもの。
 * 推薦理由テキストはここでは生成せず、別途 claudePrompt.js で Claude API により生成する。
 *
 * 入力: { grade, understoodIds, weakIds }
 * 出力: [{ unit, score, isFoundationalForWeak }, ...] (上位3件)
 */

const { getUnitsForGrade, findUnitById, GRADE_ORDER } = require("./units");

/**
 * AC-1〜AC-3 に対応:
 * - AC-1: 1〜3件返す
 * - AC-2: 理解済み単元は除外 / 前提単元が満たされていること
 * - AC-3: 苦手単元の基礎単元はスコア加点で優先
 */
function recommend({ grade, understoodIds, weakIds }) {
  const allUnits = getUnitsForGrade(grade);
  const understoodSet = new Set(understoodIds || []);
  const weakSet = new Set(weakIds || []);

  // 候補: 理解済みでない単元
  const candidates = allUnits.filter(u => !understoodSet.has(u.id));

  // スコアリング
  const scored = candidates.map(u => {
    const prereqsMet = u.prerequisites.every(p => understoodSet.has(p));
    if (!prereqsMet) return null; // AC-2: 前提が満たされていない単元は対象外

    let score = 50; // ベース加点

    // 前提に苦手単元が含まれていれば減点 (苦手の上に積まない)
    const weakPrereqs = u.prerequisites.filter(p => weakSet.has(p));
    if (weakPrereqs.length > 0) {
      score -= 30 * weakPrereqs.length;
    }

    // 苦手単元の前提となる基礎単元 → AC-3 加点
    let isFoundationalForWeak = false;
    for (const wid of weakSet) {
      const weakUnit = findUnitById(wid);
      if (!weakUnit) continue;
      if (weakUnit.prerequisites.includes(u.id)) {
        score += 40;
        isFoundationalForWeak = true;
      }
    }

    // 候補自体が苦手 → 復習として中程度に推す
    if (weakSet.has(u.id)) {
      score += 35;
    }

    // 後続単元 (前提が多い) を少し加点
    score += u.prerequisites.length * 2;

    return { unit: u, score, isFoundationalForWeak };
  }).filter(Boolean);

  // スコア降順 + 同点は学年が低い順 (基礎優先)
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return GRADE_ORDER.indexOf(a.unit.grade) - GRADE_ORDER.indexOf(b.unit.grade);
  });

  return scored.slice(0, 3);
}

module.exports = { recommend };
