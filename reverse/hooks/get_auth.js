/* 直接调用 App 内部的 om/a.c() 生成 Authorization，避免构造 okhttp Request。 */
'use strict';

var TARGET_QUERY = 'cc=TG36064&dev_name=Google&ik_appid=OklL&code1462295386=1795230572000&xid=1&cv=IK9.9.05_Android&ast=1&lc=3726b262d726e165&sign_from=android&ua=GooglePixel3&osversion=android_28&uid=779252212&liveid=1792755265153708&count=20';
var SAMPLE_QUERY = 'cc=TG36064&dev_name=Google&ik_appid=OklL&xid=1&cv=IK9.9.05_Android&ast=1&lc=3726b262d726e165&sign_from=android&ua=GooglePixel3&osversion=android_28&code585639254=1795231009064&md5=c633c886c5a233f2184a5a813dc5ac15';
var SAMPLE_TS = '1795231009065';
var SAMPLE_EXPECTED = '2YE0CRaVV7sAWJWJFtqkrpIBNUw=';

function log(tag, msg) {
  var line = '[AUTH][' + tag + '] ' + msg;
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

function makeAuth(query, ts) {
  var A = Java.use('om/a');
  var B = Java.use('om/b');
  var app = Java.use('android.app.ActivityThread').currentApplication();
  var ctx = app ? app.getApplicationContext() : null;
  var cfg = B.$new(ctx);
  var pkg = String(cfg.c());
  var appid = String(cfg.a());
  var secret = String(cfg.b());
  log('CFG', 'pkg=' + pkg + ' appid=' + appid + ' secret=' + secret);

  log('STEP', 'before body');
  var body = Java.array('byte', []);
  log('STEP', 'before sign');
  var sig = String(A.c(
    pkg,
    body,
    'GET',
    String(ts),
    String(query),
    secret
  ));
  return { appid: appid, sig: sig, auth: 'InkeV1 ' + appid + ':' + sig };
}

rpc.exports.generate = function (query) {
  return new Promise(function (resolve) {
    Java.perform(function () {
      try {
        var ts = String(Math.floor(Date.now() / 1000) * 1000);
        var out = makeAuth(query, ts);
        log('QUERY', query);
        log('TS', ts);
        log('AUTH', out.auth);
        resolve(JSON.stringify(out));
      } catch (e) {
        log('ERR', String(e));
        resolve('');
      }
    });
  });
};

setTimeout(function () {
  Java.perform(function () {
    try {
      var sample = makeAuth(SAMPLE_QUERY, SAMPLE_TS);
      log('SAMPLE_EXPECTED', SAMPLE_EXPECTED);
      log('SAMPLE_ACTUAL', sample.sig);
      log('SAMPLE_MATCH', String(sample.sig === SAMPLE_EXPECTED));
    } catch (e) {
      log('SAMPLE_ERR', String(e));
    }
    try {
      rpc.exports.generate(TARGET_QUERY);
    } catch (e) {
      log('TARGET_ERR', String(e));
    }
  });
}, 1500);
