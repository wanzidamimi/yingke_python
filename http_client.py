# -*- coding: utf-8 -*-
"""HTTP 会话骨架：curl_cffi 复刻浏览器/APP 的 TLS 指纹。

阶段 2 抓包确认后：
  - 把 UA / 头填进 config.py
  - 在 get_session() 里按抓包结果补 headers
  - 若有 enter-room 接口，在这里实现 enter_room(room) -> 真实 WS 参数
"""
import curl_cffi.requests as creq

import config


def get_session(impersonate="chrome"):
    """返回带指定 TLS 指纹的 Session。"""
    s = creq.Session(impersonate=impersonate)
    s.headers.update({
        "User-Agent": config.USER_AGENT or "",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    s.headers.update(config.EXTRA_HEADERS or {})
    return s


def enter_room(session, room):
    """TODO: 调进入直播间接口，返回 WS 握手所需参数 dict。

    骨架阶段返回空 dict，调用方会用 config.WS_URL_TEMPLATE 尝试直连并给出明确提示。
    """
    return {}


def build_ws_url(room, params=None):
    """TODO: 用 config.WS_URL_TEMPLATE 拼真实 WS 地址。"""
    if not config.WS_URL_TEMPLATE:
        return None
    params = params or {}
    try:
        return config.WS_URL_TEMPLATE.format(room_id=room, **params)
    except (KeyError, IndexError):
        return config.WS_URL_TEMPLATE
