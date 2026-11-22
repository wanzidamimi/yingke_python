/*
 * 极简 token dump：完全照搬已验证稳定的 probe_http.js 结构
 * 只 hook IKSecureSignInterceptor.intercept 打 Response + request header
 */
'use strict';
function log(t, s) { console.log('[TK2][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString().slice(0, 600); } catch (e) { return '<e>'; }
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
  try {
    var S = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
    S.intercept.overloads.forEach(function (ov, idx) {
      ov.implementation = function () {
        var res = ov.apply(this, arguments);
        try { log('RESP_' + idx, js(res)); } catch (e) {}
        return res;
      };
    });
    log('HOOK', 'ok');
  } catch (e) { log('WARN', String(e)); }
  log('READY', 'v2 installed');
});
