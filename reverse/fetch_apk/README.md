# 官方 APK 获取：项目调研与通用流程

目标：建立一套**可复用**的官方 APK 获取方式，映客只是第一个样本，以后处理其他 APP 都走这里。

## 一、GitHub 项目调研（2026-11 检索）

### A. 国内应用商店（映客这类国内 APP 的主渠道）

| 项目 | 覆盖 | 用法 / 状态 | 评价 |
|---|---|---|---|
| **halifox/app_market_crawler** ⭐推荐 | 360、百度、华为、联想、PP助手、三星、vivo、豌豆荚、小米、应用宝、应用汇（11 家） | Scrapy；`python -m app_market_crawler crawl <market> --mode package-list --packages <包名>`；采集详情/历史版本/**下载地址**；README 标注基于 2025-10 接口，仅 3 stars | 覆盖最全、按包名查、能拿下载地址；接口易失效，需自己验证 |
| **Han0nly/Crawl_3rd_party_stores** | 小米、360、应用宝、百度、豌豆荚、APKPure、酷安 | Python + Scrapy 选择器；按包名/ID 抓下载链接 | 老项目，思路可借鉴（每商店一个 spider） |
| **hh3755/ApkCrawler** | 应用宝、安卓市场、小米、豌豆荚、360 + 大量商店目录 | 按商店域名分目录，README 只有链接列表，无明确运行说明；0 stars | 参考目录组织方式，不推荐直接用 |
| **AppMarket / Obtainium**（Android 端工具） | 聚合小米/华为/OPPO/vivo/TapTap/酷安/GitHub 等 | 手机 App，直接从源头查历史版本并下载 | 适合**手动快速拿单个 APK**，不适合脚本化 |

### B. Google Play / 国际源

| 项目 | 用法 | 评价 |
|---|---|---|
| **EFForg/apkeep** ⭐推荐 | `apkeep -a <包名> .`；`-d apk-pure` / `-d f-droid`；`@版本` 指定版本；CSV 批量；Docker `ghcr.io/efforg/apkeep:stable` | 跨源 CLI 里最规范：EFF 维护、262 commits、跨 Google Play/APKPure/F-Droid、支持版本与批量。Google Play 源需 email + AAS token；APKPure/F-Droid 免凭据（APKPure 仅研究用途） |
| **UlyssesZh/google-play** | Go 实现，下载 APK 或发 API 请求；2025-05 仍活跃 | 适合要 Play 元数据/API 的场景 |
| **matlink/gplaycli**（及 fork） | `gplaycli -d <AppID>`；需 Google 凭据 | 老牌但维护弱，Play 鉴权易失效 |
| **APKMirror / APKPure** | 网页按包名搜，下载原版未修改 APK，提供 SHA-256 与签名比对 | **最省事的人工兜底**；APKMirror 只托管原始签名包，可校验签名一致性 |

### C. 结论：分层策略

1. **手工拿单个样本（最快）**：应用商店网页 / APKMirror / APKPure / Obtainium，下载后校验签名与哈希。
2. **脚本化批量/多版本（研究归档）**：`halifox/app_market_crawler`（国内）或 `apkeep`（国际），产出下载地址后入库。
3. **统一归档**：不管从哪来，都落到本目录的标准结构 + `manifest.json`，后续 REA 分析只认这个结构。

## 二、统一 APK 获取流程（以后所有 APP 都走这套）

```
包名 -> 选源 -> 下载 -> 校验 -> 登记 -> 交给 REA
```

1. **确定包名**：从应用商店 URL、Manifest、或搜索确认（如映客 `com.inke.tv`，需核实）。
2. **选源优先级**：国内 APP → 官方商店（应用宝/华为/小米）→ APKPure/APKMirror 兜底；海外 APP → apkeep(google-play/apk-pure/f-droid) → APKMirror。
3. **优先拿历史版本**：多个版本便于对比接口变化（REA 的 `compare_application_versions`）。
4. **校验**：记录 SHA-256、签名方案与证书指纹（REA `inspect_apk_signature`）、文件大小。来源不可信时对比官方签名。
5. **登记**：写 `reverse/apks/manifest.json`（字段见下），并把 APK 放进本目录。
6. **分析**：把路径传给 REA `inspect_android_package`，开始静态逆向。

## 三、目录约定

```
reverse/fetch_apk/
├── README.md          # 本文件：项目调研 + 通用流程
├── manifest.json      # 所有 APK 的登记表（包名/版本/来源/哈希/签名）
└── fetch.py           # 统一入口：按包名+来源下载，自动校验并登记
```

 manifests.json 单条示例：

```json
{
  "package": "com.inke.tv",
  "version": "x.y.z",
  "source": "yingyongbao | apkmirror | apk-pure | google-play | manual",
  "source_url": "https://...",
  "sha256": "...",
  "signer_fingerprint_sha256": "...",
  "path": "reverse/apks/inke_x.y.z.apk",
  "fetched_at": "2026-11-18",
  "note": ""
}
```

## 四、合规

- 仅下载/分析你有权研究的 APP，遵守目标商店服务条款。
- 控制访问频率，不做大规模爬取。
- APKMirror/APKPure 的镜像包要核对签名与原版一致；不要传播修改版或他人隐私数据。
