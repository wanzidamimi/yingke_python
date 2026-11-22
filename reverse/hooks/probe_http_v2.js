/*
 * HTTP 抓包 v2：适配映客自研网络栈（非标准 okhttp3）
 * hook IKSecureSignInterceptor.intercept(a)，通过反射挖 URL
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l probe_http_v2.js
 */
'use strict';
function log(t, s) { console.log('[H2][' + t + '] ' + s); }
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
  var S = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
  S.intercept.overloads.forEach(function (ov, idx) {
    ov.implementation = function () {
      var chain = arguments[0];
      // 反射：列 chain 的所有方法名（只列一次）
      if (idx === 0 && !this._scanned) {
        this._scanned = true;
        try {
          var cls = chain.getClass();
          var ms = cls.getDeclaredMethods();
          var names = [];
          for (var i = 0; i < ms.length; i++) names.push(ms[i].getName());
          log('CHAIN_METHODS', cls.getName() + ' -> ' + names.join(','));
        } catch (e) { log('SCAN_ERR', String(e).slice(0, 150)); }
      }
      // 调用原方法拿 Response
      var res = ov.apply(this, arguments);
      try {
        // Response.request().url()
        var req = res.request();
        var url = req.url().toString();
        // 过滤埋点
        if (url.indexOf('maidian.inke.cn') < 0 &&
            url.indexOf('/log/') < 0 && url.indexOf('/upload/') < 0) {
          log('URL', url);
          // 尝试拿请求方法
          try { log('METHOD', req.method() + ' headers=' + js(req.headers())); } catch (e) {}
        }
      } catch (e) {}
      return res;
    };
  });
  log('READY', 'http v2 installed');
});
