# -*- coding: utf-8 -*-
"""关键测试：同一 curl_cffi Session 拿 URL + 发 WS 升级（模拟浏览器会话）。仅学习研究。"""
import base64, os, sys, io
from urllib.parse import urlparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests

s = requests.Session()
KW = {"impersonate": "chrome"}

# 1) 先用同一 session 访问房间页 + 精选 + url
top = s.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
lid, uid = room["live_id"], room["uid"]
s.get("https://www.inke.cn/liveroom/index.html?uid=%s" % uid, timeout=15, **KW)
d = s.get("https://chatroom.inke.cn/url",
          params={"roomid": lid, "uid": uid, "id": lid, "access_from": "pc_web"},
          headers={"Referer": "https://www.inke.cn/liveroom/index.html?uid=%s" % uid},
          timeout=15, **KW).json()
ws_url = d["url"]
p = urlparse(ws_url)
path = p.path + ("?" + p.query if p.query else "")
key = base64.b64encode(os.urandom(16)).decode()
print("session cookies:", dict(s.cookies))
print("WS:", ws_url[:170])

# 2) 同一 session 发升级请求（保持 cookie + chrome TLS）
headers = {
    "Upgrade": "websocket", "Connection": "Upgrade",
    "Sec-WebSocket-Key": key, "Sec-WebSocket-Version": "13",
    "Origin": "https://www.inke.cn",
    "Referer": "https://www.inke.cn/liveroom/index.html?uid=%s" % uid,
}
r = s.get("https://" + p.netloc + path, headers=headers, timeout=15, **KW)
print("\nstatus:", r.status_code)
print("upgrade header:", r.headers.get("upgrade"), "| connection:", r.headers.get("connection"))
print("sec-ws-accept:", r.headers.get("sec-websocket-accept"))
print("body:", r.text[:200])
