/*
 * 早期 hook：通过 ClassLoader.loadClass 在目标类被加载的第一时间安装 hook。
 * 用法：frida -q -D emulator-5554 -f com.meelive.ingkee -t 60 -l hook_early.js
 */
'use strict';

var installed = {};
var TARGETS = [
  'cl/c',
  'zj/d',
  'tech.appshatcher.comm.conn.core.rsa.InKeRsaManager',
  'll/b',
  'ol/e',
  'ol/b'
];

function log(tag, msg) {
  console.log('[E][' + new Date().toISOString() + '][' + tag + '] ' + msg);
}

function hex(arr) {
  if (!arr) return '';
  var out = '';
  for (var i = 0; i < arr.length; i++) {
    out += ('0' + (arr[i] & 0xff).toString(16)).slice(-2);
  }
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
bk('pthread_kill', 0, 1);
try {
  var sc = findExport('syscall');
  if (sc) {
    Interceptor.attach(sc, {
      onEnter: function (args) {
        var n = args[0].toInt();
        if (n === 60 || n === 62 || n === 231) args[0] = ptr(39);
      }
    });
  }
} catch (e) {}
['exit', '_exit', 'abort', 'raise'].forEach(function (n) {
  try {
    var a = findExport(n);
    if (!a) return;
    Interceptor.replace(a, new NativeCallback(function () { return 0; }, 'int', []));
  } catch (e) {}
});
log('ANTI', 'native hooks installed');

function install(name) {
  if (installed[name]) return;
  installed[name] = true;
  Java.perform(function () {
    try {
      if (name === 'cl/c') {
        var C = Java.use('cl/c');
        C.h.overload('int').implementation = function (n) {
          var r = this.h(n);
          log('NONCE', r);
          return r;
        };
        log('HOOK', 'cl/c.h ok');
      } else if (name === 'zj/d') {
        var Z = Java.use('zj/d');
        Z.d.overload('long').implementation = function (gid) {
          var r = this.d(gid);
          log('TOKEN', 'gid=' + gid + ' token=' + r);
          return r;
        };
        Z.a.overload().implementation = function () {
          var out = this.a();
          log('HANDSHAKE_FINAL', hex(out));
          return out;
        };
        log('HOOK', 'zj/d ok');
      } else if (name === 'tech.appshatcher.comm.conn.core.rsa.InKeRsaManager') {
        var R = Java.use('tech.appshatcher.comm.conn.core.rsa.InKeRsaManager');
        R.encrypt.overload('[B').implementation = function (data) {
          log('RSA_PLAIN', hex(data));
          var k = this.b();
          log('RSA_KEY', String(k.a) + ' ' + String(k.b));
          var out = this.encrypt(data);
          log('RSA_CIPHER', hex(out));
          return out;
        };
        log('HOOK', 'InKeRsaManager ok');
      } else if (name === 'll/b') {
        var S = Java.use('ll/b');
        S.a.overload('java.lang.String').implementation = function (s) {
          log('SUBSCRIBE_ID', String(s));
          return this.a(s);
        };
        log('HOOK', 'll/b ok');
      } else if (name === 'ol/e') {
        var H = Java.use('ol/e');
        H.g.overload().implementation = function () {
          log('HTTP_BACKUP_TRIGGER');
          return this.g();
        };
        log('HOOK', 'ol/e.g ok');
      } else if (name === 'ol/b') {
        var B = Java.use('ol/b');
        B.a.overload('int', 'int', 'java.lang.String', '[B').implementation = function (rt, ct, url, body) {
          log('HTTP_BACKUP_URL', String(url));
          log('HTTP_BACKUP_BODY_HEX', hex(body));
          log('HTTP_BACKUP_BODY_LEN', String(body.length));
          return this.a(rt, ct, url, body);
        };
        log('HOOK', 'ol/b.a ok');
      }
    } catch (e) { log('HOOK_ERR', name + ': ' + e); }
  });
}

Java.perform(function () {
  var CL = Java.use('java.lang.ClassLoader');
  var ov = CL.loadClass.overloads;
  ov.forEach(function (m) {
    m.implementation = function () {
      var cls = m.apply(this, arguments);
      try {
        var name = String(arguments[0]);
        if (TARGETS.indexOf(name) >= 0) {
          log('CLASS_LOADED', name);
          setTimeout(function () { install(name); }, 0);
        }
      } catch (e) {}
      return cls;
    };
  });
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (TARGETS.indexOf(name) >= 0) setTimeout(function () { install(name); }, 0);
    },
    onComplete: function () {}
  });
  log('READY', 'ClassLoader.loadClass hooked');
  setTimeout(function () {
    Java.perform(function () {
      var count = 0;
      Java.choose('ol/e', {
        onMatch: function (inst) {
          count++;
          try { inst.g(); log('TRIGGER', 'ol/e.g called'); }
          catch (e) { log('TRIGGER_ERR', String(e)); }
        },
        onComplete: function () { log('TRIGGER_DONE', 'instances=' + count); }
      });
    });
  }, 3000);
});
