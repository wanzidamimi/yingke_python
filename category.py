# -*- coding: utf-8 -*-
"""消息分类骨架：映客真实消息类型待抓包确认后填入 _TYPE_MAP。"""
import re

CATEGORIES = [
    ("chat",   "弹幕",   "#e6e8eb"),
    ("gift",   "礼物",   "#ff8fab"),
    ("like",   "点赞",   "#8ecae6"),
    ("member", "进场",   "#a0c4ff"),
    ("social", "关注/分享", "#bde0fe"),
    ("stats",  "数据",   "#9aa3af"),
    ("rank",   "排行",   "#ffb703"),
    ("system", "系统",   "#63b3ff"),
    ("guard",  "守护",   "#ffd166"),
    ("notice", "公告",   "#c77dff"),
    ("other",  "其他",   "#9aa3af"),
]
CATEGORY_LABELS = {k: lab for k, lab, _ in CATEGORIES}

# TODO: 阶段 2 后填真实消息类型 -> 类别
_TYPE_MAP = {}

_BADGE_PAT = re.compile(r"(荣誉等级\s*\d+|勋章\s*\d+\s*级|VIP\s*\d+|Lv\.?\s*\d+)", re.IGNORECASE)
_HINT = [
    (re.compile(r"送礼|赠送|礼物"), "gift"),
    (re.compile(r"点赞|点了赞"), "like"),
    (re.compile(r"关注了|分享了|进入直播间"), "social"),
]


def classify(message_type, *texts):
    mt = message_type or ""
    cat = _TYPE_MAP.get(mt, "other")
    main = str(texts[0]) if texts else ""
    joined = " ".join(str(t) for t in texts if t)
    if _BADGE_PAT.search(joined):
        cat = "badge" if "badge" in CATEGORY_LABELS else "other"
    elif cat == "other":
        for pat, hint in _HINT:
            if pat.search(main):
                cat = hint
                break
    return {
        "category": cat,
        "category_label": CATEGORY_LABELS.get(cat, "其他"),
        "message_type": mt or None,
    }
