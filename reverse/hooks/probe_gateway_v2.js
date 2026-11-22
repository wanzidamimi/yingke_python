/*
 * 极简网关探测 v2：只 hook Builder setter 入参 + native connect
 * 避免批量方法遍历导致 ANR
 */
'use strict';
function log(t, s) { console.log('[GW2][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString().slice(0, 400); } catch (e) { return '<e>'; }
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

// native connect（多方式尝试）
try {
  var c = null;
  try { c = Module.getExportByName(null, 'connect'); } catch (e) {}
  if (!c) { try { c = Process.getModuleByName('libc.so').getExportByName('connect'); } catch (e) {} }
  if (!c) { try { c = Module.findExportByName(null, 'connect'); } catch (e) {} }
  log('CONNECT_ADDR', String(c));
  if (c) {
    Interceptor.attach(c, {
      onEnter: function (a) {
        try {
          var fam = Memory.readU16(a[1]);
          if (fam === 2) {
            var p = Memory.readU16(a[1].add(2));
            p = ((p & 0xff) << 8) | ((p >> 8) & 0xff);
            var ip = [Memory.readU8(a[1].add(4)), Memory.readU8(a[1].add(5)),
                      Memory.readU8(a[1].add(6)), Memory.readU8(a[1].add(7))].join('.');
            log('CONNECT', ip + ':' + p);
          } else log('CONNECT_FAM', 'family=' + fam);
        } catch (e) {}
      }
    });
    log('CONNECT_HOOK', 'ok');
  }
} catch (e) { log('WARN', 'connect: ' + e); }

Java.perform(function () {
  // 只 hook Builder 的 8 个 setter（a~h，参数是 Builder 类型的单参方法）
  try {
    var B = Java.use('tech.appshatcher.comm.facade.InKeConnClient$Builder');
    ['a','b','c','d','e','f','g','h','j','k','l','m','n','o'].forEach(function (n) {
      try {
        var fn = B[n];
        if (!fn) return;
        // 只 hook 第一个重载，参数为非 Builder 的（j~o 是配置 setter）
        for (var i = 0; i < fn.length; i++) {
          (function (ov) {
            var pts = [];
            try {
              // 从 overload 拿不到参数类型，直接用 implementation 覆盖所有重载
              ov.implementation = function () {
                var a = [];
                for (var k = 0; k < arguments.length; k++) a.push(js(arguments[k]));
                log('B.' + n, a.join(' | '));
                return ov.apply(this, arguments);
              };
            } catch (e) {}
          })(fn[i]);
        }
      } catch (e) {}
    });
    log('BUILDER_HOOK', 'ok');
  } catch (e) { log('WARN', 'builder: ' + e); }

  log('READY', 'v2 installed');
});
