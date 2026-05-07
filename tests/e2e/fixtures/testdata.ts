/**
 * テスト入力データ定義
 *
 * docs/test-design.md セクション3で定義された E2E テストケースの入力を集約する。
 *
 * 単元名マッピング: 設計書の表記と units.js の正式名に不一致があるため、
 * 設計書表記をキーとして正式名・unitId を引けるテーブルを用意する。
 * 詳細は本ファイル末尾の unitMapping を参照。
 */

// --- 単元マッピング表 ---
// 設計書 → units.js (正式名) / unitId
export const unitMapping: Record<
  string,
  { unitId: string; canonicalName: string; grade: string }
> = {
  // 中1
  "正負の数":         { unitId: "m1_seifu",     canonicalName: "正の数と負の数", grade: "中1" },
  "正の数と負の数":   { unitId: "m1_seifu",     canonicalName: "正の数と負の数", grade: "中1" }, // 正式名でも引けるよう別名登録 (m1AllUnits 等で参照)
  "文字式":           { unitId: "m1_mojishiki", canonicalName: "文字式",         grade: "中1" },
  "一元一次方程式": { unitId: "m1_houteishiki", canonicalName: "一元一次方程式", grade: "中1" },
  "比例・反比例": { unitId: "m1_hireihanpi",  canonicalName: "比例・反比例",   grade: "中1" },
  "比例":         { unitId: "m1_hireihanpi",  canonicalName: "比例・反比例",   grade: "中1" }, // 設計書で「比例」と表記されるため別名登録
  "平面図形":     { unitId: "m1_heimen",      canonicalName: "平面図形",       grade: "中1" },
  "空間図形":     { unitId: "m1_kuukan",      canonicalName: "空間図形",       grade: "中1" },
  "データの分布": { unitId: "m1_data",        canonicalName: "データの分布",   grade: "中1" },
  "確率の基礎":   { unitId: "m1_kakuritsu",   canonicalName: "確率の基礎",     grade: "中1" },

  // 中2
  "式の計算":     { unitId: "m2_shiki",       canonicalName: "式の計算",       grade: "中2" },
  "連立方程式":   { unitId: "m2_renritsu",    canonicalName: "連立方程式",     grade: "中2" },
  "平行線と角":   { unitId: "m2_heikou",      canonicalName: "平行線と角",     grade: "中2" },
  "合同と証明":   { unitId: "m2_goudou",      canonicalName: "合同と証明",     grade: "中2" },
  "一次関数":     { unitId: "m2_ichijikansuu", canonicalName: "一次関数",      grade: "中2" },
  "データの分布と箱ひげ図": { unitId: "m2_data", canonicalName: "データの分布と箱ひげ図", grade: "中2" },
  "確率(中2)":    { unitId: "m2_kakuritsu",   canonicalName: "確率(中2)",      grade: "中2" },

  // 中3
  "展開と因数分解": { unitId: "m3_tenkai",       canonicalName: "展開と因数分解", grade: "中3" },
  "平方根":         { unitId: "m3_heihoukon",    canonicalName: "平方根",         grade: "中3" },
  "二次方程式":     { unitId: "m3_nijihouteishiki", canonicalName: "二次方程式",  grade: "中3" },
  "相似":           { unitId: "m3_souji",        canonicalName: "相似",           grade: "中3" },
  "円周角と中心角": { unitId: "m3_enjou",        canonicalName: "円周角と中心角", grade: "中3" },
  "三平方の定理":   { unitId: "m3_sanheihou",    canonicalName: "三平方の定理",   grade: "中3" },
  "二次関数(中3)":  { unitId: "m3_nijikansuu",   canonicalName: "二次関数(中3)",  grade: "中3" },
  "標本調査":       { unitId: "m3_hyohon",       canonicalName: "標本調査",       grade: "中3" },

  // 高1
  "数と式":           { unitId: "h1_kazutoshiki", canonicalName: "数と式",         grade: "高1" },
  "二次関数(高1)":    { unitId: "h1_nijikansuu",  canonicalName: "二次関数(高1)",  grade: "高1" },
  // E2E-N-002 の「二次関数」解釈: 高1 を採用 (response-to-coding-ai-round2.md A参照)
  "二次関数":         { unitId: "h1_nijikansuu",  canonicalName: "二次関数(高1)",  grade: "高1" },
  "三角比":           { unitId: "h1_sankakuhi",   canonicalName: "三角比",         grade: "高1" },
  "図形の性質":       { unitId: "h1_zukei_seishitsu", canonicalName: "図形の性質", grade: "高1" },
  "場合の数と確率":   { unitId: "h1_baai",        canonicalName: "場合の数と確率", grade: "高1" },
  "データの分析":     { unitId: "h1_data",        canonicalName: "データの分析",   grade: "高1" },

  // 高2
  "式と証明":         { unitId: "h2_shiki",       canonicalName: "式と証明",       grade: "高2" },
  "複素数と方程式":   { unitId: "h2_fukuso",      canonicalName: "複素数と方程式", grade: "高2" },
  "図形と方程式":     { unitId: "h2_zukei",       canonicalName: "図形と方程式",   grade: "高2" },
  "三角関数":         { unitId: "h2_sankakukansuu", canonicalName: "三角関数",     grade: "高2" },
  "指数・対数関数":   { unitId: "h2_shisuutaisuu", canonicalName: "指数・対数関数", grade: "高2" },
  "数列":             { unitId: "h2_suuretsu",    canonicalName: "数列",           grade: "高2" },
  "統計的な推測":     { unitId: "h2_tokei",       canonicalName: "統計的な推測",   grade: "高2" },
  "微分(高2)":        { unitId: "h2_bibun",       canonicalName: "微分(高2)",      grade: "高2" },
  "微分":             { unitId: "h2_bibun",       canonicalName: "微分(高2)",      grade: "高2" }, // 設計書「微分」の別名登録
  "積分(高2)":        { unitId: "h2_sekibun",     canonicalName: "積分(高2)",      grade: "高2" },
  "整数の性質":       { unitId: "h2_seisuu",      canonicalName: "整数の性質",     grade: "高2" },

  // 高3
  "ベクトル":         { unitId: "h3_vector",      canonicalName: "ベクトル",       grade: "高3" },
  "極限":             { unitId: "h3_kyokugen",    canonicalName: "極限",           grade: "高3" },
  "微分法":           { unitId: "h3_bibun",       canonicalName: "微分法",         grade: "高3" },
  "積分法":           { unitId: "h3_sekibun",     canonicalName: "積分法",         grade: "高3" },
  "平面上の曲線と複素数平面": { unitId: "h3_kyokusen", canonicalName: "平面上の曲線と複素数平面", grade: "高3" },
};

/** 設計書表記の単元名リストを unitId 配列に変換 */
export function toIds(names: string[]): string[] {
  return names.map(n => {
    const m = unitMapping[n];
    if (!m) throw new Error(`unitMapping に未登録: "${n}"`);
    return m.unitId;
  });
}

/** 単元の正式名 (units.js 表記) を取得 */
export function canonical(name: string): string {
  const m = unitMapping[name];
  if (!m) throw new Error(`unitMapping に未登録: "${name}"`);
  return m.canonicalName;
}

// --- 学年ごとの全単元 (E2E-E-003, E2E-E-004 用) ---
export const m1AllUnits: string[] = [
  "正の数と負の数", "文字式", "一元一次方程式", "比例・反比例",
  "平面図形", "空間図形", "データの分布", "確率の基礎",
];

export const m2AllUnits: string[] = [
  "式の計算", "連立方程式", "平行線と角", "合同と証明",
  "一次関数", "データの分布と箱ひげ図", "確率(中2)",
];

// --- E2E テストの入力データ ---
export interface TestInput {
  grade: string;
  understood: string[]; // 設計書表記の単元名
  weak: string[];
}

export const inputs = {
  N001: { grade: "中1", understood: ["正負の数"],           weak: ["文字式"] },
  N002: { grade: "高3", understood: ["数と式", "二次関数"], weak: ["微分"] },
  N003: { grade: "中2", understood: ["一次関数"],           weak: ["連立方程式"] },
  N004: { grade: "中2", understood: ["比例"],               weak: [] as string[] },
  N005: { grade: "中3", understood: ["比例"],               weak: [] as string[] },
  N006: { grade: "中2", understood: ["一次関数"],           weak: ["連立方程式"] },
  N007: { grade: "中2", understood: ["一次関数"],           weak: ["連立方程式"] },
  E001: { grade: "",    understood: [] as string[],         weak: [] as string[] },
  E002: { grade: "中2", understood: [] as string[],         weak: [] as string[] },
  E003: { grade: "中1", understood: m1AllUnits,             weak: [] as string[] },
  E004: { grade: "中2", understood: [] as string[],         weak: m2AllUnits },
  E005: { grade: "中2", understood: ["一次関数"],           weak: ["連立方程式"] },
} as const;
