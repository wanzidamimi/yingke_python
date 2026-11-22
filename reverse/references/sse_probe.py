# -*- coding: utf-8 -*-
"""读取 Web SSE 事件若干秒，验证端到端弹幕链路。"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

r = requests.get("http://127.0.0.1:8801/api/events", stream=True, timeout=30)
print("SSE status", r.status_code)
end = time.time() + 18
for line in r.iter_lines(decode_unicode=True):
    if time.time() > end:
        break
    if line and line.startswith("data: "):
        print("EVENT:", line[6:][:400])
