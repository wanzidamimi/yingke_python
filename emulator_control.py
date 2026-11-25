# -*- coding: utf-8 -*-
"""本地雷电模拟器控制：唤醒、解锁、启动映客、截图。

只操作当前测试机上的模拟器，不涉及账号凭据。
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).parent
SHOT = ROOT / "logs" / "emulator_latest.png"
ADB_SERIAL = "emulator-5554"
LDPLAYER = r"D:\leidian\LDPlayer9\dnplayer.exe"
PKG = "com.meelive.ingkee"


def _adb(args, timeout=10):
    adb = shutil.which("adb")
    if not adb:
        adb = r"C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    cmd = [adb, "-s", ADB_SERIAL] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def device_online():
    try:
        proc = _adb(["devices"], timeout=5)
        return ADB_SERIAL in proc.stdout
    except Exception:
        return False


def ensure_emulator():
    if device_online():
        return True
    if Path(LDPLAYER).exists():
        subprocess.Popen([LDPLAYER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(1)
        if device_online():
            return True
    return False


def save_screenshot(path=SHOT):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    adb = shutil.which("adb") or r"C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe"
    data = subprocess.check_output(
        [adb, "-s", ADB_SERIAL, "exec-out", "screencap", "-p"],
        timeout=10,
    )
    with open(path, "wb") as f:
        f.write(data)
    return Path(path)


def wake_and_launch(pin=None):
    """唤醒、必要时解锁 PIN，然后启动映客。

    pin 只从请求临时传入，不落盘、不保存。
    """
    if not ensure_emulator():
        return {
            "ok": False,
            "error": "模拟器未在线，且无法自动启动",
        }

    steps = []
    wake = _adb(["shell", "input", "keyevent", "224"])
    steps.append("wake")
    time.sleep(1)

    # 如果传了 PIN，尝试解锁；不传则不触碰密码输入。
    if pin:
        try:
            _adb(["shell", "input", "keyevent", "82"])
            time.sleep(1)
            _adb(["shell", "input", "text", str(pin)])
            _adb(["shell", "input", "keyevent", "66"])
            steps.append("unlock")
            time.sleep(1)
        except Exception:
            steps.append("unlock_failed")

    _adb(["shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1"])
    steps.append("launch_app")
    time.sleep(6)

    focus = ""
    try:
        proc = _adb(["shell", "dumpsys", "window"], timeout=8)
        for line in proc.stdout.splitlines():
            if "mCurrentFocus" in line:
                focus = line.strip()
                break
    except Exception:
        pass

    shot = save_screenshot()
    return {
        "ok": True,
        "steps": steps,
        "focus": focus,
        "screenshot": "/api/emulator/screenshot",
        "screenshot_path": str(shot),
        "note": "已唤醒并启动映客；登录态请从截图确认。若停在登录页，请在模拟器内手动登录。",
    }
