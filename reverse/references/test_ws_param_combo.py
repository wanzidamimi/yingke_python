# -*- coding: utf-8 -*-
"""穷举 /url 参数组合，找能握手成功的 URL。仅学习研究。"""
import sys, io, time, itertools
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
liveid, uid = room["live_id"], room["uid"]
print("liveid=%s uid=%s" % (liveid, uid))

# 穷举 roomid/id/uid 的取值组合
combos = [
    {"roomid": liveid, "id": liveid, "uid": uid},
    {"roomid": liveid, "id": liveid, "uid": liveid},
    {"roomid": uid, "id": uid, "uid": uid},
    {"roomid": liveid, "id": uid, "uid": uid},
    {"roomid": uid, "id": liveid, "uid": uid},
]
for c in combos:
    p = dict(c); p["access_from"] = "pc_web"
    try:
        d = requests.get("https://chatroom.inke.cn/url", params=p,
                         headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
        url = d.get("url", "")
        try:
            ws = websocket.create_connection(url, timeout=6)
            print("SUCCESS combo=%s" % c)
            ws.close()
            break
        except Exception as e:
            body = "invalid" if "invalid parameters" in str(e) else str(e)[:40]
            print("FAIL combo=%s -> %s" % (c, body))
    except Exception as e:
        print("ERR combo=%s %s" % (c, repr(e)[:60]))
