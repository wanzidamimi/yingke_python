# -*- coding: utf-8 -*-
"""诊断 WS 握手 invalid parameters：对比不同 HTTP 客户端拿 URL + 完整响应。仅学习研究。"""
import json
import sys
import io
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests as stdreq
from curl_cffi import requests as curlreq
import websocket

liveid, uid = "1795004103423719", "771687341"
params = {"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"}

def get_url(client, label):
    try:
        if label == "curl":
            r = client.get("https://chatroom.inke.cn/url", params=params,
                           headers={"Referer": "https://www.inke.cn/"}, timeout=15,
                           impersonate="chrome")
        else:
            r = client.get("https://chatroom.inke.cn/url", params=params,
                           headers={"Referer": "https://www.inke.cn/",
                                    "User-Agent": "Mozilla/5.0"}, timeout=15)
        d = r.json()
        print("%s: dm_error=%s url_len=%s" % (label, d.get("dm_error"), len(d.get("url", ""))))
        return d.get("url")
    except Exception as e:
        print("%s ERR: %s" % (label, repr(e)[:100]))
        return None

u1 = get_url(curlreq, "curl")
u2 = get_url(stdreq, "stdlib")

# 用 stdlib 拿的 URL 连（同出口）
for label, url in [("curl-url", u1), ("stdlib-url", u2)]:
    if not url:
        continue
    print("\n=== %s ===" % label)
    # 打印完整错误响应
    try:
        ws = websocket.create_connection(url, timeout=8)
        print("握手成功!")
        ws.close()
    except websocket.WebSocketBadStatusException as e:
        print("status:", getattr(e, "status_code", "?"))
        print("body:", getattr(e, "status_text", "?"))
        print("headers:", getattr(e, "resp_headers", None))
    except Exception as e:
        print("ERR:", repr(e)[:150])
