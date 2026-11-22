# -*- coding: utf-8 -*-
"""映客 APP 弹幕协议配置（占位骨架）。

阶段 1/2 完成后，把 REA 静态分析 + 抓包确认的结果填进来。
凡是 TODO 项当前都为空或 None，运行侧会以明确的 system 事件提示，而不是静默失败。
"""
import os

# ===== APP 身份（待 REA 从 Manifest / 抓包确认）=====
APP_PACKAGE = "com.inke.tv"          # TODO: 以实际 APK 为准
APP_VERSION = None                   # TODO: 抓包请求里的 appVersion
APP_BUILD = None                     # TODO: 渠道 / build 号

# ===== 接口域名（待抓包确认）=====
HTTP_BASE = None                     # TODO: 例 https://api.xxx.inke.cn
WS_URL_TEMPLATE = None               # TODO: 例 wss://xxx/im?roomId={room_id}&token={token}

# ===== 设备指纹（待抓包确认；APP 通常是固定 UA 或自定义头）=====
USER_AGENT = None                    # TODO: 抓包原样复制
EXTRA_HEADERS = {}                   # TODO: app 自定义头（如 X-App-Version / X-Device-Id）

# ===== 签名 / 鉴权 =====
# none   : 暂不签名（骨架默认，便于先打通链路）
# node   : 走 node_env/ 里的补环境脚本（签名在 JS 层时）
# frida  : 走 Frida RPC 直接拿 so/Java 的签名结果
# python : 按 rea_notes.md 的算法线索在 signer.py 复刻
SIGN_MODE = "none"

NODE_SIGN_CMD = [
    "node",
    os.path.join(os.path.dirname(__file__), "node_env", "sign.js"),
]

# Frida RPC 桥（可选）
FRIDA_DEVICE = "usb"                 # usb / remote:host:port
FRIDA_PROCESS = "com.inke.tv"        # TODO: 进程名

# ===== 连接参数 =====
PING_INTERVAL = 20                   # 心跳秒数，WS 时生效
CONNECT_TIMEOUT = 15
RECONNECT_DELAY = 3

# ===== 入口检查 =====
def missing():
    """返回尚未配置的关键项名称列表。"""
    keys = []
    for name in ("APP_VERSION", "HTTP_BASE", "WS_URL_TEMPLATE", "USER_AGENT"):
        if not globals().get(name):
            keys.append(name)
    return keys
