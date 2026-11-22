/*
 * 安全版：只 hook OkHttpClient.newCall 记录 URL，不读 body（避免破坏 App）
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l probe_urls_safe.js
 */
'use strict';
function log(t, s) { console.log('[US][' + t + '] ' + s); }
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
      },
      onLeave: function (r) { if (this.b) r.replace(0); }
    });
  } catch (e) {}
}
bk('kill', 0, 1); bk('tgkill', 1, 2);
log('ANTI', 'ok');

Java.perform(function () {
  // 只 hook newCall：安全，只记录不改任何数据
  try {
    var OC = Java.use('okhttp3.OkHttpClient');
    OC.newCall.overload('okhttp3.Request').implementation = function (req) {
      try {
        var url = req.url().toString();
        // 过滤埋点，只记录业务接口
        if (url.indexOf('maidian.inke.cn') < 0 && url.indexOf('/log/') < 0 && url.indexOf('/upload/') < 0) {
          log('URL', url);
        }
      } catch (e) {}
      return this.newCall(req);
    };
    log('HOOK', 'newCall ok');
  } catch (e) { log('WARN', 'newCall: ' + e); }

  log('READY', 'safe url probe installed');
});
