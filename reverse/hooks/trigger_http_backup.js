/* 主动触发 ol/e.g() 并打印 ol/b.a 的 URL/body。 */
'use strict';

function log(tag, msg) { console.log('[HTTP][' + new Date().toISOString() + '][' + tag + '] ' + msg); }
function hex(arr) {
  if (!arr) return '';
  var out = '';
  for (var i = 0; i < arr.length; i++) out += ('0' + (arr[i] & 0xff).toString(16)).slice(-2);
  return out;
}
function findExport(name) {
  try { return Module.getGlobalExportByName(name); } catch (e) { return null; }
}
function bk(name, pi, si) {
  try {
    var a = findExport(name);
    if (!a) return;
    Interceptor.attach(a, {
      onEnter: function (x) { this.b = (x[si].toInt32() === 9 || x[si].toInt32() === 6) && x[pi].toInt32() !== -1; },
      onLeave: function (r) { if (this.b) r.replace(0); }
    });
  } catch (e) {}
}
bk('kill', 0, 1);
bk('tgkill', 1, 2);
bk('pthread_kill', 0, 1);
['exit', '_exit', 'abort', 'raise'].forEach(function (n) {
  try {
    var a = findExport(n);
    if (a) Interceptor.replace(a, new NativeCallback(function () { return 0; }, 'int', []));
  } catch (e) {}
});
log('ANTI', 'ready');

Java.perform(function () {
  try {
    var H = Java.use('ol/b');
    H.a.overload('int', 'int', 'java.lang.String', '[B').implementation = function (rt, ct, url, body) {
      log('URL', String(url));
      log('BODY_HEX', hex(body));
      log('BODY_LEN', String(body.length));
      return this.a(rt, ct, url, body);
    };
    log('HOOK', 'ol/b.a ok');
  } catch (e) { log('ERR', 'ol/b.a hook: ' + e); }

  setTimeout(function () {
    Java.perform(function () {
      var count = 0;
      Java.choose('ol/e', {
        onMatch: function (inst) {
          count++;
          try { inst.g(); log('TRIGGER', 'ol/e.g called'); }
          catch (e) { log('ERR', 'ol/e.g: ' + e); }
        },
        onComplete: function () { log('DONE', 'instances=' + count); }
      });
    });
  }, 1500);
});
