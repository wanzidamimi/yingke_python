# -*- coding: utf-8 -*-
"""找 getSoketUrl 函数定义，看 /url 请求构造和签名。"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests
KW = {"impersonate": "chrome"}
js = requests.get("https://webcdn.inke.cn/www.inke.cn.live/static/js/liveroom.www.a6740050e.chunk.js",
                  timeout=20, **KW).text

# getSoketUrl 定义：找 "getSoketUrl:" 或 "getSoketUrl=function" 或 "getSoketUrl(e"
for pat in [r'getSoketUrl["\']?\s*[=:]', r'getSoketUrl:function', r'getSoketUrl\s*\(', r'"getSoketUrl"']:
    print("\n=== PAT", pat, "===")
    for m in list(re.finditer(pat, js))[:8]:
        i = m.start()
        print("--- at", i, "---")
        print(js[max(0, i-200):i+700].replace("\n", " ")[:900])
