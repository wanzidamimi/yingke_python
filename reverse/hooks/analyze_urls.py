# -*- coding: utf-8 -*-
"""分析 hook 日志里抓到的 URL，提取唯一域名+路径。"""
import re
import sys
from urllib.parse import urlparse

path = sys.argv[1] if len(sys.argv) > 1 else r"reverse/hooks/probe_http1.log"
s = open(path, encoding="utf-8", errors="ignore").read()
urls = re.findall(r"url=(https?://[^\s,}\"]+)", s)
print("原始 URL 条数:", len(urls))

doms = {}
for u in urls:
    p = urlparse(u)
    key = p.netloc + p.path
    doms[key] = doms.get(key, 0) + 1

print("\n=== 唯一域名+路径（按次数排序）===")
for k, v in sorted(doms.items(), key=lambda x: -x[1]):
    print("%2d  %s" % (v, k))
