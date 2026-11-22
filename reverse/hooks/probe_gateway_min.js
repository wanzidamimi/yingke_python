/*
 * 最小网关探测：纯接口方案可行性验证第一步
 * 目标：看 TCP 网关地址是否明文可见（Builder 参数 / native connect / 配置字段）
 * 用法：frida -D 127.0.0.1:5555 -p <PID> -l probe_gateway_min.js
 */
'use strict';
function log(t, s) { console.log('[PROBE][' + t + '] ' + s); }
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString(); } catch (e) { return '<e>'; }
}

// ---- 反反调试（复用 rpc_full.js 思路，顶层先装）----
function blockKill(name, pi, si) {
  try {
    var a = Module.findExportByName(null, name);
    if (!a) return;
    Interceptor.attach(a, {
      onEnter: function (x) {
        var sig = x[si].toInt32(), pid = x[pi].toInt32();
        this.b = (sig === 9 || sig === 6) && pid !== -1;
      },
      onLeave: function (r) { if (this.b) r.replace(0); }
    });
  } catch (e) {}
}
blockKill('kill', 0, 1);
blockKill('tgkill', 1, 2);
function noop(name, ret, args) {
  try {
    var a = Module.findExportByName(null, name);
    if (a) Interceptor.replace(a, new NativeCallback(function () {
      return ret === 'int' ? 0 : undefined;
    }, ret, args));
  } catch (e) {}
}
noop('exit', 'void', ['int']);
noop('_exit', 'void', ['int']);
noop('exit_group', 'void', ['int']);
noop('abort', 'void', []);
log('NATIVE_ANTI', 'ok');

// ---- native 层 connect/getaddrinfo：抓真实 socket 目标 ----
try {
  var connect = Module.findExportByName(null, 'connect');
  if (connect) {
    Interceptor.attach(connect, {
      onEnter: function (args) {
        try {
          var sa = args[1];
          var fam = Memory.readU16(sa);
          var out = 'family=' + fam;
          if (fam === 2) {
            var port = (Memory.readU16(sa.add(2)) & 0xffff);
            port = ((port & 0xff) << 8) | ((port >> 8) & 0xff);
            var ip = [Memory.readU8(sa.add(4)), Memory.readU8(sa.add(5)),
                      Memory.readU8(sa.add(6)), Memory.readU8(sa.add(7))].join('.');
            out = ip + ':' + port;
          } else if (fam === 10) {
            out = '[ipv6]:' + ((Memory.readU16(sa.add(2)) & 0xff) << 8 |
                  (Memory.readU16(sa.add(2)) >> 8));
          }
          log('NATIVE_CONNECT', out);
        } catch (e) { log('NATIVE_CONNECT_ERR', String(e)); }
      }
    });
    log('HOOK', 'native connect ok');
  } else { log('WARN', 'connect not found'); }
} catch (e) { log('WARN', 'connect hook: ' + e); }

// ---- Java 层 ----
Java.perform(function () {
  // 1. Builder 所有方法入参
  try {
    var B = Java.use('tech.appshatcher.comm.facade.InKeConnClient$Builder');
    var ms = B.class.getDeclaredMethods();
    log('BUILDER_METHODS', ms.map(function (m) {
      return m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')';
    }).join(' | '));
    ms.forEach(function (m) {
      var name = m.getName();
      var pts = m.getParameterTypes().map(function (p) { return p.getName(); });
      if (!pts.length) return;
      try {
        var fn = B[name];
        var ov = fn.overload.apply(fn, pts);
        ov.implementation = function () {
          var a = [];
          for (var i = 0; i < arguments.length; i++) a.push(js(arguments[i]).slice(0, 500));
          log('Builder.' + name, a.join(' | '));
          return ov.apply(this, arguments);
        };
      } catch (e) {}
    });
    log('HOOK', 'Builder ok');
  } catch (e) { log('WARN', 'Builder: ' + e); }

  // 2. InKeConnClient 全部静态方法（构造入口常在静态工厂）
  try {
    var C = Java.use('tech.appshatcher.comm.facade.InKeConnClient');
    C.class.getDeclaredMethods().forEach(function (m) {
      log('CONN_METHOD', m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')');
    });
  } catch (e) { log('WARN', 'InKeConnClient: ' + e); }

  // 3. RSA 管理器的字段（可能含公钥）
  try {
    var R = Java.use('tech.appshatcher.comm.conn.core.rsa.InKeRsaManager');
    R.class.getDeclaredFields().forEach(function (f) {
      try {
        var v = R[f.getName()].value;
        log('RSA_FIELD', f.getName() + '=' + js(v).slice(0, 300));
      } catch (e) {}
    });
    R.class.getDeclaredMethods().forEach(function (m) {
      log('RSA_METHOD', m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')');
    });
  } catch (e) { log('WARN', 'RSA: ' + e); }

  // 4. 固定配置类的 host 样式字段（避免全量枚举导致超时）
  var CFG = [
    'tech.appshatcher.comm.BuildConfig',
    'com.meelive.ingkee.connectioncomponent.BuildConfig',
    'tech.appshatcher.comm.facade.InKeConnClient$Builder',
    'tech.appshatcher.comm.conn.tcp_channel.TcpChannelFactory'
  ];
  CFG.forEach(function (name) {
    try {
      var C = Java.use(name);
      C.class.getDeclaredFields().forEach(function (f) {
        try {
          var v = C[f.getName()].value;
          if (v != null && js(v).length < 200) log('CFG_FIELD', name + '.' + f.getName() + '=' + js(v));
        } catch (e) {}
      });
    } catch (e) {}
  });
  log('CFG_DONE', 'fixed config scan done');

  log('READY', 'gateway probe installed');
});
