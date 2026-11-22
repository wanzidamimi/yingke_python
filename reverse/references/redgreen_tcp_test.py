# -*- coding: utf-8 -*-
"""红绿测试：App 私有 TCP 网关是否可从本机直连（纯接口可行性前提）。仅学习研究。"""
import sys, io, socket
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 从模拟器 connection.xml 提取到的网关
gateways = ["111.13.223.167:1300", "47.95.96.98:1300", "111.13.223.188:1300"]

def green(n, e): print("  [GREEN] %s -> %s" % (n, e))
def red(n, e): print("  [RED]   %s -> %s" % (n, e))

for gw in gateways:
    host, port = gw.split(":")
    port = int(port)
    try:
        s = socket.create_connection((host, port), timeout=6)
        green("TCP 连通 " + gw, "连接成功 peer=%s" % (s.getpeername(),))
        # 尝试读 banner/握手响应
        s.settimeout(3)
        try:
            data = s.recv(128)
            print("         初始数据: %r" % data[:64])
        except Exception:
            print("         连接后无初始数据（等待客户端先发）")
        s.close()
    except Exception as e:
        red("TCP 连通 " + gw, repr(e)[:90])

# 对照：Web 网关 443（已知通）
try:
    s = socket.create_connection(("chatroom.inke.cn", 443), timeout=6)
    green("对照 chatroom.inke.cn:443", "连接成功")
    s.close()
except Exception as e:
    red("对照 chatroom.inke.cn:443", repr(e)[:90])
