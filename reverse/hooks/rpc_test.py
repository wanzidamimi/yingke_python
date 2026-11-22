# -*- coding: utf-8 -*-
"""验证 Frida RPC 弹幕通道：attach -> 加载脚本 -> 进直播间 -> 轮询拉消息。"""
import json
import sys
import time

import frida

HOST = "127.0.0.1:27042"
SCRIPT = r"D:\Scrapy-project\yingke_python\reverse\hooks\rpc_full.js"
PKG = "com.meelive.ingkee"


def on_message(msg, data):
    if msg.get("type") == "error":
        print("FRIDA ERROR:", msg.get("stack") or msg.get("description"))


def main():
    # 用 adb 设备通道（PID 命名空间与 frida-ps -D 一致）
    dev = frida.get_device("127.0.0.1:5555", timeout=10)
    print("device:", dev.id)
    # PID 用 adb pidof（frida 枚举时进程名是中文乱码）
    import subprocess
    target = None
    try:
        adb = r"C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe"
        r = subprocess.run([adb, "-s", "127.0.0.1:5555", "shell", "pidof", PKG],
                           capture_output=True, text=True, timeout=10)
        ids = [x for x in r.stdout.split() if x.strip().isdigit()]
        if ids:
            target = int(ids[0])
    except Exception as e:
        print("pidof err", e)
    if not target:
        print("未找到进程", PKG)
        return 1
    print("attach pid", target)
    session = dev.attach(target)
    with open(SCRIPT, encoding="utf-8") as f:
        src = f.read()
    script = session.create_script(src, runtime="v8")
    script.on("message", on_message)
    script.load()
    api = script.exports_sync
    print("ping:", api.ping())
    print("等待弹幕，按 Ctrl+C 停止；每 2 秒拉取一次...")
    try:
        while True:
            msgs = api.drain()
            for m in msgs:
                txt = m.get("data", "")
                # 只打印含 tp 的消息摘要
                try:
                    d = json.loads(txt)
                    tps = [x.get("tp") for x in d.get("ms", [])]
                    print("event=%s tp=%s liveid=%s" % (
                        m.get("event"), tps, d.get("liveid")))
                except Exception:
                    print("event=%s raw=%s" % (m.get("event"), str(txt)[:80]))
            if not msgs:
                sys.stdout.write(".")
                sys.stdout.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
