import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import video_stream


class VideoStreamTest(unittest.TestCase):
    def test_find_stream_addr_by_liveid(self):
        rooms = [
            {"live_id": "111", "uid": "1", "stream_addr": "https://a/%s.flv" % "111"},
            {"live_id": "222", "uid": "2", "stream_addr": "https://a/%s.flv" % "222"},
        ]
        self.assertEqual(
            video_stream.find_stream_addr("222", rooms=rooms),
            "https://a/222.flv",
        )

    def test_is_allowed_stream_host(self):
        self.assertTrue(video_stream.is_allowed_stream_host(
            "https://live-pull-ws.ikstatic.cn/live/x.flv?token=1"
        ))
        self.assertFalse(video_stream.is_allowed_stream_host(
            "https://evil.example.com/live/x.flv"
        ))
        self.assertFalse(video_stream.is_allowed_stream_host(
            "file:///etc/passwd"
        ))

    def test_iter_upstream_stream_uses_streaming_get(self):
        class FakeResponse:
            def __init__(self):
                self.closed = False
                self.kwargs = None

            def iter_content(self, chunk_size):
                assert chunk_size == 4
                yield b"FLV1"
                yield b"FLV2"

            def close(self):
                self.closed = True

        fake = FakeResponse()
        old_get = video_stream.creq.get
        captured = {}

        def fake_get(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return fake

        video_stream.creq.get = fake_get
        try:
            chunks = list(video_stream.iter_upstream_stream(
                "https://live-pull-ws.ikstatic.cn/live/x.flv",
                chunk_size=4,
            ))
            self.assertEqual(chunks, [b"FLV1", b"FLV2"])
            self.assertTrue(captured["kwargs"]["stream"])
            self.assertTrue(fake.closed)
        finally:
            video_stream.creq.get = old_get

    def test_resolve_stream_addr_refreshes_after_ttl(self):
        old_fetch = video_stream.fetch_hot_rooms_raw
        video_stream.stream_cache.clear()
        video_stream.fetch_hot_rooms_raw = lambda: [
            {"live_id": "333", "stream_addr": "https://live-pull-ws.ikstatic.cn/old.flv"}
        ]
        try:
            first = video_stream.resolve_stream_addr("333", now=1000, ttl=300)
            self.assertIn("old.flv", first)

            video_stream.fetch_hot_rooms_raw = lambda: [
                {"live_id": "333", "stream_addr": "https://live-pull-ws.ikstatic.cn/new.flv"}
            ]
            cached = video_stream.resolve_stream_addr("333", now=1200, ttl=300)
            self.assertIn("old.flv", cached)

            refreshed = video_stream.resolve_stream_addr("333", now=1400, ttl=300)
            self.assertIn("new.flv", refreshed)
        finally:
            video_stream.fetch_hot_rooms_raw = old_fetch
            video_stream.stream_cache.clear()


if __name__ == "__main__":
    unittest.main()
