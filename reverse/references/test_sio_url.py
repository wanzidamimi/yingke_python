# -*- coding: utf-8 -*-
"""按 pure-live-core 源码：live_share_pc?uid= 的 data.sio_url 就是 WS 地址。仅学习研究。"""
import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
uid = room["uid"]
print("主播 uid=%s nick=%s" % (uid, room.get("nick")))

# 关键：pure-live-core 用 uid 调 live_share_pc，取 data.sio_url
d = requests.get("https://webapi.busi.inke.cn/web/live_share_pc",
                 params={"uid": uid}, timeout=15, **KW).json()
print("error_code=%s" % d.get("error_code"))
data = d.get("data", {})
print("返回字段:", list(data.keys()))

sio = data.get("sio_url")
print("sio_url:", sio)
if not sio:
    print("无 sio_url，完整 data:", json.dumps(data, ensure_ascii=False)[:2000])
    raise SystemExit(0)

# 直连 sio_url
print("\n直连 sio_url 收 25 秒...")
ws = websocket.create_connection(sio, timeout=10)
ws.settimeout(5)
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
        # 兼容 sio 的 socket.io 帧格式：可能是 42["...",{...}]
        payload = obj
        if isinstance(raw, str) and raw.startswith("42"):
            try:
                payload = json.loads(raw[2:])[1]
            except Exception:
                pass
        ev = payload.get("b", {}).get("ev", "?") if isinstance(payload, dict) else "?"
        ms = payload.get("ms", []) if isinstance(payload, dict) else []
        tps = [m.get("tp", "?") for m in ms if isinstance(m, dict)]
        for t in tps:
            types[t] = types.get(t, 0) + 1
        for m in ms:
            if isinstance(m, dict) and m.get("tp") == "pub":
                for st in m.get("statement_info", []):
                    print("[弹幕] %s" % st.get("c", ""))[:200]
    except Exception as e:
        if "timed out" in str(e).lower():
            continue
        print("recv err:", repr(e)[:100])
        break
ws.close()
print("\n总消息数:", count)
print("类型统计:", types)
