# -*- coding: utf-8 -*-
"""用 curl_cffi(Chrome TLS) 模拟 WS 升级握手，判断是否是 TLS 指纹问题。仅学习研究。"""
import base64, os, sys, io
from urllib.parse import urlparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
KW = {"impersonate": "chrome"}

# 1) 拿 WS URL（Chrome TLS）
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
lid, uid = room["live_id"], room["uid"]
d = requests.get("https://chatroom.inke.cn/url",
                 params={"roomid": lid, "uid": uid, "id": lid, "access_from": "pc_web"},
                 headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
ws_url = d["url"]
p = urlparse(ws_url)
path = p.path + ("?" + p.query if p.query else "")
key = base64.b64encode(os.urandom(16)).decode()

# 2) 用 Chrome TLS 发 WS 升级请求
headers = {
    "Host": p.netloc,
    "Upgrade": "websocket",
    "Connection": "Upgrade",
    "Sec-WebSocket-Key": key,
    "Sec-WebSocket-Version": "13",
    "Origin": "https://www.inke.cn",
    "Referer": "https://www.inke.cn/",
}
print("WS URL:", ws_url[:180])
print("\n发升级请求 (Chrome TLS)...")
r = requests.get("https://" + p.netloc + path, headers=headers, timeout=15, **KW)
print("status:", r.status_code)
print("headers:", dict(r.headers))
print("body:", r.text[:300])
