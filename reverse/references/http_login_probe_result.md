# HTTP 手机号登录探针结果

## 结论

```text
发送短信验证码接口：已打通 ✅
登录接口：已打通 ✅
登录响应 secret 校验：通过 ✅
```

短信发送请求实测返回：

```json
{"dm_error":0,"error_msg":"操作成功","request_id":"<运行时返回>"}
```

登录接口实测返回：

```json
{"dm_error":0,"error_msg":"操作成功"}
```

实际得到的字段：

```text
uid
session
secret
```

说明：

```text
真实 session 和手机号没有写入仓库文件
只用运行时数据完成验证
```

登录响应校验实测：

```text
secret_match = True
```

## 新增文件

| 文件 | 说明 |
|---|---|
| `reverse/references/http_login_probe.py` | 隔离探针，构造手机号登录参数与签名 |
| `reverse/references/run_http_login_probe.py` | CLI，支持 `--step dry/sms/login` |
| `tests/test_http_login_probe.py` | 红绿单元测试 |
| `docs/superpowers/plans/2026-11-23-http-login-probe.md` | 实施计划 |

## 源码确认的参数

### 发送验证码

```text
POST https://service.inke.cn/user/account/phone_code
```

body 字段：

```text
phone       = RSA/PKCS1(area_code + phone) -> lowercase hex
region      = native getRegion(area_code)，首版用 cn 实测通过
secret      = MD5(area_code + phone)
source      = login
area_code   = 86
finger_list = {}
```

返回：

```text
request_id
```

### 登录

```text
POST https://service.inke.cn/user/account/phone_login
```

body 字段：

```text
request_id   = 短信接口返回值
phone        = 同短信接口的 RSA hex
code         = 用户短信验证码
secret       = MD5(area_code + phone + "#" + code)
dev_name     = GooglePixel3
finger_list  = {}
link         = 0
visitor_uid  = 0
target_uid   = 0
```

登录响应字段：

```text
uid
session
secret
```

响应校验公式：

```text
secret == MD5("IKLOGIN#RsDyXjH#" + session + "#" + uid + "#MsJzKdY")
```

## 签名

请求头：

```text
Authorization: InkeV1 OklL:<base64(HMAC_SHA1(message, 1ba5fb066d7e33d5))>
Client-TimeStamp: <毫秒时间戳>
Content-Type: text/plain; charset=utf-8
User-Agent: okhttp/3.12.13
```

签名消息：

```text
com.meelive.ingkee
+ "\n"
+ base64(MD5(body_bytes))
+ "\n"
+ POST
+ "\n"
+ timestamp
+ "\n"
+ query
```

## 测试

红灯阶段：

```text
8 tests failed，原因：模块不存在
```

绿灯阶段：

```text
8 tests OK
```

覆盖：

```text
MD5
phone_secret
login_secret
RSA/PKCS1 手机号加密
Authorization 签名
短信请求体
登录请求体
```

## 隐私约束

```text
手机号只从 INKE_TEST_PHONE 环境变量读取
验证码只从 INKE_SMS_CODE 环境变量读取
两者都不写入仓库文件、不写入测试、不写入文档
```

## 使用方式

发送验证码：

```powershell
$env:INKE_TEST_PHONE='手机号'
python reverse/references/run_http_login_probe.py --step sms
```

登录：

```powershell
$env:INKE_TEST_PHONE='手机号'
$env:INKE_SMS_CODE='验证码'
python reverse/references/run_http_login_probe.py --step login --request-id '<短信接口返回的 request_id>'
```
