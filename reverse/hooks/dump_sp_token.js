/*
 * hook SharedPreferences.getString，抓 App 读取的 token/auth 类明文值
 * 轻量 hook，避免 ANR
 */
'use strict';
function log(t, s) { console.log('[SPT][' + t + '] ' + s); }
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
  // hook SharedPreferencesImpl.getString 的返回值
  try {
    var SP = Java.use('android.app.SharedPreferencesImpl');
    SP.getString.overload('java.lang.String', 'java.lang.String').implementation = function (key, def) {
      var v = this.getString(key, def);
      try {
        var k = String(key).toLowerCase();
        if (v != null && (k.indexOf('token') >= 0 || k.indexOf('auth') >= 0 ||
            k.indexOf('sid') >= 0 || k.indexOf('secret') >= 0 || k.indexOf('login') >= 0 ||
            k.indexOf('key') >= 0 || k.indexOf('session') >= 0)) {
          log('SP_GET', String(key) + ' = ' + String(v).slice(0, 300));
        }
      } catch (e) {}
      return v;
    };
    log('HOOK', 'SharedPreferencesImpl.getString ok');
  } catch (e) { log('WARN', 'sp: ' + e); }
  log('READY', 'sp token dump installed');
});
