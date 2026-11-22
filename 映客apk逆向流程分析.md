# 映客 APK 逆向流程分析

> 本文整理整个映客弹幕逆向过程：用了哪些工具、走过哪些弯路、最后如何确定真正的弹幕接口，以及现在项目已经接成了什么样子。  
> 目标是让不熟悉逆向的人也能看懂。全文仅针对本地测试样本和授权环境，用于学习研究。

---

## 一、先说结论

映客 App 的直播间弹幕不是通过一个普通的网页地址发送的，也不是通过我们一开始猜的 WebSocket 或 HTTPS 接口发送的。

最终确认：

```text
直播间弹幕走 App 私有 TCP 长连接：1300 端口
```

它不是这种形式：

```text
wss://xxx.inke.cn/danmu?roomid=...
```

也不是这种形式：

```text
https://service.inke.cn/api/message/get
```

而是这样的流程：

```text
连接网关 IP:1300
-> 握手
-> 认证
-> 进房请求 0x0002
-> 订阅房间 0x4c04
-> 消息同步 0x4020
-> 服务端持续推送 0xb001 / 0xb002
-> 解压 JSON
-> 找 ms[].tp = pub
-> 取 ms[].c 作为弹幕正文
```

最重要的一句话：

```text
弹幕接口不是一个 URL，而是一组 TCP 私有协议命令。
```

---

## 二、整个逆向过程用了哪些工具

下面按用途分类说明。

### 1. APK 静态分析工具

| 工具 / 文件 | 用途 |
|---|---|
| `apktool` 反编译结果 `smali_out` | 把 APK 里的代码变成可读的 smali，分析类、方法、字符串、网络调用 |
| smali 搜索 | 搜索 `chat`、`s.m`、`s.pb`、`tp`、`ms`、 `MESSAGE_GET`、`MESSAGE_V2_FETCH` 等关键字 |
| `AndroidManifest.xml` | 查 App 包名、权限、入口、meta-data |
| 资源文件搜索 | 搜索“来啦来啦”“哈哈哈哈哈”等快捷弹幕文案，判断是否本地硬编码 |

静态分析解决了这些问题：

```text
App 包名是什么
有哪些消息入口
消息 JSON 结构长什么样
有哪些候选接口地址
订阅命令大概在哪里构造
```

但静态分析不能解决运行时动态值，比如：

```text
当前 gid
当前 nonce
当前 RC4 key
服务端是否真的给这个房间推消息
```

---

### 2. ADB 与模拟器工具

| 工具 | 用途 |
|---|---|
| `adb` | 查看进程、启动 App、点击进入直播间、截图、设置代理 |
| `adb shell screencap` | 截图确认当前页面和界面上是否真的有弹幕 |
| `adb shell am start` | 尝试通过深链进入直播间 |
| `adb shell monkey` | 启动映客 App |
| `adb shell settings put global http_proxy` | 给模拟器设置 MITM 代理 |
| `adb root` / `su` | 安装证书、查看连接 |

ADB 的作用主要是控制模拟器：

```text
打开 App
进入直播间
确认界面状态
设置代理
提取系统信息
```

---

### 3. Frida 动态 Hook 工具

| 文件 | 用途 |
|---|---|
| `hook_handshake.js` | hook 握手相关函数，想拿 nonce / token / RSA 明文 |
| `hook_early.js` | 尝试更早 hook `ClassLoader.loadClass` |
| `hook_http_min.js` | 尝试 hook HTTP 备份订阅 |
| `get_auth.js` | 调 App 内部签名函数生成 Authorization |
| `hook_sign_args.js` | hook 签名函数真实参数 |
| `probe_http.js` | 观察 App 发出的 HTTP 请求 |

Frida 解决的问题：

```text
确认签名算法参数顺序
拿到 App 内部 appid / secret
理解部分加密逻辑
```

Frida 没解决的问题：

```text
spawn 阶段太早，Java runtime 还没起来
attach 阶段太晚，连接已经建立
App 有反调试，进程容易被杀
arm64 native bridge 下 x86_64 frida 看不到真正的 native libc
```

所以后来把 Frida 从主链路里移除了。

---

### 4. 抓包工具

| 工具 | 用途 |
|---|---|
| `pktmon` | Windows 宿主抓包，主要抓 1300、80、全 TCP、全 UDP |
| `pktmon etl2pcap` | 把 ETL 转成 pcapng |
| `tcpdump` | 模拟器内抓包，抓全量 pcap |
| `parse_pktmon_pcap.py` | 自己写的 pcapng 解析脚本 |
| `quick_capture.py` | 一键抓包并汇总目标地址 |
| `Wireshark` 思路 | 按端口、SNI、TCP 连接方向分析 |

抓包是最终定位弹幕接口的关键工具。

一开始用 `pktmon` 抓：

```text
1300 端口
80 端口
全 TCP
全 UDP
```

后来又用 `tcpdump` 抓全量流量，确认 App 的真实连接目标。

---

### 5. MITM / HTTPS 解密工具

| 工具 | 用途 |
|---|---|
| `mitmproxy` / `mitmdump` | 解密 HTTPS 请求 |
| `mitm_capture_auth.py` | 记录真实 Authorization、URL、headers、body |
| `mitm_save.py` | 保存服务端配置响应 |
| CA 证书安装 | 让 App 信任代理证书 |

MITM 主要帮助确认：

```text
service.inke.cn 上有哪些接口
配置里有哪些 URL key
Authorization 的真实格式
/api/message/get 为什么返回 700
MESSAGE_V2_* 新版接口列表
```

但最后发现：

```text
弹幕实时接收不走 HTTPS
```

MITM 是排除错误方向的重要工具，不是最终采集方案。

---

### 6. Python 协议复刻工具

| 文件 | 用途 |
|---|---|
| `app_tcp_client.py` | 握手、RSA、RC4、订阅包构造 |
| `brute_nonce.py` | 穷举 nonce，解密握手响应，恢复 RC4 key |
| `replay_and_subscribe.py` | 重放握手、认证、订阅 |
| `analyze_hotroom.py` | 统计房间消息类型 |
| `reassemble_tcp_frames.py` | TCP 流重组 + 私有帧切帧 |
| `extract_live_danmu.py` | 从 pcap 提取真实弹幕 |
| `inke_tcp_collector.py` | 最终主流程使用的 TCP 采集器 |

这些脚本完成了从“看抓包”到“项目可用”的转换。

---

## 三、走过的弯路

### 弯路 1：以为弹幕有固定 WebSocket URL

一开始以为映客会和很多 Web 直播平台一样，有一个类似：

```text
wss://chat.inke.cn/danmu?roomid=xxx
```

的地址。

后来发现：

```text
Web 端旧接口 chatroom.inke.cn/url 是旧路线
App 当前不是这个模式
```

App 的模式是：

```text
私有 TCP 网关 + 私有二进制协议 + gzip/RC4 JSON
```

---

### 弯路 2：一直搜 `tp=chat`

源码注释和旧解析器里出现了：

```json
{"tp":"chat"}
```

于是一直在抓包里搜：

```text
tp=chat
```

结果一直搜不到。

后来源码细看才发现：

```text
tp=chat 在 cfg 分支里只是配置
用于设置 forbid / freq
不是聊天正文
```

真正的聊天正文类型是：

```text
tp=pub
内容是 c 字段
```

这是一个非常关键的误判。

---

### 弯路 3：Frida 想拿早期握手，但被反调试挡住

思路是对的：

```text
越早 hook，越能拿到握手明文
```

但实际遇到几个问题：

```text
spawn 太早：Java runtime 还没初始化
attach 太晚：TCP 连接已经建立
App 反调试会杀进程
x86_64 模拟器里的 arm64 native bridge 导致 hook 不到真正的 native libc
```

最后确认根因：

```text
App 的 native 反调试在 arm64 侧
当前 Frida 只能看到 x86_64 侧
SIGKILL 无法事后拦截
```

所以停止死磕 Frida，转被动抓包 + 重放。

---

### 弯路 4：HTTP `/api/message/get` 返回 700

从配置里找到：

```text
MESSAGE_GET = https://service.inke.cn/api/message/get
```

但直接请求返回：

```json
{"dm_error":700,"error_msg":"客户端版本过低, 请进行升级"}
```

一开始怀疑 Authorization 错了。

后来把签名算法完整还原：

```text
packageName
+ 空 body 的 md5 base64
+ HTTP method
+ timestamp
+ query
```

再 HMAC-SHA1，才确认：

```text
Authorization 是正确的
700 是接口自身的版本门槛
```

也就是说：

```text
/api/message/get 是旧接口，不是当前弹幕主通道
```

---

### 弯路 5：MITM 证书一开始不被信任

最开始只装了用户 CA，App 不信任：

```text
Client does not trust the proxy's certificate
```

后来通过：

```text
复制 cacerts 到可写目录
用正确 hash 命名 CA
mount --bind 覆盖 /system/etc/security/cacerts
```

解决系统证书问题。

这一步成功解密了：

```text
service.inke.cn
```

但最后发现弹幕不走 HTTPS，所以 MITM 主要用于排查，不是最终方案。

---

### 弯路 6：按单个 TCP 包解析，漏掉真实弹幕

这是最后一个大坑。

一开始的解析脚本是：

```text
一个 TCP payload = 一个私有协议帧
```

但实际网络中：

```text
一个 gzip body 可能跨多个 TCP 段
```

所以很多消息被切碎，脚本直接跳过。

后来改成：

```text
先按 TCP 四元组 + seq 重组完整字节流
再按私有帧结构切帧
再 gzip / RC4 解压
```

这一步之后，终于在旧抓包里找到了真实弹幕：

```text
cmd=0x0004
tp=pub
c=来啦来啦[say hi][庆祝]
```

---

### 弯路 7：订阅命令发错

一开始按旧理解发送：

```text
cmd=0x0100
```

服务端只回 ACK，没有推送。

后来从真实 App 抓包里看到，进房订阅其实是：

```text
0x0002  进房请求
0x4c04  房间订阅
0x4020  消息同步
```

而不是单独的 `0x0100`。

同时包头里的 `version` 也写错了：

```text
0x0002 version = 0x000c
0x4c04 version = 0x000d
0x4020 version = 0x000e
```

`version` 不是命令字本身，这一点当时也踩了坑。

---

## 四、最后是怎么确定弹幕接口的

最终靠三条证据闭环。

### 证据 1：抓包里有界面上真实出现的弹幕

在 `danmu_long.pcapng` 里，通过 TCP 流重组发现了：

```json
{
  "uid": 779252212,
  "bus_buf": {
    "b": {
      "ev": "c.ch"
    },
    "tp": "pub",
    "c": "来啦来啦[say hi][庆祝]"
  }
}
```

这就是界面上出现过的弹幕。

同时也抓到服务端推送：

```text
cmd=b001
tp=pub
nick=蝉鸣半夏
c=来啦来啦[say hi][庆祝]
```

这说明：

```text
弹幕确实走 1300 TCP
```

---

### 证据 2：重放真实命令序列能持续收消息

按真实 App 的顺序重放：

```text
握手
认证
0x0002
0x4c04
0x4020
```

服务端开始持续返回：

```text
cmd=b001
cmd=b002
```

其中能解析出：

```text
聊天弹幕
进场消息
在线人数
系统公告
```

这证明不是偶然抓到，而是可以稳定复现的链路。

---

### 证据 3：轮换多个直播间都能收到聊天

测试 5 个直播间，每个 20 秒：

| 直播间 | 聊天消息 |
|---|---:|
| 江南 | 21 |
| 无声的糖果果 | 20 |
| ·KAMA· | 21 |
| 昭昭💕 | 0 |
| Kiki♒️ | 21 |

其中 4 个房间都有聊天，只有 1 个冷清房间没有聊天。

说明：

```text
采集器没有问题
是否收到聊天取决于直播间活跃度
```

---

## 五、最终协议链路

### 1. 连接

```text
TCP IP:1300
```

常用网关：

```text
111.13.223.188:1300
111.13.223.167:1300
47.95.96.98:1300
```

---

### 2. 握手和认证

目前仍使用抓包样本重放：

```text
203 字节握手包
817 字节认证包
nonce = dbebdhgd
key = 0c2a616bfd8442aec0495d04d3ae3599
```

握手响应用 nonce 做 RC4 解密，得到后续报文使用的 key。

---

### 3. 进房三步

#### `0x0002`：进房请求

```text
body = RC4(JSON)
JSON 里包含 uid、rid、liveid、pass-through
```

#### `0x4c04`：房间订阅

```text
body = 明文
body 结构：
  u16(0x0100)
  lv("domain")
  lv("group")
  lv("topic_xx")
  lv(liveid)

ext = {"long-uid":779252212,"xid":13}
```

`topic_xx` 中的 `xx` 是 liveid 最后两位。

#### `0x4020`：消息同步

```text
body = 空

ext = {
  "liveid": "...",
  "max-id": ...,
  "xid": 14,
  "long-uid": 779252212
}
```

---

### 4. 服务端推送

主要是两个命令：

```text
0xb001 : body = RC4(key) + gzip JSON
0xb002 : body = gzip JSON
```

解压后是房间消息 JSON：

```json
{
  "b": {"ev": "s.m"},
  "liveid": "...",
  "ms": [
    {
      "tp": "pub",
      "c": "弹幕内容",
      "from": {
        "id": 123,
        "nic": "昵称"
      },
      "msg_type": 0
    }
  ]
}
```

---

### 5. 弹幕字段

```text
tp = pub
内容字段 = c
昵称字段 = from.nic
用户 uid = from.id
```

旧代码里看到的：

```text
tp = pp
tp = chat
```

不是当前线上主要格式。

---

## 六、项目现在接成了什么

新增或修改：

```text
app.py
inke_tcp_collector.py
static/index.html
category.py
```

页面现在有：

```text
热门直播间卡片
手动 liveid 输入
手动 UID 输入
分类过滤
实时 SSE 列表
CSV 导出
历史记录
```

后端流程变为：

```text
用户选房间
-> /api/start
-> 解析 liveid
-> InkeTcpCollector
-> TCP 1300 握手/认证/进房/订阅
-> 解析弹幕
-> on_message()
-> SSE 推到页面
-> Recorder 写 CSV
```

启动：

```powershell
cd d:/Scrapy-project/yingke_python
python -m uvicorn app:app --host 127.0.0.1 --port 8801
```

打开：

```text
http://127.0.0.1:8801
```

---

## 七、当前还限制在哪里

这版已经不再依赖 pcap 样本：

```text
inke_room2.pcapng      不再读取
danmu_long.pcapng      不再读取
```

已经完成：

```text
自主 RSA 握手：完成 ✅
动态 0x4004 认证：完成 ✅
动态 0x0002 / 0x4c04 / 0x4020 进房：完成 ✅
从 ADB SharedPreferences 动态刷新 gid：完成 ✅
去掉 pass-through token 仍能进房：验证通过 ✅
页面选择直播间：完成 ✅
SSE/CSV：完成 ✅
```

目前还需要一个运行时配置：

```text
reverse/references/inke_runtime_config.json
```

里面主要是账号 uid、gid、设备字段和进房 JSON 模板。

也就是说，主流程已经从：

```text
重放 pcap
```

升级为：

```text
自主生成握手 + 动态构造认证 + 动态构造进房
```

剩余可优化项：

```text
1. smid / sid / mtid / devi / clientId 仍来自一次配置
2. 如果要跨账号使用，需要从 App 接口或本地配置动态刷新这些字段
3. room_id / logid 目前沿用模板，实测不影响收弹幕
```

这些属于“账号环境迁移”优化，不影响当前账号下的弹幕采集。

---

## 八、这次逆向最重要的经验

1. **不要只信源码注释**  
   源码里有旧逻辑，`tp=chat` / `tp=pp` 都误导过我们。线上真实格式是 `tp=pub`。

2. **抓包必须按流重组**  
   单个 TCP payload 不是完整协议帧，跨包 body 会漏掉关键消息。

3. **服务端配置不等于当前主链路**  
   `/api/message/get` 存在，但被版本门槛挡住，不是当前弹幕主通道。

4. **MITM 适合排查，不一定适合最终采集**  
   它帮我们找到很多接口和签名细节，但真正弹幕走私有 TCP。

5. **协议命令比 URL 更重要**  
   映客这类 App 的“弹幕接口”不是 URL，而是 TCP 命令组合。

6. **冷门房间没有弹幕很正常**  
   是否收到弹幕取决于房间活跃度。测试和验收要多换几个房间。

---

## 九、最终状态一句话

```text
映客 App 的直播间弹幕已确认走 TCP 1300 私有长连接。
主流程已经接入 TCP 直连采集器，页面可以选热门直播间，能实时收到 tp=pub 的聊天弹幕，并继续用 SSE 展示和 CSV 导出。
```
