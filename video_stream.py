# -*- coding: utf-8 -*-
"""映客 HTTP-FLV 画面流解析与同源代理辅助。

不保存视频到本地磁盘；只在内存里短期缓存带签名的 stream_addr。
"""
import time
from urllib.parse import urlparse

from curl_cffi import requests as creq

HOT_ROOMS_URL = "https://webapi.busi.inke.cn/web/Live_top_pc"
ALLOWED_HOSTS = {
    "live-pull-ws.ikstatic.cn",
    "live-pull.ikstatic.cn",
}
stream_cache = {}


def fetch_hot_rooms_raw():
    """返回热门直播间原始列表，包含 stream_addr。"""
    data = creq.get(
        HOT_ROOMS_URL,
        impersonate="chrome",
        timeout=10,
    ).json()
    return (data.get("data") or {}).get("list") or []


def find_stream_addr(liveid, rooms=None):
    """按 liveid 查找 stream_addr。"""
    liveid = str(liveid or "")
    if not liveid:
        return ""
    rows = rooms if rooms is not None else fetch_hot_rooms_raw()
    for row in rows or []:
        if str(row.get("live_id") or "") == liveid:
            return str(row.get("stream_addr") or "")
    return ""


def is_allowed_stream_host(url):
    """只允许映客官方拉流域名，避免任意 URL 代理。"""
    try:
        parsed = urlparse(str(url or ""))
    except Exception:
        return False
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in ALLOWED_HOSTS


def resolve_stream_addr(liveid, now=None, ttl=300, force=False):
    """解析并短期缓存 stream_addr。"""
    now = time.time() if now is None else now
    liveid = str(liveid or "")
    cached = stream_cache.get(liveid)
    if not force and cached and now - cached["ts"] < ttl:
        return cached["url"]

    url = find_stream_addr(liveid)
    if url:
        stream_cache[liveid] = {"url": url, "ts": now}
    return url


def iter_upstream_stream(url, chunk_size=64 * 1024):
    """流式读取上游 FLV；只经过内存，不写磁盘。"""
    if not is_allowed_stream_host(url):
        return
    resp = creq.get(
        url,
        stream=True,
        impersonate="chrome",
        timeout=(5, 15),
    )
    try:
        for chunk in resp.iter_content(chunk_size):
            if chunk:
                yield chunk
    finally:
        try:
            resp.close()
        except Exception:
            pass
