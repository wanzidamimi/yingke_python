# -*- coding: utf-8 -*-
"""验证 pure-live-core 揭示的映客 Web 端公开接口（仅学习研究，低频访问）。"""
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from curl_cffi import requests
    IMP = "curl_cffi"
    KW = {"impersonate": "chrome"}
except Exception:
    import requests
    IMP = "requests"
    KW = {}

BASE = "https://webapi.busi.inke.cn"
print("HTTP 实现:", IMP)


def get(path, params=None):
    url = BASE + path
    try:
        r = requests.get(url, params=params, timeout=15, **KW)
        print("\nGET", r.url)
        print("status", r.status_code, "len", len(r.content))
        return r.json()
    except Exception as e:
        print("ERR", path, repr(e))
        return None


# 1) 精选列表，拿一个真实房间的 uid + live_id
top = get("/web/Live_top_pc")
rooms = []
if top and top.get("error_code") == 0:
    rooms = top["data"]["list"]
    print("\n精选房间数:", len(rooms))
    for x in rooms[:3]:
        print("  uid=%s live_id=%s nick=%s" % (x.get("uid"), x.get("live_id"), x.get("nick")))

if not rooms:
    raise SystemExit("无房间数据")

uid = rooms[0]["uid"]
live_id = rooms[0]["live_id"]

# 2) live_share_pc：房间元数据，看是否含 ws / 弹幕地址
for params in ({"uid": uid}, {"uid": uid, "id": live_id}):
    d = get("/web/live_share_pc", params)
    if d:
        print("JSON:", json.dumps(d, ensure_ascii=False)[:1500])

# 3) 官网房间脚本里找 websocket 线索（另测）
