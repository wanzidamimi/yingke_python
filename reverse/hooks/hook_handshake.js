/*
 * 抓 App 私有 TCP 握手包：hook HandshakeRequest.a() 与 InKeRsaManager.encrypt()
 * 用法：frida -D 127.0.0.1:5555 -p <映客主进程PID> -l hook_handshake.js
 */
'use strict';

var RSA_TEST_HEX = '0001010020656531363531356634663338643136613637303833353537653866663061373100086162636465666768';

function log(tag, msg) {
  console.log('[HS][' + new Date().toISOString() + '][' + tag + '] ' + msg);
}

function hex(arr) {
  try {
    var out = '';
    for (var i = 0; i < arr.length; i++) {
      var v = arr[i] & 0xff;
      out += ('0' + v.toString(16)).slice(-2);
    }
    return out;
  } catch (e) { return '<hex-error:' + e + '>'; }
}

function dumpByteArray(tag, arr) {
  if (!arr) { log(tag, 'null'); return; }
  try {
    log(tag + '_LEN', String(arr.length));
    log(tag + '_HEX', hex(arr));
  } catch (e) { log(tag + '_ERR', String(e)); }
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
        if (n === 60 || n === 62 || n === 231) {
          log('ANTI', 'blocked syscall ' + n);
          args[0] = ptr(39);
        }
      }
    });
    log('ANTI', 'syscall hooked');
  }
} catch (e) { log('WARN', 'syscall hook: ' + e); }
['exit', '_exit', 'abort', 'raise'].forEach(function (n) {
  try {
    var a = findExport(n);
    if (!a) return;
    Interceptor.replace(a, new NativeCallback(function () {
      log('ANTI', 'blocked ' + n);
      return 0;
    }, 'int', []));
  } catch (e) {}
});
log('ANTI', 'kill/tgkill/exit hooked');

var captureSocketWrite = false;
var rsaHooked = false;
var hsHooked = false;

function installClassHooks() {
  Java.perform(function () {
    try {
      var Process = Java.use('android.os.Process');
      Process.killProcess.overload('int').implementation = function (pid) {
        log('ANTI', 'blocked Process.killProcess(' + pid + ')');
      };
      var Runtime = Java.use('java.lang.Runtime');
      Runtime.exit.overload('int').implementation = function (code) {
        log('ANTI', 'blocked Runtime.exit(' + code + ')');
      };
      Java.use('java.lang.System').exit.overload('int').implementation = function (code) {
        log('ANTI', 'blocked System.exit(' + code + ')');
      };
      log('HOOK', 'java exit hooks ok');
    } catch (e) { log('WARN', 'java exit hook: ' + e); }

    if (!rsaHooked) {
      try {
        var Rsa = Java.use('tech.appshatcher.comm.conn.core.rsa.InKeRsaManager');
        Rsa.encrypt.overload('[B').implementation = function (data) {
          dumpByteArray('RSA_PLAIN', data);
          try {
            var k = this.b();
            log('RSA_PUBLIC_ID', String(k.a));
            log('RSA_PUBLIC_KEY', String(k.b));
          } catch (e) { log('RSA_KEY_ERR', String(e)); }
          var out = this.encrypt(data);
          dumpByteArray('RSA_CIPHER', out);
          return out;
        };
        rsaHooked = true;
        log('HOOK', 'InKeRsaManager.encrypt ok');
      } catch (e) { log('WARN', 'rsa hook: ' + e); }
    }

    try {
      var SubReq = Java.use('ll/b');
      SubReq.a.overload('java.lang.String').implementation = function (s) {
        log('SUBSCRIBE_ID', String(s));
        return this.a(s);
      };
      log('HOOK', 'SubscribeRequest.a ok');
    } catch (e) { log('WARN', 'subscribe hook: ' + e); }

    try {
      var HttpBack = Java.use('ol/b');
      HttpBack.a.overload('int', 'int', 'java.lang.String', '[B').implementation = function (
        readTimeout, connTimeout, url, body
      ) {
        log('HTTP_BACKUP_URL', String(url));
        dumpByteArray('HTTP_BACKUP_BODY', body);
        return this.a(readTimeout, connTimeout, url, body);
      };
      log('HOOK', 'ol/b.a ok');
    } catch (e) { log('WARN', 'http backup hook: ' + e); }

    if (!hsHooked) {
      try {
        var HS = Java.use('zj/d');
        HS.a.overload().implementation = function () {
          try {
            log('HANDSHAKE_PACKET_TYPE', String(this.a.a()));
            log('HANDSHAKE_PUBLIC_ID', String(this.b.a()));
            log('HANDSHAKE_TOKEN', String(this.d));
            log('HANDSHAKE_NONCE', String(this.g));
            dumpByteArray('HANDSHAKE_TOKEN_BYTES', this.d);
            dumpByteArray('HANDSHAKE_NONCE_BYTES', this.f);
          } catch (e) { log('HS_FIELD_ERR', String(e)); }
          var out = this.a();
          dumpByteArray('HANDSHAKE_FINAL', out);
          captureSocketWrite = true;
          return out;
        };
        hsHooked = true;
        log('HOOK', 'HandshakeRequest.a ok');
      } catch (e) { log('WARN', 'handshake hook: ' + e); }
    }

    if (rsaHooked && hsHooked) {
      log('READY', 'handshake probe installed');
    } else {
      setTimeout(installClassHooks, 500);
    }
  });
}

['java.net.SocketOutputStream', 'java.net.Socket$SocketOutputStream'].forEach(function (cls) {
  try {
    var S = Java.use(cls);
    S.write.overloads.forEach(function (ov) {
      ov.implementation = function () {
        if (captureSocketWrite) {
          try { dumpByteArray('SOCKET_WRITE', arguments[0]); } catch (e) {}
          captureSocketWrite = false;
        }
        return ov.apply(this, arguments);
      };
    });
    log('HOOK', 'socket write ok: ' + cls);
  } catch (e) { log('WARN', 'socket hook ' + cls + ': ' + e); }
});

setTimeout(installClassHooks, 300);
setTimeout(function () {
  log('AUTO', 'trigger http backup');
  rpc.exports.httpBackup().then(function (n) { log('AUTO', 'http backup instances=' + n); });
}, 7000);

rpc.exports.reconnect = function () {
  return new Promise(function (resolve) {
    Java.perform(function () {
      var count = 0;
      Java.choose('tech.appshatcher.comm.facade.InKeConnClient', {
        onMatch: function (inst) {
          try { inst.g(); count++; } catch (e) { log('RECONNECT_ERR', String(e)); }
        },
        onComplete: function () { resolve(count); }
      });
    });
  });
};

rpc.exports.rsaEncrypt = function (hex) {
  return new Promise(function (resolve) {
    Java.perform(function () {
      var out = null;
      var bytes = Java.use('[B');
      var arr = bytes.new(hex.length / 2);
      for (var i = 0; i < hex.length / 2; i++) {
        arr[i] = parseInt(hex.substr(i * 2, 2), 16) & 0xff;
      }
      Java.choose('tech.appshatcher.comm.conn.core.rsa.InKeRsaManager', {
        onMatch: function (inst) {
          if (out) return;
          try {
            out = inst.encrypt(arr);
            log('RSA_TEST_OUT', hex(out));
          } catch (e) { log('RSA_TEST_ERR', String(e)); }
        },
        onComplete: function () {
          if (!out) {
            try {
              var cls = Java.use('tech.appshatcher.comm.conn.core.rsa.InKeRsaManager');
              var app = Java.use('android.app.ActivityThread').currentApplication();
              var ctx = app ? app.getApplicationContext() : null;
              var inst2 = cls.$new(ctx);
              out = inst2.encrypt(arr);
              log('RSA_TEST_OUT_NEW', hex(out));
            } catch (e) { log('RSA_TEST_NEW_ERR', String(e)); }
          }
          resolve(out ? hex(out) : '');
        }
      });
    });
  });
};

rpc.exports.forceReconnect = function () {
  return new Promise(function (resolve) {
    Java.perform(function () {
      var count = 0;
      Java.choose('pj/y', {
        onMatch: function (inst) {
          try { inst.z0(); count++; } catch (e) { log('FORCE_RECONNECT_ERR', String(e)); }
        },
        onComplete: function () { resolve(count); }
      });
    });
  });
};

rpc.exports.httpBackup = function () {
  return new Promise(function (resolve) {
    Java.perform(function () {
      var count = 0;
      Java.choose('ol/e', {
        onMatch: function (inst) {
          try { inst.g(); count++; } catch (e) { log('HTTP_BACKUP_ERR', String(e)); }
        },
        onComplete: function () { resolve(count); }
      });
    });
  });
};
