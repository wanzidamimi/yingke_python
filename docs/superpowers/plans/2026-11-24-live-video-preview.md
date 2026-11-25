# Web 直播间画面预览 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or executing-plans to implement this plan task-by-task.

**Goal:** 在现有 Web 弹幕控制台上显示当前直播间的主播画面；画面与弹幕采集分离，画面走 HTTP-FLV，弹幕继续走 TCP 1300。

**Architecture:** 后端从 `Live_top_pc` 获取 `stream_addr`，按 `liveid` 缓存短期播放地址，并通过同源代理转发 FLV 字节；前端用本地打包的 `mpegts.js` / `flv.js` 播放 HTTP-FLV。前端只传 `liveid`，不接触带 `wsSecret` 的完整 URL。

**Tech Stack:** FastAPI、httpx/curl_cffi 流式请求、HTML video + MSE、mpegts.js（本地 vendor）、unittest。

**Spec:** 用户 2026-11-24 需求：“Web 端页面显示直播间画面；确认 TCP 是否返回画面。”

## Global Constraints

- 不把视频流接入 TCP 1300 采集器。
- 不把 `stream_addr` 或 `wsSecret` 暴露给浏览器。
- 后端只 resolving 白名单域名：
  - `live-pull-ws.ikstatic.cn`
  - `live-pull.ikstatic.cn`
  - 后续实证发现的其他映客官方拉流域名
- 不接受任意 URL 参数，防止 SSRF。
- 播放器 JS 放本地 `static/vendor/`，不依赖 CDN。
- 无画面可用时，页面明确提示“该房间暂无可播放画面”，不影响弹幕采集。

## Evidence

### TCP 1300

已抓到并解析：

```text
cmd=b001 / b002
gzip 或 RC4+gzip JSON
tp=pub        聊天
tp=usernu     在线人数
user_join_tip 进场
gift          礼物
system        系统消息
```

没有发现：

```text
视频帧
HLS/FLV 分片
音频帧
```

### Web API

`https://webapi.busi.inke.cn/web/Live_top_pc` 当前热门房间字段：

```json
{
  "uid": "757603607",
  "live_id": "1795522334333278",
  "nick": "亦可姐姐",
  "portrait": "...",
  "stream_addr": "https://live-pull-ws.ikstatic.cn/live/1795522334333278_t.flv?stream_id=...&wsSecret=...&wsABStime=..."
}
```

实测：

```text
HTTP 200
Content-Type: video/x-flv
```

`live_share_pc?uid=...` 返回：

```text
status
liveid
media_info
records
```

但没有直接返回 `stream_addr`，所以手动 UID 的首版画面能力依赖“解析 liveid 后在 Live_top_pc 中匹配”。

---

## Task 1: 后端流地址解析

**Files:**
- Create: `video_stream.py`
- Test: `tests/test_video_stream.py`

**Interfaces:**
- Produces:
  - `fetch_hot_rooms_raw() -> list[dict]`
  - `find_stream_addr(liveid, rooms=None) -> str`
  - `normalize_stream_url(url) -> str`
  - `is_allowed_stream_host(url) -> bool`

**Steps:**
- [ ] 写失败测试：从热门列表匹配 liveid 返回 stream_addr。
- [ ] 写失败测试：非白名单域名拒绝。
- [ ] 实现 `video_stream.py`。
- [ ] 测试通过。

---

## Task 2: 后端同源 FLV 代理

**Files:**
- Modify: `app.py`
- Test: `tests/test_video_proxy_api.py`

**Interfaces:**
- Produces:
  - `GET /api/video/stream?liveid=...`

行为：

```text
1. liveid 必填
2. 从 Live_top_pc 找 stream_addr
3. 校验域名白名单
4. 流式代理上游响应
5. Content-Type 原样返回 video/x-flv
6. Cache-Control: no-store
```

- [ ] 写失败测试：缺 liveid 返回 ok=false。
- [ ] 写失败测试：mock `find_stream_addr`，验证接口使用 liveid。
- [ ] 实现接口。
- [ ] 测试通过。

---

## Task 3: 前端播放器

**Files:**
- Create: `static/vendor/mpegts.min.js`
- Modify: `static/index.html`
- Test: `tests/test_ui_video_player.py`

页面结构：

```html
<div class="video-stage">
  <video id="liveVideo" muted autoplay playsinline></video>
  <div id="videoPlaceholder">选择房间后显示画面</div>
  <div id="videoInfo">画面来自 HTTP-FLV，与弹幕 TCP 连接独立</div>
</div>
```

JS：

```javascript
let videoPlayer = null;

async function loadVideo(liveid) {
  destroyVideo();
  const url = `/api/video/stream?liveid=${encodeURIComponent(liveid)}`;
  videoPlayer = mpegts.createPlayer({type:'flv', url, isLive:true});
  videoPlayer.attachMediaElement(document.getElementById('liveVideo'));
  videoPlayer.load();
  videoPlayer.play().catch(() => {});
}

function destroyVideo() {
  if (videoPlayer) {
    videoPlayer.destroy();
    videoPlayer = null;
  }
}
```

调用点：

```text
房间卡片点击 -> startSession() + loadVideo(liveid)
顶部手动输入 -> startSession() + resolve 后 loadVideo(liveid)
停止采集 -> stopVideo()
退出登录 -> stopVideo()
```

- [ ] 写 UI 文本测试：`liveVideo`、`mpegts`、`loadVideo`。
- [ ] 实现页面结构。
- [ ] 测试通过。

---

## Task 4: 流刷新与错误提示

**Files:**
- Modify: `static/index.html`
- Modify: `video_stream.py`
- Test: `tests/test_video_stream.py`

行为：

```text
1. stream_addr 带 wsSecret/时间参数，会过期
2. 每次选择房间都重新 resolve
3. 播放器 error 时提示“画面流过期，正在刷新”
4. 自动 reload 一次
5. 仍失败则显示“该房间暂无可播放画面”
```

- [ ] 写失败测试：stream URL 缓存过期后重新 resolve。
- [ ] 实现刷新逻辑。
- [ ] 测试通过。

---

## Task 5: 文档与验收

**Files:**
- Modify: `README.md`
- Modify: `逆向实战记录_映客.md`

验收命令：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile app.py video_stream.py
```

手工验收：

```text
1. 打开页面
2. 登录
3. 点击热门房间卡片
4. 弹幕正常显示
5. 画面区域显示主播视频
6. 停止后画面停止
7. 换房间后画面切换
8. 冷清/无流房间只显示提示，不影响弹幕
```

## Review Focus

- TCP 不承载画面，不能误接到 b001/b002 解析。
- 浏览器不能拿到 `wsSecret`。
- 不接受任意视频 URL。
- 视频失败不能阻塞弹幕采集。
- 无声自动播放要设置 `muted`，避免浏览器拦截。
