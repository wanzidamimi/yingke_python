/*
 * 抓 HTTP 进房接口：hook IKSecureSignInterceptor.intercept（OkHttp 风格拦截器）
 * 直接拿 Java 层明文 Request URL / Response，不需要过证书锁定
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l probe_http.js
 */
'use strict';
function log(t, s) { console.log('[HTTP][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString().slice(0, 600); } catch (e) { return '<e>'; }
}

// 反反调试
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
bk('kill', 0, 1);
bk('tgkill', 1, 2);
log('ANTI', 'ok');

Java.perform(function () {
  // 1. hook IKSecureSignInterceptor.intercept 的所有重载
  try {
    var S = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
    var ovl = S.intercept.overloads;
    log('INTERCEPT_OVERLOADS', String(ovl.length));
    ovl.forEach(function (ov, idx) {
      ov.implementation = function () {
        try {
          var chain = arguments[0];
          log('CHAIN_CLASS_' + idx, chain.getClass().getName());
          // 尝试拿 request / url
          try {
            var req = chain.request();
            log('REQ_' + idx, js(req));
            try { log('URL_' + idx, js(req.url())); } catch (e) {}
            try { log('HEADERS_' + idx, js(req.headers())); } catch (e) {}
            try { log('BODY_' + idx, js(req.body())); } catch (e) {}
          } catch (e) { log('REQ_ERR_' + idx, String(e).slice(0, 200)); }
        } catch (e) {}
        var res = ov.apply(this, arguments);
        try { log('RESP_' + idx, js(res)); } catch (e) {}
        return res;
      };
    });
    log('HOOK', 'IKSecureSignInterceptor.intercept ok');
  } catch (e) { log('WARN', 'interceptor: ' + e); }

  // 2. hook OkHttp 的 CallServerInterceptor / BridgeInterceptor（若存在）
  ['okhttp3.internal.http.CallServerInterceptor',
   'okhttp3.internal.http.BridgeInterceptor'].forEach(function (cls) {
    try {
      var C = Java.use(cls);
      var ms = C.class.getDeclaredMethods();
      log('OKHTTP_CLASS', cls + ' methods=' + ms.length);
      ms.forEach(function (m) {
        if (m.getName() !== 'intercept') return;
        try {
          C.intercept.overloads.forEach(function (ov) {
            ov.implementation = function () {
              try {
                var chain = arguments[0];
                var req = chain.request();
                log('OKHTTP_URL', js(req.url()));
              } catch (e) {}
              return ov.apply(this, arguments);
            };
          });
        } catch (e) {}
      });
    } catch (e) {}
  });

  log('READY', 'http probe installed');
});
