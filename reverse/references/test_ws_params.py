# -*- coding: utf-8 -*-
"""逐个删除 WS URL 参数，找握手必需参数。仅学习研究。"""
import sys, io, time
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
liveid, uid = room["live_id"], room["uid"]
d = requests.get("https://chatroom.inke.cn/url",
                 params={"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"},
                 headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
raw = d["url"]
p = urlparse(raw)
q = parse_qsl(p.query, keep_blank_values=True)
print("参数:", [k for k, v in q])

# 逐个删除测试
for drop in ["sec", "nonce", "time", "token", "sid", "session", "xrealip", "place", "access_from"]:
    q2 = [(k, v) for k, v in q if k != drop]
    u = urlunparse(p._replace(query=urlencode(q2)))
    try:
        w = websocket.create_connection(u, timeout=6)
        print("SUCCESS drop=%s" % drop)
        w.close()
    except Exception as e:
        s = str(e)
        status = "invalid params" if "invalid parameters" in s else ("200" if "200" in s else s[:50])
        print("FAIL drop=%-12s %s" % (drop, status))
