from __future__ import annotations

# spaCy zh_core_web_sm 标签：https://spacy.io/models/zh
_TAG_NORM: dict[str, str] = {
    "PERSON": "PER",  # 人名
    "GPE": "LOC",     # 地缘政治实体（国家、城市等）
    "FAC": "LOC",     # 设施（建筑、场所等）
    "ORG": "ORG",     # 机构名
}

# 统一输出类型：PER=人名 LOC=地名 ORG=机构名
ALL_TYPES = {"PER", "LOC", "ORG"}
MIN_LEN = 2

_GENERIC = {
    "公司", "地方", "人", "东西", "时间", "问题", "方面", "情况",
    "内容", "方式", "地区", "国家", "城市", "产品", "服务", "系统",
    "工作", "用户", "数据", "功能", "平台", "项目", "团队", "业务",
}

# 实体规范化字典：模型因训练数据不足导致截断时，映射到完整名称。
# 遇到新的截断问题直接在这里追加即可。
_ENTITY_NORM: dict[str, str] = {
    # 科技公司
    "宁德": "宁德时代",
    "字节": "字节跳动",
    "拼多": "拼多多",
    "大疆": "大疆创新",
    "科大": "科大讯飞",
    "滴滴": "滴滴出行",
    "京东物": "京东物流",
    "摩拜": "摩拜单车",
    "光年": "光年之外",
    # 媒体/娱乐
    "今日头条月": "今日头条",
    "今日": "今日头条",
    # 地名
    "浦东": "浦东新区",
    "雄安": "雄安新区",
    "前海": "前海合作区",
}


def normalize_tag(tag: str) -> str | None:
    return _TAG_NORM.get(tag)


def filter_entities(
    tagged: list[tuple[str, str]],
    types: list[str] | None = None,
) -> list[str]:
    """Filter and deduplicate entities.

    Args:
        tagged: List of (text, raw_tag) from the model.
        types: Allowed standard types. None means all (PER, LOC, ORG).

    Returns:
        Deduplicated list of entity strings passing all filters.
    """
    allowed = set(types) if types else ALL_TYPES
    seen: set[str] = set()
    result: list[str] = []

    for text, raw_tag in tagged:
        std_tag = normalize_tag(raw_tag)
        if std_tag not in allowed:
            continue
        text = text.strip()
        if len(text) < MIN_LEN:
            continue
        if text in _GENERIC:
            continue
        text = _ENTITY_NORM.get(text, text)
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)

    return result
