# -*- coding: utf-8 -*-
"""实测 chatroom.inke.cn/url 拿 WebSocket 弹幕地址（仅学习研究，低频访问）。"""
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
KW = {"impersonate": "chrome"}

# 1) 先拿一个在线房间
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
liveid = room["live_id"]
uid = room["uid"]
print("房间: liveid=%s uid=%s nick=%s" % (liveid, uid, room.get("nick")))

# 2) 调 getSoketUrl（注意返回格式 codeKey=dm_error）
params = {"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"}
headers = {"Referer": "https://www.inke.cn/", "Origin": "https://www.inke.cn"}
r = requests.get("https://chatroom.inke.cn/url", params=params, headers=headers, timeout=15, **KW)
print("\nGET", r.url)
print("status", r.status_code, "len", len(r.content))
print("body:", r.text[:1200])
