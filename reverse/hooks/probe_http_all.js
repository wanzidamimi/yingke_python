/*
 * 抓全部 OkHttp 请求/响应：hook okhttp3.RealCall.execute +enqueue 回调
 * 覆盖所有 OkHttp 实例（不限 IKSecureSignInterceptor）
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l probe_http_all.js
 */
'use strict';
function log(t, s) { console.log('[HA][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString().slice(0, 500); } catch (e) { return '<e>'; }
}
function bk(name, pi, si) {
  try {
    var a = Module.findExportByName(null, name);
    if (!a) return;
    Interceptor.attach(a, {
      onEnter: function (x) {
        var s = x[si].toInt32(), p = x[pi].toInt32();
        this.b = (s === 9 || s === 6) && p !== -1;
      },
      onLeave: function (r) { if (this.b) r.replace(0); }
    });
  } catch (e) {}
}
bk('kill', 0, 1); bk('tgkill', 1, 2);
log('ANTI', 'ok');

Java.perform(function () {
  // 1. hook OkHttpClient.newCall —— 拿 Request URL
  try {
    var OC = Java.use('okhttp3.OkHttpClient');
    OC.newCall.overload('okhttp3.Request').implementation = function (req) {
      try { log('NEWCALL', js(req.url())); } catch (e) {}
      return this.newCall(req);
    };
    log('HOOK', 'OkHttpClient.newCall ok');
  } catch (e) { log('WARN', 'newCall: ' + e); }

  // 2. hook RealCall.execute —— 拿 Response + body
  try {
    var RC = Java.use('okhttp3.internal.connection.RealCall');
    RC.execute.overload().implementation = function () {
      var res = this.execute();
      try {
        var url = res.request().url().toString();
        // 读 body（同步）
        var body = '';
        try {
          var b = res.body();
          if (b) body = b.string();
        } catch (e) { body = '<body err>'; }
        // 忽略埋点
        if (url.indexOf('maidian.inke.cn') < 0) {
          log('RESP_URL', url);
          if (body && body.length < 3000) log('RESP_BODY', body);
        }
      } catch (e) {}
      return res;
    };
    log('HOOK', 'RealCall.execute ok');
  } catch (e) { log('WARN', 'realcall: ' + e); }

  // 3. hook BridgeInterceptor.intercept（所有 OkHttp 都过它）—— 拿 URL
  try {
    var BI = Java.use('okhttp3.internal.http.BridgeInterceptor');
    BI.intercept.overloads.forEach(function (ov) {
      ov.implementation = function () {
        try {
          var chain = arguments[0];
          var url = chain.request().url().toString();
          if (url.indexOf('maidian.inke.cn') < 0) log('BRIDGE_URL', url);
        } catch (e) {}
        return ov.apply(this, arguments);
      };
    });
    log('HOOK', 'BridgeInterceptor ok');
  } catch (e) { log('WARN', 'bridge: ' + e); }

  log('READY', 'http-all probe installed');
});
