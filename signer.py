# -*- coding: utf-8 -*-
"""签名桥骨架：支持四种方案，由 config.SIGN_MODE 选择。

- none   : 占位，原样返回参数
- node   : 常驻 Node 进程，stdio JSON-RPC 调 node_env/sign.js（签名在 JS 层时）
- python : 按 reverse/rea_notes.md 的算法线索本地复刻
- frida  : 通过 Frida RPC 调 APP 内函数直接拿签名（so/Java 层，最省逆向成本）
"""
import json
import subprocess
import threading

import config


class BaseSigner:
    def sign(self, params: dict) -> dict:
        return dict(params)

    def close(self):
        pass


class NodeSigner(BaseSigner):
    """常驻 node 子进程；sign.js 从 stdin 读一行 JSON，stdout 回一行 JSON。"""

    def __init__(self, cmd=None):
        self.cmd = cmd or config.NODE_SIGN_CMD
        self._proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._lock = threading.Lock()

    def sign(self, params: dict) -> dict:
        with self._lock:
            self._proc.stdin.write(json.dumps(params, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline().strip()
        if not line:
            raise RuntimeError("node signer 无返回: " + self._proc.stderr.readline().strip())
        return json.loads(line)

    def close(self):
        try:
            self._proc.terminate()
        except OSError:
            pass


class PythonSigner(BaseSigner):
    """TODO: 按静态分析结论复刻签名算法。"""

    def sign(self, params: dict) -> dict:
        raise NotImplementedError("按 reverse/rea_notes.md 的签名线索实现")


class FridaSigner(BaseSigner):
    """TODO: 通过 frida-server + RPC 调用 APP 内签名函数。

    典型流程（阶段 2/3）：
      1. 真机/模拟器运行 frida-server
      2. attach config.FRIDA_PROCESS
      3. js 里 hook 目标方法，export rpc.exports.sign = ...
      4. 这里用 script.exports_sync.sign(params) 拿结果
    """

    def __init__(self):
        raise NotImplementedError("Frida RPC 桥待阶段 3 接入")


def make_signer(mode=None):
    mode = mode or config.SIGN_MODE
    return {
        "none": BaseSigner,
        "node": NodeSigner,
        "python": PythonSigner,
        "frida": FridaSigner,
    }[mode]()
