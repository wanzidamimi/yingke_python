# -*- coding: utf-8 -*-
"""弹幕长连接客户端骨架（WS 直连；私有 TCP/长轮询时替换 transport）。

对外契约与 douyin_python 一致：run_sync(room, on_message, duration, on_client)。
未配置接口时不静默失败，而是通过 on_message 发 system 事件说明下一步。
"""
import asyncio
import time

import config
from category import classify
from decoder import decode_frame, to_message
from http_client import build_ws_url, enter_room, get_session
from signer import make_signer


class DanmuClient:
    def __init__(self, on_message):
        self.on_message = on_message
        self.running = True
        self._seq = 0

    def _emit(self, event):
        if self.on_message:
            self.on_message(event)

    def _handle_frame(self, frame, message_type=None):
        for item in decode_frame(frame):
            msg = to_message(item, self._seq)
            self._seq += 1
            msg.update(classify(message_type, msg.get("text", "")))
            self._emit(msg)

    async def run(self, room, duration=None):
        missing = config.missing()
        if missing:
            self._emit({
                "kind": "system",
                "text": "接口未配置，缺少: " + ", ".join(missing) +
                        "。请先按 reverse/README.md 完成阶段 1/2，把结果填进 config.py。",
            })
            self.running = False
            return

        signer = make_signer()
        session = get_session()
        try:
            params = enter_room(session, room)
            params = signer.sign(params)
            url = build_ws_url(room, params)
            if not url:
                self._emit({"kind": "error", "text": "WS_URL_TEMPLATE 为空，无法连接"})
                return
            self._emit({"kind": "system", "text": "连接: " + url.split("?")[0]})
            # 阶段 3：用 websockets.connect(url, extra_headers=..., ping_interval=...) 逐帧接收
            # 这里保留 skeleton 结构，避免引入未确认协议的假实现。
            import websockets
            async with websockets.connect(
                url,
                extra_headers=dict(session.headers),
                ping_interval=config.PING_INTERVAL,
                open_timeout=config.CONNECT_TIMEOUT,
            ) as ws:
                self._emit({"kind": "system", "text": "WebSocket 已握手 (101)"})
                start = time.time()
                async for frame in ws:
                    if not self.running:
                        break
                    if duration and time.time() - start > duration:
                        break
                    if isinstance(frame, str):
                        frame = frame.encode("utf-8")
                    self._handle_frame(frame)
        except ImportError:
            self._emit({"kind": "error", "text": "缺少依赖，先运行 pip install -r requirements.txt"})
        except Exception as exc:
            self._emit({"kind": "error", "text": f"连接异常: {exc}"})
        finally:
            signer.close()
            session.close()
            self.running = False


def run_sync(room, on_message, duration=None, on_client=None):
    """同步入口：app.py 在线程里调用。"""
    client = DanmuClient(on_message)
    if on_client:
        on_client(client)
    asyncio.run(client.run(room, duration=duration))
