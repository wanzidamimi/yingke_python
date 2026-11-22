# -*- coding: utf-8 -*-
"""映客弹幕实时提取（已破解协议版）。

方案：映客弹幕走私有 TCP + RSA 加密（tech.appshatcher.comm.conn），
纯协议复刻成本极高。本模块采用 Frida 在 APP 端 hook
RoomMessageCenter.onMessage，直接拿解密后的明文 JSON 流。

两种运行方式：
  1) 推荐：run_live() —— Python 通过 frida device 通道 attach，RPC 拉消息队列。
  2) 兜底：parse_line() —— 解析 frida CLI 输出的 [FULL][MSG] 日志行。

协议（观察，映客 9.9.05）：
  外层: {"b":{"ev":"s.m"|"s.pb"},"liveid":"...","dest":N,"ms":[...],...}
  每条 ms[i]: {"tp":"<类型>", "c":"<显示文本>", "from":{"nic":"<昵称>",...}, ...}
  类型 tp: chat(聊天) / user_join_tip|color(进场) / usernu(人数)
           / gift_refine_sync_state(礼物) / doubleclickcount(点赞)
           / float_public_chat_v2(飘屏) / guard_seat_info_update 等
"""
import json
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PKG = "com.meelive.ingkee"
ADB = r"C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe"
DEVICE = "127.0.0.1:5555"
HOOK_JS = str(Path(__file__).parent / "reverse" / "hooks" / "rpc_full.js")

# tp -> (类别, 中文标签)
TP_MAP = {
    "chat": ("chat", "弹幕"),
    "user_join_tip": ("member", "进场"),
    "color": ("member", "进场"),
    "usernu": ("stats", "人数"),
    "gift_refine_sync_state": ("gift", "礼物"),
    "doubleclickcount": ("like", "点赞"),
    "float_public_chat_v2": ("notice", "飘屏"),
    "guard_seat_info_update": ("guard", "守护"),
    "c_room_hour_time_ranking": ("rank", "排行"),
    "sys": ("system", "系统"),
    "pub": ("notice", "公告"),
}

MSG_RE = re.compile(r"\[FULL\]\[MSG\]\s*\S+\s*\|\s*(\{.*\})")


def parse_payload(obj):
    """把一条外层 JSON 解析为标准化消息列表。"""
    out = []
    if not isinstance(obj, dict):
        return out
    liveid = obj.get("liveid", "")
    for item in obj.get("ms", []):
        if not isinstance(item, dict):
            continue
        tp = item.get("tp", "")
        cat, label = TP_MAP.get(tp, ("other", "其他"))
        data = item.get("data") if isinstance(item.get("data"), dict) else item
        # 昵称：from.nic 或 data.user.nick
        frm = data.get("from") if isinstance(data.get("from"), dict) else {}
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        nick = frm.get("nic") or user.get("nick") or ""
        # 文本：c / ct / content[].text
        text = data.get("c") or data.get("ct") or ""
        if not text and isinstance(data.get("content"), list):
            text = "".join(
                seg.get("text", "") for seg in data["content"]
                if isinstance(seg, dict)
            )
        # 人数消息没文本，给个可读描述
        if tp == "usernu":
            text = "在线 %s 人" % data.get("n", "?")
        if not text and not nick and cat == "other":
            continue  # 过滤纯字段噪声
        out.append({
            "kind": "danmu",
            "category": cat,
            "category_label": label,
            "message_type": tp,
            "user": nick,
            "content": text,
            "text": ("%s: %s" % (nick, text)) if nick and text else (text or nick),
            "liveid": liveid,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return out


def parse_line(line):
    """解析 frida CLI 的一行输出，返回消息列表。"""
    m = MSG_RE.search(line)
    if not m:
        return []
    try:
        obj = json.loads(m.group(1))
    except Exception:
        return []
    return parse_payload(obj)


def _adb_pid():
    r = subprocess.run([ADB, "-s", DEVICE, "shell", "pidof", PKG],
                       capture_output=True, text=True, timeout=10)
    for x in r.stdout.split():
        if x.strip().isdigit():
            return int(x)
    return None


def parse_room(raw):
    """从用户输入解析出 uid 和/或 liveid。

    支持：纯数字房间号、www.inke.cn/liveroom/index.html?uid=xxx、
    inke://...?uid=xxx&id=xxx、完整 URL。
    返回 (uid, liveid)，取不到则为 None。
    """
    raw = (raw or "").strip()
    uid = liveid = None
    m = re.search(r"\d{6,}", raw)
    if "?" in raw or "://" in raw:
        try:
            q = parse_qs(urlparse(raw).query)
            uid = (q.get("uid") or [None])[0]
            liveid = (q.get("id") or q.get("liveid") or [None])[0]
        except Exception:
            pass
    if m and not liveid:
        # 单个长数字：先当 uid 用（App 深链用 uid）
        uid = uid or m.group(0)
    return uid, liveid


def lookup_liveid(uid):
    """用 Web 公开接口 uid -> liveid（仅用于校验/过滤，不影响 hook）。"""
    if not uid:
        return None
    try:
        from curl_cffi import requests as creq
        d = creq.get("https://webapi.busi.inke.cn/web/live_share_pc",
                     params={"uid": uid}, impersonate="chrome", timeout=10).json()
        data = d.get("data") or {}
        if str(data.get("status")) == "1" and data.get("liveid"):
            return str(data["liveid"])
    except Exception:
        pass
    return None


def enter_room(uid):
    """通过 adb 深链尝试让模拟器里的映客进入目标主播房间。"""
    if not uid:
        return False
    for scheme in ("inke://room?uid=%s", "inke://live/?uid=%s", "inke://live?uid=%s"):
        try:
            subprocess.run(
                [ADB, "-s", DEVICE, "shell", "am", "start", "-a",
                 "android.intent.action.VIEW", "-d", scheme % uid],
                capture_output=True, text=True, timeout=10)
        except Exception:
            pass
    return True


class InkeDanmu:
    """基于 frida CLI 的实时弹幕采集：启动 frida 子进程，读 stdout 解析。"""

    def __init__(self, on_message=None, target_liveid=None):
        self.on_message = on_message
        self.target_liveid = str(target_liveid) if target_liveid else None
        self._proc = None
        self._running = False

    def start(self):
        pid = _adb_pid()
        if not pid:
            raise RuntimeError("未找到映客进程，请先在模拟器打开映客并进入直播间")
        cmd = ["frida", "-D", DEVICE, "-p", str(pid), "-l", HOOK_JS]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1)
        self._running = True
        threading.Thread(target=self._reader, daemon=True).start()
        return pid

    def _reader(self):
        while self._running and self._proc:
            line = self._proc.stdout.readline()
            if not line:
                break
            for msg in parse_line(line):
                # 指定目标房间时，只推送该房间的弹幕
                if self.target_liveid and msg.get("liveid") not in (None, "", self.target_liveid):
                    continue
                if self.on_message:
                    self.on_message(msg)

    def stop(self):
        self._running = False
        if self._proc:
            self._proc.terminate()
            self._proc = None

    @property
    def alive(self):
        return self._running and self._proc is not None and self._proc.poll() is None


if __name__ == "__main__":
    print("映客弹幕提取器（Frida hook 版）")
    print("前置：雷电模拟器已开 root、frida-server 运行、映客已进直播间")
    pid = _adb_pid()
    print("当前映客 PID:", pid)
    print("\n用 parse_line() 解析 frida 日志，或用 InkeDanmu().start() 启动实时采集。")
    # 自检：解析一条真实样本
    sample = ('[FULL][MSG] s.m | {"b":{"ev":"s.m"},"liveid":"1794976070509688",'
              '"ms":[{"tp":"chat","c":"大家好","from":{"nic":"测试用户"}}]}')
    parsed = parse_line(sample)
    print("\n自检解析:", json.dumps(parsed, ensure_ascii=False, indent=2))
    assert parsed and parsed[0]["user"] == "测试用户", "解析自检失败"
    print("SELFTEST PASS")
