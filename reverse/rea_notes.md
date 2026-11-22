# REA 分析记录（模板）

> 按「观察 / 推断 / 未知」记录。每条尽量附 Evidence ID 或抓包文件位置。

## 样本信息

- APK 路径：`D:\Scrapy-project\yingke_python\yingke.apk`（119,320,058 bytes）
- 版本 / 渠道：versionName `9.9.05`，versionCode `9920`；渠道未知
- 包名：`com.meelive.ingkee`（**观察**：JADX `inspect_android_package`，Evidence `ev_3ce6785...`）
- SHA-256：`5974d43b003812af8989536f8bad98b6a9e68daa17f70ad9c2a70f841d25c749`
- minSdk 21 / targetSdk 33
- 来源：用户已下载，来源待补登记到 `fetch_apk/manifest.json`

## 关键障碍：APK 已加固（加壳）

**观察（Evidence `ev_e1104cc...`）**：
- `search_android_classes` 空查询只返回 5 个类：`com.meelive.ingkee.R`、`s.h.e.l.l.A`、`s.h.e.l.l.C`、`s.h.e.l.l.N`、`s.h.e.l.l.S`。
- 全部关键词（danmu / barrage / chat / comment）`matches` 均为空。
- ZIP 内只有 1 个 `classes.dex`，但存在 `assets/ijm_lib/{arm64-v8a,x86_64}/libexec.so`、`libexecmain.so`、`libexecoat.so`、`assets/IJMDal.Data`。

**推断**：`s.h.e.l.l.*` + `ijm_lib` 是**爱加密（IJMedia / ijm_lib）加固**特征。真实业务 dex 被加密藏在壳中，运行时由 native 层解密加载，因此 JADX 静态只能看到壳的 5 个类。**当前无法直接静态反编译出业务代码/接口**。

**结论**：REA 静态逆向对"壳内"代码暂时无效，必须先脱壳拿到原始 dex，这一步 REA 不会做（它不执行 APK）。

## 脱壳已完成（见项目根目录 `逆向实战记录_映客.md`）

- 雷电9 开 root（`vms/config/leidian0.config` 的 `rootMode` 改 true 后 reboot）+ frida 17.19.0/server/frida-dexdump 2.0.1。
- attach 运行中 PID 脱壳，dump 42 个 dex（去重后 41 个），重组为 `reverse/unpacked.apk`（181MB）。
- REA 分析 `unpacked.apk`：类数量 5 → 33368，业务代码全部可见。

## 接口候选（观察，Evidence 见根目录实战记录）

- 弹幕链路：`tech.appshatcher.comm.conn.*`（私有 TCP 长连接 + RSA）→ `RoomMessageCenter.onMessage(JSONObject)`（JSON 载荷）。
- 关键类：`InKeConnClient`、`TcpChannelFactory`、`InKeRsaManager`、`IKSecureSignInterceptor`、`BarragePushModel`、`IMChatMessage*`。
- 未知（需动态确认）：TCP host/port、订阅命令字、RSA 加密范围、liveId/token 来源。

## 下一步

1. Frida hook `RoomMessageCenter.onMessage` / `InKeConnClient` 收发 / `InKeRsaManager` 拿明文协议与网关地址。
2. mitmproxy/Charles 抓进房 HTTP 接口拿 liveId/token。
3. 回填运行侧骨架。

## 阶段 1：静态分析

### 包与清单（观察）
- `inspect_android_package` Evidence ID：
- 关键权限 / 组件：
- 网络相关配置（usesCleartextTraffic / networkSecurityConfig）：

### 候选类（观察）
| 类名 | 发现方式 | 作用推断 | Evidence ID |
|---|---|---|---|
| | `search_android_classes("danmu")` | | |

### 候选接口（推断）
| URL / host | 来自方法 | 是否弹幕相关 | 待抓包验证 |
|---|---|---|---|
| | | | ☐ |

### 签名线索（推断）
- 相关类 / 方法：
- 参数顺序与拼接规则：
- 是否进 so（so 名 / 导出函数）：

### 未知（需动态验证）
- 反射 / 动态加载点：
- 未解析调用：
- so 内部逻辑：

## 阶段 2：抓包确认

- 抓包文件：
- 真实弹幕接口 URL：
- 握手参数 / 头：
- 消息格式（JSON / protobuf / 私有二进制）：
- 二进制样本位置：
- 证书锁定：有 / 无；绕过方式：

## 阶段 3：复刻进度

- [ ] `config.py` 填入域名与版本
- [ ] `http_client.py` 会话初始化
- [ ] `signer.py` 签名方案
- [ ] `decoder.py` 消息解码
- [ ] `danmu_client.py` 长连接
- [ ] 自检 + 真房间验证
