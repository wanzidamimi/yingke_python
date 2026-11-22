# -*- coding: utf-8 -*-
"""红绿测试：验证映客 Web 端直播间链路是否真的可用。
GREEN = 该项能力可用（拿到预期成功证据）
RED   = 该项能力不可用（拿到明确失败证据）
每项都打印实际响应，结论只基于实测数据。仅学习研究。
"""
import sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests

KW = {"impersonate": "chrome"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
HDR = {"User-Agent": UA}

def green(name, evidence):
    print("  [GREEN] %s -> %s" % (name, evidence))

def red(name, evidence):
    print("  [RED]   %s -> %s" % (name, evidence))

print("=" * 70)
print("组 A：HTTP API 层（Web 前端依赖的接口）")
print("=" * 70)

# A1 精选列表
r = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", headers=HDR, timeout=15, **KW)
try:
    d = r.json()
    n = len((d.get("data") or {}).get("list") or [])
    if r.status_code == 200 and d.get("error_code") == 0 and n > 0:
        green("A1 Live_top_pc", "HTTP %d, error_code=%d, 在线房间数=%d" % (r.status_code, d.get("error_code"), n))
        room = d["data"]["list"][0]
        print("         样本: uid=%s live_id=%s" % (room.get("uid"), room.get("live_id")))
    else:
        red("A1 Live_top_pc", "HTTP %d, body=%s" % (r.status_code, r.text[:200]))
except Exception as e:
    red("A1 Live_top_pc", "解析失败 %s body=%s" % (repr(e)[:80], r.text[:200]))

# A2 房间详情
uid = str(room.get("uid")) if 'room' in dir() else "771687341"
r2 = requests.get("https://webapi.busi.inke.cn/web/live_share_pc", params={"uid": uid},
                  headers=HDR, timeout=15, **KW)
try:
    d2 = r2.json()
    data = d2.get("data") or {}
    if r2.status_code == 200 and d2.get("error_code") == 0 and str(data.get("status")) == "1":
        green("A2 live_share_pc", "HTTP %d, status=%s, liveid=%s, live_name=%s" % (
            r2.status_code, data.get("status"), data.get("liveid"), data.get("live_name")))
    else:
        red("A2 live_share_pc", "HTTP %d, error_code=%s, status=%s" % (
            r2.status_code, d2.get("error_code"), data.get("status")))
except Exception as e:
    red("A2 live_share_pc", "解析失败 %s body=%s" % (repr(e)[:80], r2.text[:200]))

# A3 推流地址是否存在（Web 播放器的关键：能否拿到视频流）
flv = (data.get("live_addr") or [{}])[0].get("stream_addr") if data else None
if flv:
    green("A3 推流地址", "live_addr.stream_addr 存在")
else:
    red("A3 推流地址", "live_share_pc 无 live_addr 字段（Web 播放器可能拿不到流）")

# A4 chatroom /url
r3 = requests.get("https://chatroom.inke.cn/url",
                  params={"roomid": data.get("liveid"), "uid": uid, "id": data.get("liveid"), "access_from": "pc_web"},
                  headers={**HDR, "Referer": "https://www.inke.cn/"}, timeout=15, **KW)
try:
    d3 = r3.json()
    url = d3.get("url", "")
    if d3.get("dm_error") == 0 and url.startswith("wss://"):
        green("A4 chatroom/url", "dm_error=0, 返回 wss URL(长度%d)" % len(url))
    else:
        red("A4 chatroom/url", "dm_error=%s body=%s" % (d3.get("dm_error"), r3.text[:200]))
except Exception as e:
    red("A4 chatroom/url", "解析失败 %s body=%s" % (repr(e)[:80], r3.text[:200]))

print()
print("=" * 70)
print("组 B：Web 首页 / 房间页 HTML 层")
print("=" * 70)

# B1 首页是否含直播入口
r4 = requests.get("https://www.inke.cn/", headers=HDR, timeout=15, **KW)
html = r4.text
print("  首页 HTTP %d, HTML 长度 %d" % (r4.status_code, len(html)))
if re.search(r'liveroom|live\.php|/live/', html, re.I):
    green("B1 首页直播入口", "HTML 含 liveroom/live 链接")
else:
    red("B1 首页直播入口", "HTML 无直播入口链接（可能是纯下载页/SPA）")
# 找下载引导
if re.search(r'下载.*APP|APP.*下载|apk|appstore', html, re.I):
    print("         首页含“下载APP”引导文案")

# B2 房间页 HTML
r5 = requests.get("https://www.inke.cn/liveroom/index.html?uid=%s" % uid, headers=HDR, timeout=15, **KW)
room_html = r5.text
print("  房间页 HTTP %d, HTML 长度 %d" % (r5.status_code, len(room_html)))
if re.search(r'<video|video-js|hls\.js|liveroom', room_html, re.I):
    green("B2 房间页结构", "HTML 含 video/liveroom 相关标记")
else:
    red("B2 房间页结构", "HTML 无 video/liveroom 标记")

print()
print("=" * 70)
print("结论依据：以上 GREEN/RED 均为实测响应，未做任何假设")
print("=" * 70)
