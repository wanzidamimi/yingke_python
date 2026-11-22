/*
 * dump App HTTP 请求的所有 header，找登录 token
 * hook IKSecureSignInterceptor.intercept（已验证稳定）
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l dump_token.js
 */
'use strict';
function log(t, s) { console.log('[TOK][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString().slice(0, 400); } catch (e) { return '<e>'; }
}
function bk(name, pi, si) {
  try {
    var a = Module.findExportByName(null, name);
    if (!a) return;
    Interceptor.attach(a, {
      onEnter: function (x) {
        var s = x[si].toInt32(), p = x[pi].toInt32();
        this.b = (s === 9 || s === 6) && p !== -1;
      }, onLeave: function (r) { if (this.b) r.replace(0); }
    });
  } catch (e) {}
}
bk('kill', 0, 1); bk('tgkill', 1, 2);
log('ANTI', 'ok');

Java.perform(function () {
  // hook 签名拦截器，dump Response.request() 的所有 header
  try {
    var S = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
    S.intercept.overloads.forEach(function (ov) {
      ov.implementation = function () {
        var res = ov.apply(this, arguments);
        try {
          var req = res.request();
          var url = req.url().toString();
          // 只看非埋点
          if (url.indexOf('maidian') < 0) {
            log('URL', url);
            try {
              var hdrs = req.headers();
              var map = hdrs.toMap ? hdrs.toMap() : hdrs;
              log('HEADERS', js(map));
            } catch (e) {
              // 尝试 toString
              try { log('HEADERS_STR', js(req.headers())); } catch (e2) {}
            }
          }
        } catch (e) {}
        return res;
      };
    });
    log('HOOK', 'intercept ok');
  } catch (e) { log('WARN', 'intercept: ' + e); }

  // 也 hook 一个更底层：把所有 Request.Builder.header 调用打出来
  try {
    var HB = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
    // 反射看字段名（静态 token 字段）
    var fields = HB.class.getDeclaredFields();
    for (var i = 0; i < fields.length; i++) {
      try {
        var fname = fields[i].getName();
        var val = HB[fname].value;
        if (val != null && js(val).length < 200) log('STATIC_FIELD', fname + '=' + js(val));
      } catch (e) {}
    }
  } catch (e) {}

  log('READY', 'token dump installed');
});
