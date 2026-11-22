/* 最小 HTTP 备份订阅探针：只 hook ol/a.a、ol/b.a、ol/e.g，并主动触发 ol/e.g()。 */
'use strict';

function log(tag, msg) {
  var line = '[MIN][' + new Date().toISOString() + '][' + tag + '] ' + msg;
  console.log(line);
  try { send(line); } catch (e) {}
}
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

var tries = 0;
function installAndTrigger() {
  Java.perform(function () {
    try {
      var A = Java.use('ol/a');
      A.a.overload().implementation = function () {
        var r = this.a();
        log('BACKUP_URI', String(r));
        return r;
      };
      log('HOOK', 'ol/a.a ok');
    } catch (e) { log('WARN', 'ol/a.a: ' + e); }

    try {
      var B = Java.use('ol/b');
      B.a.overload('int', 'int', 'java.lang.String', '[B').implementation = function (rt, ct, url, body) {
        log('HTTP_URL', String(url));
        log('HTTP_BODY_HEX', hex(body));
        log('HTTP_BODY_LEN', String(body.length));
        return this.a(rt, ct, url, body);
      };
      log('HOOK', 'ol/b.a ok');
    } catch (e) { log('WARN', 'ol/b.a: ' + e); }

    try {
      var E = Java.use('ol/e');
      E.g.overload().implementation = function () {
        log('OL_E_G_CALLED');
        return this.g();
      };
      log('HOOK', 'ol/e.g ok');
    } catch (e) { log('WARN', 'ol/e.g: ' + e); }

    var count = 0;
    Java.choose('ol/e', {
      onMatch: function (inst) {
        count++;
        try { inst.g(); log('TRIGGER', 'called on instance ' + count); }
        catch (e) { log('ERR', 'trigger: ' + e); }
      },
      onComplete: function () {
        log('DONE', 'instances=' + count);
        if (count === 0 && tries++ < 90) setTimeout(installAndTrigger, 1000);
      }
    });
  });
}

function waitJava() {
  if (typeof Java === 'undefined') {
    setTimeout(waitJava, 500);
    return;
  }
  installAndTrigger();
}
setTimeout(waitJava, 500);

rpc.exports.install = function () {
  waitJava();
};
