# -*- coding: utf-8 -*-
"""消息解码骨架。

映客弹幕协议未确认前，提供两层能力：
  1. decode_frame: 处理外层 envelope（gzip / 长度前缀 / protobuf wire 通用递归）
  2. to_message: 把解析出的字段归一化为运行侧统一消息 dict

阶段 2 拿到真实二进制样本后，优先用精确 schema；
没有 schema 时沿用 douyin_python/dyproto/decoder.py 的 wire 递归思路。
"""
import gzip
import struct


def _read_varint(data, i):
    shift = 0
    val = 0
    while i < len(data) and shift < 70:
        b = data[i]
        i += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, i
        shift += 7
    raise ValueError("varint 越界")


def wire_fields(data):
    """通用 protobuf wire 递归：返回 [(field_no, wire_type, value)]。"""
    out = []
    i = 0
    while i < len(data):
        try:
            key, i = _read_varint(data, i)
        except ValueError:
            break
        field_no, wt = key >> 3, key & 0x07
        if field_no == 0:
            break
        if wt == 0:
            v, i = _read_varint(data, i)
            out.append((field_no, wt, v))
        elif wt == 1:
            v = data[i:i + 8]
            i += 8
            out.append((field_no, wt, v))
        elif wt == 2:
            n, i = _read_varint(data, i)
            v = data[i:i + n]
            i += n
            out.append((field_no, wt, v))
        elif wt == 5:
            v = data[i:i + 4]
            i += 4
            out.append((field_no, wt, v))
        else:
            break
    return out


def _try_gzip(data):
    try:
        return gzip.decompress(data)
    except (OSError, EOFError):
        return data


def decode_frame(frame: bytes):
    """输入一帧 bytes，输出归一化消息 dict 列表。骨架阶段尽力而为。"""
    if not frame:
        return []
    data = _try_gzip(frame)
    msgs = []
    try:
        fields = wire_fields(data)
    except Exception:
        fields = []
    for no, wt, val in fields:
        if wt == 2 and isinstance(val, bytes):
            text = None
            try:
                text = val.decode("utf-8")
            except UnicodeDecodeError:
                pass
            if text is not None:
                msgs.append({"field": no, "text": text, "raw_len": len(val)})
    if not msgs:
        msgs.append({"field": 0, "text": repr(data[:120]), "raw_len": len(data), "binary": True})
    return msgs


def to_message(decoded: dict, seq=0):
    """把 decode_frame 的一条结果转成统一消息结构。"""
    return {
        "kind": "danmu" if not decoded.get("binary") else "binary",
        "seq": seq,
        "ts": None,
        "message_type": None,
        "user": "",
        "content": decoded.get("text", ""),
        "text": decoded.get("text", ""),
    }
