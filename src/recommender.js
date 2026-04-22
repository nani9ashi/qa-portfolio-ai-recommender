/**
 * レコメンドロジック (AIモック)
 * - 理解済み単元は推薦しない (AC-2)
 * - 推薦単元の前提が理解済みでカバーされていること (AC-2)
 * - 苦手単元に関連する基礎単元が優先される (AC-3)
 * - 1〜3件返す (AC-1)
 */
function recommend({ grade, understoodIds, weakIds }) {
  const allUnits = getUnitsForGrade(grade);
  const understoodSet = new Set(understoodIds);
  const weakSet = new Set(weakIds);

  // 候補: 理解済みでない単元
  const candidates = allUnits.filter(u => !understoodSet.has(u.id));

  // スコアリング
  const scored = candidates.map(u => {
    const prereqsMet = u.prerequisites.every(p => understoodSet.has(p));
    let score = 0;
    const reasonParts = [];

    // 前提が満たされている → ベース加点
    if (prereqsMet) {
      score += 50;
    } else {
      // 前提が満たされていない単元は対象外 (AC-2)
      return null;
    }

    // 前提に苦手単元が含まれていない (苦手の上に積み上げない配慮)
    const weakPrereqs = u.prerequisites.filter(p => weakSet.has(p));
    if (weakPrereqs.length > 0) {
      score -= 30 * weakPrereqs.length;
      reasonParts.push(
        `ただし前提単元の「${weakPrereqs.map(p => findUnitById(p)?.name).join("・")}」が苦手と回答されているため、まずはその復習がおすすめです。`
      );
    }

    // 苦手単元が前提に含む単元 → 基礎として優先 (AC-3)
    let isFoundationalForWeak = false;
    for (const wid of weakSet) {
      const weakUnit = findUnitById(wid);
      if (!weakUnit) continue;
      if (weakUnit.prerequisites.includes(u.id)) {
        score += 40;
        isFoundationalForWeak = true;
        reasonParts.push(
          `苦手と回答された「${weakUnit.name}」の基礎となる単元のため、ここを固めると次のステップに進みやすくなります。`
        );
      }
    }

    // 苦手単元自体は再学習として中程度に推す
    if (weakSet.has(u.id)) {
      score += 35;
      reasonParts.push(`苦手と回答された単元のため、もう一度基礎から見直すことをおすすめします。`);
    }

    // 直前に学んだであろう単元 (前提単元数が多い = 後続の単元) を少し加点
    score += u.prerequisites.length * 2;

    // 前提が満たされている説明
    if (reasonParts.length === 0) {
      const prereqNames = u.prerequisites
        .map(p => findUnitById(p)?.name)
        .filter(Boolean);
      if (prereqNames.length > 0) {
        reasonParts.push(
          `理解済みの「${prereqNames.join("・")}」を前提とする単元のため、自然に次のステップとして学習を進められます。`
        );
      } else {
        reasonParts.push(
          `${u.grade}の基礎単元として、まず取り組むのに適しています。`
        );
      }
    }

    return {
      unit: u,
      score,
      reason: reasonParts.join(" "),
      isFoundationalForWeak,
    };
  }).filter(Boolean);

  // スコア降順 + 同点は学年が低い順 (基礎優先)
  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return GRADE_ORDER.indexOf(a.unit.grade) - GRADE_ORDER.indexOf(b.unit.grade);
  });

  // 上位3件 (1件以上はある想定だが、ない場合は空配列)
  return scored.slice(0, 3);
}
