# -*- coding: utf-8 -*-
"""不依赖网络的骨架自检：签名占位 / 解码 / 分类 / CSV 导出。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import category
import decoder
from recorder import SessionRecorder
from signer import make_signer


def check(cond, label):
    assert cond, "FAIL: " + label
    print("ok:", label)


def main():
    # 配置缺失检测
    check(isinstance(config.missing(), list), "config.missing() 返回列表")

    # 签名占位
    s = make_signer("none")
    check(s.sign({"a": 1}) == {"a": 1}, "BaseSigner 原样返回")

    # wire 解码 + gzip
    payload = b"\x0a\x05hello"
    fields = decoder.wire_fields(payload)
    check(any(f[0] == 1 and f[2] == b"hello" for f in fields), "varint/wire 解析")
    msgs = decoder.decode_frame(payload)
    check(any("hello" in m.get("text", "") for m in msgs), "decode_frame 文本提取")

    # 分类
    c = category.classify("", "感谢赠送的礼物")
    check(c["category"] == "gift", "分类: 礼物")

    # CSV 导出
    with tempfile.TemporaryDirectory() as d:
        rec = SessionRecorder(export_dir=d)
        rec.begin("test_room")
        rec.add({"kind": "danmu", "text": "你好", "seq": 1})
        p = rec.save()
        check(p is not None and p.exists(), "CSV 导出")
        check(len(SessionRecorder.list_files(export_dir=d)) == 1, "历史列表")
        check(SessionRecorder.path_for("../evil.csv", export_dir=d) is None, "目录穿越防护")

    print("\nSELFTEST PASS")


if __name__ == "__main__":
    main()
