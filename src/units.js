/**
 * 数学単元データ (学習指導要領準拠・完全版)
 *
 * 中学: 文部科学省 中学校学習指導要領 数学科 (令和3年度施行)
 *       中1–3 の A数と式 / B図形 / C関数 / Dデータの活用 を網羅
 *
 * 高校: 文部科学省 高等学校学習指導要領 数学科 (令和4年度施行)
 *       数学I・A → 高1, 数学II・B → 高2, 数学III・C → 高3 に対応
 *
 * 各単元には前提単元 (prerequisites) を定義し、レコメンドの依存関係に使う。
 */
const UNITS = {

  // ===== 中学1年 =====
  // A:正の数と負の数 / 文字式 / 一元一次方程式
  // B:平面図形 / 空間図形
  // C:比例・反比例
  // D:データの分布 / 確率の基礎（頻度確率）
  "中1": [
    { id: "m1_seifu",       name: "正の数と負の数", prerequisites: [] },
    { id: "m1_mojishiki",   name: "文字式",         prerequisites: ["m1_seifu"] },
    { id: "m1_houteishiki", name: "一元一次方程式", prerequisites: ["m1_mojishiki"] },
    { id: "m1_hireihanpi",  name: "比例・反比例",   prerequisites: ["m1_houteishiki"] },
    { id: "m1_heimen",      name: "平面図形",       prerequisites: [] },
    { id: "m1_kuukan",      name: "空間図形",       prerequisites: ["m1_heimen"] },
    { id: "m1_data",        name: "データの分布",   prerequisites: [] },
    { id: "m1_kakuritsu",   name: "確率の基礎",     prerequisites: [] },
  ],

  // ===== 中学2年 =====
  // A:式の計算 / 連立方程式
  // B:平行線と角 / 合同と証明
  // C:一次関数
  // D:データの分布と箱ひげ図 / 確率（場合の数ベース）
  "中2": [
    { id: "m2_shiki",        name: "式の計算",              prerequisites: ["m1_mojishiki"] },
    { id: "m2_renritsu",     name: "連立方程式",            prerequisites: ["m1_houteishiki"] },
    { id: "m2_heikou",       name: "平行線と角",            prerequisites: ["m1_heimen"] },
    { id: "m2_goudou",       name: "合同と証明",            prerequisites: ["m2_heikou"] },
    { id: "m2_ichijikansuu", name: "一次関数",              prerequisites: ["m1_hireihanpi", "m2_renritsu"] },
    { id: "m2_data",         name: "データの分布と箱ひげ図", prerequisites: ["m1_data"] },
    { id: "m2_kakuritsu",    name: "確率(中2)",              prerequisites: ["m1_kakuritsu"] },
  ],

  // ===== 中学3年 =====
  // A:平方根 / 展開と因数分解 / 二次方程式
  // B:相似 / 円周角と中心角 / 三平方の定理
  // C:関数y=ax²（二次関数）
  // D:標本調査
  "中3": [
    { id: "m3_tenkai",           name: "展開と因数分解", prerequisites: ["m2_shiki"] },
    { id: "m3_heihoukon",        name: "平方根",         prerequisites: ["m1_seifu"] },
    { id: "m3_nijihouteishiki",  name: "二次方程式",     prerequisites: ["m3_tenkai", "m3_heihoukon"] },
    { id: "m3_souji",            name: "相似",           prerequisites: ["m2_goudou"] },
    { id: "m3_enjou",            name: "円周角と中心角", prerequisites: ["m2_goudou"] },
    { id: "m3_sanheihou",        name: "三平方の定理",   prerequisites: ["m3_heihoukon", "m3_souji"] },
    { id: "m3_nijikansuu",       name: "二次関数(中3)",  prerequisites: ["m2_ichijikansuu", "m3_nijihouteishiki"] },
    { id: "m3_hyohon",           name: "標本調査",       prerequisites: ["m2_kakuritsu", "m2_data"] },
  ],

  // ===== 高校1年 (数学I・数学A) =====
  // 数学I : 数と式（集合・命題・不等式含む）/ 図形と計量（三角比・正弦定理・余弦定理）
  //          / 二次関数 / データの分析
  // 数学A : 図形の性質 / 場合の数と確率
  "高1": [
    { id: "h1_kazutoshiki",      name: "数と式",         prerequisites: ["m3_tenkai", "m3_heihoukon"] },
    { id: "h1_nijikansuu",       name: "二次関数",       prerequisites: ["h1_kazutoshiki", "m3_nijikansuu"] },
    { id: "h1_sankakuhi",        name: "三角比",         prerequisites: ["m3_sanheihou"] },
    { id: "h1_zukei_seishitsu",  name: "図形の性質",     prerequisites: ["m3_souji", "m3_enjou"] },
    { id: "h1_baai",             name: "場合の数と確率", prerequisites: ["m2_kakuritsu"] },
    { id: "h1_data",             name: "データの分析",   prerequisites: ["m2_data"] },
  ],

  // ===== 高校2年 (数学II・数学B) =====
  // 数学II: いろいろな式（式と証明・複素数と方程式）/ 図形と方程式
  //          / 指数関数・対数関数 / 三角関数 / 微分・積分の考え
  // 数学B : 数列 / 統計的な推測
  // 数学A : 整数の性質（数学と人間の活動）
  "高2": [
    { id: "h2_shiki",         name: "式と証明",       prerequisites: ["h1_kazutoshiki"] },
    { id: "h2_fukuso",        name: "複素数と方程式", prerequisites: ["h2_shiki"] },
    { id: "h2_zukei",         name: "図形と方程式",   prerequisites: ["h1_nijikansuu"] },
    { id: "h2_sankakukansuu", name: "三角関数",       prerequisites: ["h1_sankakuhi"] },
    { id: "h2_shisuutaisuu",  name: "指数・対数関数", prerequisites: ["h1_kazutoshiki"] },
    { id: "h2_suuretsu",      name: "数列",           prerequisites: ["h1_kazutoshiki"] },
    { id: "h2_tokei",         name: "統計的な推測",   prerequisites: ["h1_baai", "h1_data"] },
    { id: "h2_bibun",         name: "微分(高2)",      prerequisites: ["h1_nijikansuu"] },
    { id: "h2_sekibun",       name: "積分(高2)",      prerequisites: ["h2_bibun"] },
    { id: "h2_seisuu",        name: "整数の性質",     prerequisites: [] },
  ],

  // ===== 高校3年 (数学III・数学C) =====
  // 数学III: 極限 / 微分法 / 積分法
  // 数学C  : ベクトル / 平面上の曲線と複素数平面
  "高3": [
    { id: "h3_vector",   name: "ベクトル",               prerequisites: ["h2_zukei", "h1_sankakuhi"] },
    { id: "h3_kyokugen", name: "極限",                   prerequisites: ["h2_suuretsu"] },
    { id: "h3_bibun",    name: "微分法",                 prerequisites: ["h2_bibun", "h3_kyokugen"] },
    { id: "h3_sekibun",  name: "積分法",                 prerequisites: ["h3_bibun", "h2_sekibun"] },
    { id: "h3_kyokusen", name: "平面上の曲線と複素数平面", prerequisites: ["h2_fukuso", "h2_zukei"] },
  ],
};

/** 学年順序: 上の学年は下の学年の単元も対象に含める */
const GRADE_ORDER = ["中1", "中2", "中3", "高1", "高2", "高3"];

/** 指定学年までの全単元を取得 (上位学年は下位学年を含む) */
function getUnitsForGrade(grade) {
  const idx = GRADE_ORDER.indexOf(grade);
  if (idx < 0) return [];
  const result = [];
  for (let i = 0; i <= idx; i++) {
    const g = GRADE_ORDER[i];
    UNITS[g].forEach(u => result.push({ ...u, grade: g }));
  }
  return result;
}

/** ID → 単元オブジェクト */
function findUnitById(id) {
  for (const g of GRADE_ORDER) {
    const u = UNITS[g].find(x => x.id === id);
    if (u) return { ...u, grade: g };
  }
  return null;
}
