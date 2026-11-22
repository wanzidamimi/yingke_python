# -*- coding: utf-8 -*-
"""终极验证：纯 Python 直连映客 WebSocket 收弹幕。仅学习研究。"""
import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}

# 1) 在线房间 -> WS URL
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
liveid, uid = room["live_id"], room["uid"]
print("房间: liveid=%s nick=%s" % (liveid, room.get("nick")))

params = {"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"}
HDR = {"Referer": "https://www.inke.cn/", "Origin": "https://www.inke.cn"}
d = requests.get("https://chatroom.inke.cn/url", params=params, headers=HDR, timeout=15, **KW).json()
ws_url = d["url"]
print("WS URL:", ws_url[:200], "...")

# 2) 尝试多种 header 组合握手
combos = [
    ("no-header", None),
    ("origin-chatroom", ["Origin: https://chatroom.inke.cn", "Referer: https://chatroom.inke.cn/"]),
    ("origin-inke", ["Origin: https://www.inke.cn", "Referer: https://www.inke.cn/"]),
    ("ua", ["User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Origin: https://www.inke.cn"]),
]
ws = None
for name, hdr in combos:
    try:
        kw = {"timeout": 10}
        if hdr:
            kw["header"] = hdr
        w = websocket.create_connection(ws_url, **kw)
        print("握手成功:", name)
        ws = w
        break
    except Exception as e:
        print("握手失败 [%s]: %s" % (name, repr(e)[:120]))
if not ws:
    raise SystemExit("全部握手失败")

# 3) 收消息
ws.settimeout(5)
print("\n收 25 秒消息...\n")
end = time.time() + 25
count = 0
types = {}
while time.time() < end:
    try:
        raw = ws.recv()
        if not raw:
            continue
        obj = json.loads(raw)
        count += 1
        ev = obj.get("b", {}).get("ev", "?")
        ms = obj.get("ms", [])
        tps = [m.get("tp", "?") for m in ms if isinstance(m, dict)]
        for t in tps:
            types[t] = types.get(t, 0) + 1
        for m in ms:
            if isinstance(m, dict) and m.get("tp") in ("chat", "pub", "comment"):
                frm = m.get("from", {})
                s = "[弹幕] %s: %s" % (frm.get("nic", "?"), m.get("c", ""))
                print(s[:200])
    except Exception as e:
        if "timed out" in str(e).lower():
            continue
        print("recv err:", repr(e)[:100])
        break
ws.close()
print("\n总消息数:", count)
print("类型统计:", types)
