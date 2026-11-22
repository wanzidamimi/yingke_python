/* 在 App 内调用 IKSecureSignInterceptor.c() 给任意 URL 生成 Authorization。 */
'use strict';

var TARGET_URL = 'https://service.inke.cn/api/message/get?uid=779252212&liveid=1792755265153708&count=20&sign_from=android';

function log(tag, msg) {
  var line = '[SIGN][' + tag + '] ' + msg;
  console.log(line);
  try { send(line); } catch (e) {}
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

rpc.exports.sign = function (url) {
  return new Promise(function (resolve) {
    Java.perform(function () {
      try {
        var IK = Java.use('tech.appshatcher.iknetworksigner.IKSecureSignInterceptor');
        var app = Java.use('android.app.ActivityThread').currentApplication();
        var ctx = app ? app.getApplicationContext() : null;
        var inst = IK.$new(ctx);
        log('STEP', 'builder');
        var RB = Java.use('okhttp3/y$a');
        var b = RB.$new();
        log('STEP', 'url');
        b.m.overload('java.lang.String').call(b, url);
        log('STEP', 'get');
        b.d();
        log('STEP', 'build');
        var req = b.b();
        log('STEP', 'sign');
        var signed = inst.c(req);
        log('STEP', 'headers');
        var auth = signed.header('Authorization');
        var ts = signed.header('Client-TimeStamp');
        log('URL', url);
        log('AUTH', String(auth));
        log('TS', String(ts));
        resolve(String(auth) + '|' + String(ts));
      } catch (e) {
        log('ERR', String(e));
        resolve('');
      }
    });
  });
};

setTimeout(function () {
  rpc.exports.sign(TARGET_URL);
}, 1500);
