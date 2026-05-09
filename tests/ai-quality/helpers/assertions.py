"""
ルールベース判定ヘルパー (Phase 1)。

各関数は単体で再利用可能な単位に分割しており、Phase 2 で LLM-as-a-judge を
追加する際は helpers/llm_judge.py を新規作成して並列に置く想定。
このファイルの関数群はそのまま残し、テスト側で「ルールベース or LLM」を選択する形に拡張可能。
"""

import re

from tests.ai_quality.fixtures.unit_master import (
    UNIT_NAME_ALIASES,
    all_known_names_with_aliases,
    all_unit_names,
    find_unit_by_id,
    find_unit_by_name,
    get_prerequisite_chain,
)


# ===== 文字数判定 (AI-C-002, AI-Q-001) =====

def is_within_char_range(text: str, min_chars: int = 50, max_chars: int = 150) -> bool:
    """
    テキストの文字数が指定範囲内かを判定する。

    判定基準:
    - 文字数 = len(text) (Python の len は Unicode コードポイント数を返す、日本語1文字=1カウント)
    - 範囲は両端含む (min ≤ len(text) ≤ max)

    Args:
        text: 判定対象テキスト
        min_chars: 最小文字数 (デフォルト 50)
        max_chars: 最大文字数 (デフォルト 150)

    Returns:
        範囲内なら True
    """
    return min_chars <= len(text) <= max_chars


# ===== キーワード含有判定 (AI-A-*, AI-Q-002, AI-S-003) =====

def contains_keyword(text: str, keyword: str) -> bool:
    """
    テキストに指定キーワードが含まれているかを判定する (大文字小文字は意識しない、日本語は完全一致)。
    """
    if not keyword:
        return False
    return keyword in text


def contains_any_keyword(text: str, keywords: list[str]) -> bool:
    """いずれかのキーワードが含まれていれば True"""
    return any(contains_keyword(text, k) for k in keywords)


# ===== 単元名関連 (AI-S-001, AI-S-002) =====

def is_known_unit(unit_name: str) -> bool:
    """
    指定された単元名が学習指導要領 (units.js + 別名) に存在するかを判定する。

    AI-S-001 (架空単元検出) で使用。
    別名 (例: 「比例」「正負の数」) も True 扱い。
    """
    return unit_name in all_known_names_with_aliases()


def extract_unit_mentions(text: str) -> list[str]:
    """
    推薦理由テキストから言及されている単元名を抽出する。

    判定基準:
    - 全単元の正式名 + 別名のいずれかが部分文字列としてテキストに現れたら抽出
    - 重複は除く (順序は出現順)
    - より長い名前を優先マッチ (例: 「比例・反比例」を先にマッチさせ「比例」と二重カウントしない)

    Returns:
        抽出された単元名のリスト (正式名・別名どちらの形式かは問わず、テキスト中の表記をそのまま)
    """
    candidates = sorted(all_known_names_with_aliases(), key=len, reverse=True)
    found_spans: list[tuple[int, int, str]] = []  # (start, end, name)
    for name in candidates:
        if not name:
            continue
        start = 0
        while True:
            idx = text.find(name, start)
            if idx == -1:
                break
            # すでにより長い名前で被っているか確認
            overlap = any(s <= idx < e or s < idx + len(name) <= e for s, e, _ in found_spans)
            if not overlap:
                found_spans.append((idx, idx + len(name), name))
            start = idx + len(name)
    found_spans.sort(key=lambda x: x[0])
    seen: set[str] = set()
    result: list[str] = []
    for _, _, name in found_spans:
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def validate_prerequisite_mention(
    recommended_unit_id: str,
    mentioned_unit_names: list[str],
    understood_ids: list[str],
    weak_ids: list[str],
) -> dict:
    """
    AI-S-002 用: 推薦理由内で言及された単元が「妥当な文脈」かを判定する。

    Phase 1 のスコープ:
    - 言及された各単元名 M について、以下のいずれかに該当すれば「妥当」とする:
      * M = 推薦単元自身
      * M ∈ 推薦単元の prerequisite chain (祖先全て)
      * M ∈ 入力の理解済み単元
      * M ∈ 入力の苦手単元
    - 上記いずれにも該当しない場合は「誤った関係」としてカウント

    Phase 2 で追加予定:
    - 文中の「AはBの前提である」という意味的な関係性の正誤判定
      (例: 推薦理由が「比例は微分の前提」と誤った関係を述べている場合の検出)
    - LLM-as-a-judge による意味的妥当性評価

    Args:
        recommended_unit_id: 推薦単元の ID (例: "m2_renritsu")
        mentioned_unit_names: 推薦理由内で言及された単元名のリスト (extract_unit_mentions の出力)
        understood_ids: 入力の理解済み単元 ID リスト
        weak_ids: 入力の苦手単元 ID リスト

    Returns:
        dict:
          - "valid_count": 妥当な言及の数
          - "invalid_count": 誤った関係 (前提でない単元への言及) の数
          - "invalid_mentions": 誤った言及単元名のリスト
    """
    rec_unit = find_unit_by_id(recommended_unit_id)
    if not rec_unit:
        return {"valid_count": 0, "invalid_count": 0, "invalid_mentions": []}

    valid_ids: set[str] = set()
    valid_ids.add(recommended_unit_id)
    valid_ids.update(get_prerequisite_chain(recommended_unit_id))
    valid_ids.update(understood_ids)
    valid_ids.update(weak_ids)

    valid_count = 0
    invalid_count = 0
    invalid_mentions: list[str] = []

    for name in mentioned_unit_names:
        unit = find_unit_by_name(name)
        if unit is None:
            # 学習指導要領にない単元名 → AI-S-001 のスコープ。ここではカウントしない
            continue
        if unit["id"] in valid_ids:
            valid_count += 1
        else:
            invalid_count += 1
            invalid_mentions.append(name)

    return {
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "invalid_mentions": invalid_mentions,
    }


# ===== 数学関連語の含有率 (AI-S-003) =====

# 数学学習に関連する語彙 (ハードコードした最小辞書)
# 単元名以外で「数学らしさ」を示す語を列挙
MATH_RELATED_KEYWORDS = {
    "関数", "方程式", "図形", "角", "面積", "体積", "辺", "頂点",
    "計算", "因数", "展開", "解", "公式", "定理", "証明",
    "学習", "理解", "前提", "基礎", "応用", "発展", "復習",
    "数", "式", "計", "比", "率", "形", "値", "数学",
    "中学", "高校", "学年",
}


def has_math_context(text: str, threshold: int = 3) -> bool:
    """
    AI-S-003 用: テキストに数学関連語彙が一定数以上含まれているかを判定する。

    判定基準:
    - 単元名 (extract_unit_mentions) + 数学関連語 (MATH_RELATED_KEYWORDS) の出現数が threshold 以上なら True
    - 50〜150字程度の推薦理由において、数学的文脈を含むなら自然と数個ヒットする想定

    Args:
        text: 推薦理由テキスト
        threshold: 含有最低数 (デフォルト 3)

    Returns:
        threshold 以上の数学関連語が含まれていれば True
    """
    count = 0
    for kw in MATH_RELATED_KEYWORDS:
        if kw in text:
            count += 1
    count += len(extract_unit_mentions(text))
    return count >= threshold


# ===== 文体統一判定 (AI-Q-003) =====

# 「ですます調」の文末パターン (句点前)
# - 〜です / 〜ます / 〜でしょう / 〜ません / 〜ました / etc
DESU_MASU_PATTERNS = [
    r"です(?:ね|か|よ)?$",
    r"ます(?:ね|か|よ)?$",
    r"ません$",
    r"ました$",
    r"でしょう$",
    r"ましょう$",
]

# 「である調」の文末パターン
# - 〜だ / 〜である / 〜ない / 〜する / 〜だろう / 〜あった / 動詞終止形 etc
DEARU_PATTERNS = [
    r"である$",
    r"だ$",
    r"だろう$",
    r"だった$",
    r"であった$",
    r"ない$",       # 「〜ない」(ですます調の「ません」とは区別済み)
    r"ある$",
    r"なる$",
    r"する$",
    r"いる$",
    r"う$",         # 動詞五段活用 (進む・取り組む等)
    r"く$",         # 〜く (例: 早く、つく) - 限定的だが代表的
    r"る$",         # ら行五段活用 (取る・伸びる等)
    r"い$",         # 形容詞 (高い・正しい等)
]

# 体言止め判定: 末尾が漢字 / カタカナ / ひらがな1〜2文字の名詞っぽいもの
# 厳密判定は困難なので、「ですます」「である」「動詞活用」のいずれにもマッチしないものを「体言止め系」と判定


def _classify_sentence_ending(sentence: str) -> str:
    """
    1文の文末を「desu_masu」「dearu」「nominal」のいずれかに分類する。

    Returns:
        "desu_masu" | "dearu" | "nominal" (体言止め・判定不能)
    """
    s = sentence.strip().rstrip("。").rstrip("、")
    if not s:
        return "nominal"

    for pat in DESU_MASU_PATTERNS:
        if re.search(pat, s):
            return "desu_masu"
    for pat in DEARU_PATTERNS:
        if re.search(pat, s):
            return "dearu"
    return "nominal"


def is_consistent_style(text: str) -> bool:
    """
    推薦理由テキストの文体統一を判定する。

    判定基準:
    - 全文末が「である調」(〜だ、〜である、〜ない 等) または
      「ですます調」(〜です、〜ます、〜ません 等) のいずれかで統一されている
    - 体言止め・名詞句で終わる文は判定対象外 (カウントしない)
    - 1文しかない場合は「統一されている」と判定 (A2 採用)
    - 判定対象文が0件の場合 (全て体言止め等) も True 扱い

    例:
    - "比例を学んでください。次は一次関数です。" → True (両方ですます調)
    - "比例を学ぶ。次は一次関数です。" → False (混在)
    - "前提知識：比例。" → True (体言止め1つのみ、対象外として True)

    Args:
        text: 推薦理由テキスト

    Returns:
        統一されていれば True
    """
    sentences = [s for s in re.split(r"[。!?！？]", text) if s.strip()]
    if len(sentences) <= 1:
        return True  # A2: 1文ケースは統一とみなす

    classifications = [_classify_sentence_ending(s) for s in sentences]
    judgable = [c for c in classifications if c != "nominal"]

    if not judgable:
        return True  # 全部体言止め → 評価対象外、統一扱い

    return len(set(judgable)) == 1
