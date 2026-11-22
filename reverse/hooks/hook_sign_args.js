/* hook om/a.c() 的真实调用参数，找出 Authorization 签名输入差异。 */
'use strict';

function log(tag, msg) {
  var line = '[SIGARGS][' + tag + '] ' + msg;
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

function arrHex(arr) {
  try {
    var out = '';
    var n = arr.length;
    for (var i = 0; i < n && i < 64; i++) out += ('0' + (arr[i] & 0xff).toString(16)).slice(-2);
    return out + (n > 64 ? '...' : '') + '(len=' + n + ')';
  } catch (e) { return '<err>'; }
}

setTimeout(function () {
  Java.perform(function () {
    try {
      var A = Java.use('om/a');
      var ovs = A.c.overloads;
      log('OVERLOADS', String(ovs.length));
      ovs.forEach(function (ov, idx) {
        ov.implementation = function () {
          try {
            log('CALL_' + idx,
              'p0=' + String(arguments[0]) +
              ' p1=' + arrHex(arguments[1]) +
              ' p2=' + String(arguments[2]) +
              ' p3=' + String(arguments[3]) +
              ' p4=' + String(arguments[4]) +
              ' p5=' + String(arguments[5])
            );
          } catch (e) { log('ARG_ERR_' + idx, String(e)); }
          var ret = ov.apply(this, arguments);
          try { log('SIG_' + idx, String(ret)); } catch (e) {}
          return ret;
        };
      });
      log('HOOK', 'om/a.c ok');
    } catch (e) { log('ERR', String(e)); }
  });
}, 300);
