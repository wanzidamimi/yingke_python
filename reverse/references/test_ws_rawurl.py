# -*- coding: utf-8 -*-
"""用完全原样的 WS URL（不 parse 重组）发升级请求，排除编码二次处理。仅学习研究。"""
import base64, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests

s = requests.Session()
KW = {"impersonate": "chrome"}
top = s.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
lid, uid = room["live_id"], room["uid"]

# 拿原始 URL（python dict 不改动它）
d = s.get("https://chatroom.inke.cn/url",
          params={"roomid": lid, "uid": uid, "id": lid, "access_from": "pc_web"},
          headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
ws_url = d["url"]  # 原样
print("原始 URL repr:", repr(ws_url))

# 把 wss 换成 https，path+query 原样保留
http_url = "https://" + ws_url[len("wss://"):]
key = base64.b64encode(os.urandom(16)).decode()
headers = {
    "Upgrade": "websocket", "Connection": "Upgrade",
    "Sec-WebSocket-Key": key, "Sec-WebSocket-Version": "13",
    "Origin": "https://www.inke.cn",
}
# 直接用原样 http_url，不经过任何 parse/重组
r = s.get(http_url, headers=headers, timeout=15, **KW)
print("status:", r.status_code, "| upgrade:", r.headers.get("upgrade"))
print("body:", r.text[:200])

# 对比：parse 重组后的 URL
from urllib.parse import urlparse, urlunparse
p = urlparse(http_url)
rebuilt = urlunparse(p)
print("\n原样 == 重组?", http_url == rebuilt)
if http_url != rebuilt:
    print("原样:", repr(http_url))
    print("重组:", repr(rebuilt))
