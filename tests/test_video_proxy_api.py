import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app as app_module
import video_stream


class VideoProxyApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)

    def test_missing_liveid(self):
        r = self.client.get("/api/video/stream")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["ok"])

    def test_video_check_endpoint(self):
        old_resolve = app_module.resolve_stream_addr
        app_module.resolve_stream_addr = lambda liveid, force=False: (
            "https://live-pull-ws.ikstatic.cn/live/%s.flv" % liveid
        )
        try:
            r = self.client.get("/api/video/check?liveid=123")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["content_type"], "video/x-flv")
        finally:
            app_module.resolve_stream_addr = old_resolve

    def test_video_check_reports_no_stream(self):
        old_resolve = app_module.resolve_stream_addr
        app_module.resolve_stream_addr = lambda liveid, force=False: ""
        try:
            r = self.client.get("/api/video/check?liveid=123")
            data = r.json()
            self.assertFalse(data["ok"])
            self.assertEqual(data["error"], "该直播间暂无可播放画面")
        finally:
            app_module.resolve_stream_addr = old_resolve

    def test_stream_proxy(self):
        old_resolve = app_module.resolve_stream_addr
        old_iter = app_module.iter_upstream_stream
        app_module.resolve_stream_addr = lambda liveid, force=False: (
            "https://live-pull-ws.ikstatic.cn/live/%s.flv?token=1" % liveid
        )
        app_module.iter_upstream_stream = lambda url: iter([b"FLV1", b"FLV2"])
        try:
            r = self.client.get("/api/video/stream?liveid=123")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers["content-type"].split(";")[0], "video/x-flv")
            self.assertEqual(r.content, b"FLV1FLV2")
        finally:
            app_module.resolve_stream_addr = old_resolve
            app_module.iter_upstream_stream = old_iter

    def test_disallowed_host_is_blocked(self):
        old_resolve = app_module.resolve_stream_addr
        app_module.resolve_stream_addr = lambda liveid, force=False: "https://evil.example.com/x.flv"
        try:
            r = self.client.get("/api/video/stream?liveid=123")
            self.assertFalse(r.json()["ok"])
            self.assertEqual(r.json()["reason"], "disallowed_stream_host")
        finally:
            app_module.resolve_stream_addr = old_resolve


if __name__ == "__main__":
    unittest.main()
