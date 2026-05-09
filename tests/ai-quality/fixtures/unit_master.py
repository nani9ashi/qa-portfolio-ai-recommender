"""
単元マスタデータ (Python 版)

Source of truth: backend/services/units.js
本ファイルはバックエンドからの参照のため再実装している。
backend/services/units.js を変更した際は本ファイルも同期更新すること。

将来的には共通 JSON スキーマ等にまとめる余地があるが、
本ポートフォリオのスコープでは三重管理を許容している (フロント / バックエンド / Python テスト)。
"""

from typing import Optional


# 学年順序 (上位学年は下位学年の単元を含む)
GRADE_ORDER = ["中1", "中2", "中3", "高1", "高2", "高3"]

# 学年別単元定義
UNITS = {
    "中1": [
        {"id": "m1_seifu",       "name": "正の数と負の数", "prerequisites": []},
        {"id": "m1_mojishiki",   "name": "文字式",         "prerequisites": ["m1_seifu"]},
        {"id": "m1_houteishiki", "name": "一元一次方程式", "prerequisites": ["m1_mojishiki"]},
        {"id": "m1_hireihanpi",  "name": "比例・反比例",   "prerequisites": ["m1_houteishiki"]},
        {"id": "m1_heimen",      "name": "平面図形",       "prerequisites": []},
        {"id": "m1_kuukan",      "name": "空間図形",       "prerequisites": ["m1_heimen"]},
        {"id": "m1_data",        "name": "データの分布",   "prerequisites": []},
        {"id": "m1_kakuritsu",   "name": "確率の基礎",     "prerequisites": []},
    ],
    "中2": [
        {"id": "m2_shiki",        "name": "式の計算",                "prerequisites": ["m1_mojishiki"]},
        {"id": "m2_renritsu",     "name": "連立方程式",              "prerequisites": ["m1_houteishiki"]},
        {"id": "m2_heikou",       "name": "平行線と角",              "prerequisites": ["m1_heimen"]},
        {"id": "m2_goudou",       "name": "合同と証明",              "prerequisites": ["m2_heikou"]},
        {"id": "m2_ichijikansuu", "name": "一次関数",                "prerequisites": ["m1_hireihanpi", "m2_renritsu"]},
        {"id": "m2_data",         "name": "データの分布と箱ひげ図",  "prerequisites": ["m1_data"]},
        {"id": "m2_kakuritsu",    "name": "確率(中2)",               "prerequisites": ["m1_kakuritsu"]},
    ],
    "中3": [
        {"id": "m3_tenkai",          "name": "展開と因数分解", "prerequisites": ["m2_shiki"]},
        {"id": "m3_heihoukon",       "name": "平方根",         "prerequisites": ["m1_seifu"]},
        {"id": "m3_nijihouteishiki", "name": "二次方程式",     "prerequisites": ["m3_tenkai", "m3_heihoukon"]},
        {"id": "m3_souji",           "name": "相似",           "prerequisites": ["m2_goudou"]},
        {"id": "m3_enjou",           "name": "円周角と中心角", "prerequisites": ["m2_goudou"]},
        {"id": "m3_sanheihou",       "name": "三平方の定理",   "prerequisites": ["m3_heihoukon", "m3_souji"]},
        {"id": "m3_nijikansuu",      "name": "二次関数(中3)",  "prerequisites": ["m2_ichijikansuu", "m3_nijihouteishiki"]},
        {"id": "m3_hyohon",          "name": "標本調査",       "prerequisites": ["m2_kakuritsu", "m2_data"]},
    ],
    "高1": [
        {"id": "h1_kazutoshiki",     "name": "数と式",         "prerequisites": ["m3_tenkai", "m3_heihoukon"]},
        {"id": "h1_nijikansuu",      "name": "二次関数(高1)",  "prerequisites": ["h1_kazutoshiki", "m3_nijikansuu"]},
        {"id": "h1_sankakuhi",       "name": "三角比",         "prerequisites": ["m3_sanheihou"]},
        {"id": "h1_zukei_seishitsu", "name": "図形の性質",     "prerequisites": ["m3_souji", "m3_enjou"]},
        {"id": "h1_baai",            "name": "場合の数と確率", "prerequisites": ["m2_kakuritsu"]},
        {"id": "h1_data",            "name": "データの分析",   "prerequisites": ["m2_data"]},
    ],
    "高2": [
        {"id": "h2_shiki",         "name": "式と証明",       "prerequisites": ["h1_kazutoshiki"]},
        {"id": "h2_fukuso",        "name": "複素数と方程式", "prerequisites": ["h2_shiki"]},
        {"id": "h2_zukei",         "name": "図形と方程式",   "prerequisites": ["h1_nijikansuu"]},
        {"id": "h2_sankakukansuu", "name": "三角関数",       "prerequisites": ["h1_sankakuhi"]},
        {"id": "h2_shisuutaisuu",  "name": "指数・対数関数", "prerequisites": ["h1_kazutoshiki"]},
        {"id": "h2_suuretsu",      "name": "数列",           "prerequisites": ["h1_kazutoshiki"]},
        {"id": "h2_tokei",         "name": "統計的な推測",   "prerequisites": ["h1_baai", "h1_data"]},
        {"id": "h2_bibun",         "name": "微分(高2)",      "prerequisites": ["h1_nijikansuu"]},
        {"id": "h2_sekibun",       "name": "積分(高2)",      "prerequisites": ["h2_bibun"]},
        {"id": "h2_seisuu",        "name": "整数の性質",     "prerequisites": []},
    ],
    "高3": [
        {"id": "h3_vector",   "name": "ベクトル",                 "prerequisites": ["h2_zukei", "h1_sankakuhi"]},
        {"id": "h3_kyokugen", "name": "極限",                     "prerequisites": ["h2_suuretsu"]},
        {"id": "h3_bibun",    "name": "微分法",                   "prerequisites": ["h2_bibun", "h3_kyokugen"]},
        {"id": "h3_sekibun",  "name": "積分法",                   "prerequisites": ["h3_bibun", "h2_sekibun"]},
        {"id": "h3_kyokusen", "name": "平面上の曲線と複素数平面", "prerequisites": ["h2_fukuso", "h2_zukei"]},
    ],
}


# ===== 表記揺れ対応辞書 =====
# 設計書・テスト文書・推薦理由テキストで使われる「別名」を、正式 unitId にマッピングする。
# tests/e2e/fixtures/testdata.ts の unitMapping を参照。
# 推薦理由テキスト中の単元名抽出 (extract_unit_mentions) で活用。
UNIT_NAME_ALIASES = {
    # 中1
    "正負の数": "m1_seifu",
    "正の数と負の数": "m1_seifu",
    "文字式": "m1_mojishiki",
    "一元一次方程式": "m1_houteishiki",
    "一次方程式": "m1_houteishiki",
    "比例": "m1_hireihanpi",
    "比例・反比例": "m1_hireihanpi",
    "反比例": "m1_hireihanpi",
    "平面図形": "m1_heimen",
    "空間図形": "m1_kuukan",
    "データの分布": "m1_data",
    "確率の基礎": "m1_kakuritsu",

    # 中2
    "式の計算": "m2_shiki",
    "連立方程式": "m2_renritsu",
    "平行線と角": "m2_heikou",
    "合同と証明": "m2_goudou",
    "一次関数": "m2_ichijikansuu",
    "データの分布と箱ひげ図": "m2_data",
    "箱ひげ図": "m2_data",
    "確率(中2)": "m2_kakuritsu",

    # 中3
    "展開と因数分解": "m3_tenkai",
    "因数分解": "m3_tenkai",
    "平方根": "m3_heihoukon",
    "二次方程式": "m3_nijihouteishiki",
    "相似": "m3_souji",
    "円周角と中心角": "m3_enjou",
    "円周角": "m3_enjou",
    "三平方の定理": "m3_sanheihou",
    "二次関数(中3)": "m3_nijikansuu",
    "標本調査": "m3_hyohon",

    # 高1
    "数と式": "h1_kazutoshiki",
    "二次関数(高1)": "h1_nijikansuu",
    "三角比": "h1_sankakuhi",
    "図形の性質": "h1_zukei_seishitsu",
    "場合の数と確率": "h1_baai",
    "データの分析": "h1_data",

    # 高2
    "式と証明": "h2_shiki",
    "複素数と方程式": "h2_fukuso",
    "複素数": "h2_fukuso",
    "図形と方程式": "h2_zukei",
    "三角関数": "h2_sankakukansuu",
    "指数・対数関数": "h2_shisuutaisuu",
    "指数関数": "h2_shisuutaisuu",
    "対数関数": "h2_shisuutaisuu",
    "数列": "h2_suuretsu",
    "統計的な推測": "h2_tokei",
    "微分(高2)": "h2_bibun",
    "積分(高2)": "h2_sekibun",
    "整数の性質": "h2_seisuu",

    # 高3
    "ベクトル": "h3_vector",
    "極限": "h3_kyokugen",
    "微分法": "h3_bibun",
    "積分法": "h3_sekibun",
    "平面上の曲線と複素数平面": "h3_kyokusen",
    "二次曲線": "h3_kyokusen",

    # 同名異学年単元 (Phase 1 では「いずれかの学年として正しいか」で判定可能、片方の正式IDに紐付け)
    # 「二次関数」 → 文脈で判別不能なため、デフォルトで中3を返し、Phase 2 で文脈推定を追加予定
    "二次関数": "m3_nijikansuu",
    # 「微分」 → 高2を返す (デフォルト)、高3「微分法」とは別単元
    "微分": "h2_bibun",
    # 「積分」 → 同上
    "積分": "h2_sekibun",
    # 「確率」 → 中2を返す (中1「確率の基礎」とは別、高1「場合の数と確率」とも別)
    "確率": "m2_kakuritsu",
}


def get_units_for_grade(grade: str) -> list[dict]:
    """指定学年までの全単元 (累積) を返す"""
    if grade not in GRADE_ORDER:
        return []
    idx = GRADE_ORDER.index(grade)
    result = []
    for i in range(idx + 1):
        g = GRADE_ORDER[i]
        for u in UNITS[g]:
            result.append({**u, "grade": g})
    return result


def find_unit_by_id(unit_id: str) -> Optional[dict]:
    """ID から単元情報を取得"""
    for g in GRADE_ORDER:
        for u in UNITS[g]:
            if u["id"] == unit_id:
                return {**u, "grade": g}
    return None


def find_unit_by_name(unit_name: str) -> Optional[dict]:
    """単元名 (正式名 or 別名) から単元情報を取得"""
    unit_id = UNIT_NAME_ALIASES.get(unit_name)
    if unit_id:
        return find_unit_by_id(unit_id)
    return None


def get_prerequisite_chain(unit_id: str) -> set[str]:
    """
    指定単元の前提単元を再帰的に取得 (祖先全て)。
    AI-S-002 (前提関係誤認) の判定で使用。
    """
    visited: set[str] = set()
    stack = [unit_id]
    while stack:
        current = stack.pop()
        unit = find_unit_by_id(current)
        if not unit:
            continue
        for p in unit["prerequisites"]:
            if p not in visited:
                visited.add(p)
                stack.append(p)
    return visited


def all_unit_names() -> set[str]:
    """全単元の正式名 (set 化、AI-S-001 ハルシネーション検出で参照)"""
    names = set()
    for g in GRADE_ORDER:
        for u in UNITS[g]:
            names.add(u["name"])
    return names


def all_known_names_with_aliases() -> set[str]:
    """正式名 + 別名 全部 (extract_unit_mentions の検索対象集合)"""
    names = all_unit_names()
    names.update(UNIT_NAME_ALIASES.keys())
    return names
