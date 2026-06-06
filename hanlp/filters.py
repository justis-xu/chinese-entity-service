from __future__ import annotations

# HanLP MSRA 标签：https://hanlp.hankcs.com/docs/annotations/ner/msra.html
_TAG_NORM: dict[str, str] = {
    "NR": "PER",  # 人名
    "NS": "LOC",  # 地名
    "NT": "ORG",  # 机构名
}

ALL_TYPES = {"PER", "LOC", "ORG", "TIME"}
MIN_LEN = 2

_GENERIC = {
    "公司", "地方", "人", "东西", "时间", "问题", "方面", "情况",
    "内容", "方式", "地区", "国家", "城市", "产品", "服务", "系统",
    "工作", "用户", "数据", "功能", "平台", "项目", "团队", "业务",
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
        types: Allowed standard types. None means all (PER, LOC, ORG, TIME).

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
        if len(text) <= MIN_LEN:
            continue
        if text in _GENERIC:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)

    return result
