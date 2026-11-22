/*
 * spawn 模式抓 native connect：在 App 启动瞬间捕获所有出站 TCP 地址
 * 不依赖 Java/dex，所以不受"脱壳类未加载"影响
 * 用法：frida -D 127.0.0.1:5555 -f com.meelive.ingkee -l probe_connect_spawn.js
 */
'use strict';
function log(t, s) { console.log('[CSP][' + t + '] ' + s); }

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

var c = null;
try { c = Module.getExportByName(null, 'connect'); } catch (e) {}
if (!c) { try { c = Process.getModuleByName('libc.so').getExportByName('connect'); } catch (e) {} }
log('CONNECT_ADDR', String(c));
if (c) {
  Interceptor.attach(c, {
    onEnter: function (a) {
      try {
        var fam = Memory.readU16(a[1]);
        if (fam === 2) {
          var raw = Memory.readU16(a[1].add(2));
          var p = ((raw & 0xff) << 8) | ((raw >> 8) & 0xff);
          var ip = [Memory.readU8(a[1].add(4)), Memory.readU8(a[1].add(5)),
                    Memory.readU8(a[1].add(6)), Memory.readU8(a[1].add(7))].join('.');
          log('TCP', ip + ':' + p);
        } else if (fam === 10) {
          log('TCP', '[ipv6]');
        } else {
          log('TCP_FAM', 'family=' + fam);
        }
      } catch (e) { log('ERR', String(e)); }
    }
  });
  log('READY', 'native connect hook installed');
}
