# -*- coding: utf-8 -*-
"""Frida RPC 弹幕提取：spawn 模式启动 APP（对抗加固反调试），轮询拉取明文弹幕。"""
import json
import sys
import time

import frida

PKG = "com.meelive.ingkee"
SCRIPT = r"D:\Scrapy-project\yingke_python\reverse\hooks\rpc_full.js"


def on_message(msg, data):
    if msg.get("type") == "error":
        print("FRIDA ERR:", msg.get("stack") or msg.get("description"), flush=True)
    elif msg.get("type") == "send":
        print("JS:", msg.get("payload"), flush=True)


def get_device():
    # 用 adb 设备通道（与 frida-ps -D 127.0.0.1:5555 一致，PID 命名空间正确）
    return frida.get_device("127.0.0.1:5555", timeout=10)


def main():
    dev = get_device()
    print("device:", dev.id, flush=True)
    print("spawning", PKG, flush=True)
    pid = dev.spawn([PKG])
    session = dev.attach(pid)
    with open(SCRIPT, encoding="utf-8") as f:
        script = session.create_script(f.read())
    script.on("message", on_message)
    script.load()
    dev.resume(pid)
    print("pid", pid, "ping:", script.exports_sync.ping(), flush=True)
    print("WAIT: 请在模拟器里进入直播间；本脚本每 2s 拉取消息...", flush=True)

    try:
        while True:
            msgs = script.exports_sync.drain()
            for m in msgs:
                txt = m.get("data", "")
                try:
                    d = json.loads(txt)
                    tps = [x.get("tp") for x in d.get("ms", [])]
                    # 提取聊天内容
                    for item in d.get("ms", []):
                        if item.get("tp") == "chat":
                            c = item.get("data", {}) or item
                            print("[CHAT] %s: %s" % (
                                (c.get("u") or {}).get("nic", "?"),
                                c.get("c", "")), flush=True)
                    if tps and any(t != "usernu" for t in tps):
                        print("event=%s tp=%s liveid=%s" % (
                            m.get("event"), tps, d.get("liveid")), flush=True)
                except Exception:
                    pass
            if not msgs:
                sys.stdout.write(".")
                sys.stdout.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nstopped", flush=True)


if __name__ == "__main__":
    sys.exit(main())
