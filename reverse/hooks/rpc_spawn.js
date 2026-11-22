/*
 * spawn 模式专用：先装反退出 hook，再等待脱壳类出现后装弹幕 hook。
 * 用法：frida -D 127.0.0.1:5555 -f com.meelive.ingkee -l rpc_spawn.js
 */
'use strict';
var MSG_QUEUE = [];
var MAX_QUEUE = 5000;
var HOOK_READY = false;
function push(e, d) {
  MSG_QUEUE.push({ event: e, data: d, t: Date.now() });
  if (MSG_QUEUE.length > MAX_QUEUE) MSG_QUEUE.splice(0, MSG_QUEUE.length - MAX_QUEUE);
}
function js(o) {
  if (o == null) return 'null';
  if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
  try { return o.toString(); } catch (e) { return '<e>'; }
}
function log(t, s) { console.log('[SPAWN][' + t + '] ' + s); }

// ---- 顶层先装 native 反退出，越早越好 ----
function blockReturn(name, retType, args) {
  try {
    var addr = Module.findExportByName(null, name);
    if (!addr) return;
    Interceptor.replace(addr, new NativeCallback(function () {
      log('EXIT_BLOCKED', name);
      return retType === 'int' ? 0 : undefined;
    }, retType, args));
  } catch (e) {}
}
function blockKill(name, pidIdx, sigIdx) {
  try {
    var addr = Module.findExportByName(null, name);
    if (!addr) return;
    Interceptor.attach(addr, {
      onEnter: function (a) {
        var sig = a[sigIdx].toInt32();
        var pid = a[pidIdx].toInt32();
        this.b = (sig === 9 || sig === 6) && pid !== -1;
      },
      onLeave: function (r) { if (this.b) { log('KILL_BLOCKED', name); r.replace(0); } }
    });
  } catch (e) {}
}
blockKill('kill', 0, 1);
blockKill('tgkill', 1, 2);
blockKill('tkill', 0, 1);
blockKill('pthread_kill', 0, 1);
blockReturn('abort', 'void', []);
blockReturn('raise', 'int', ['int']);
blockReturn('exit', 'void', ['int']);
blockReturn('_exit', 'void', ['int']);
blockReturn('exit_group', 'void', ['int']);
log('NATIVE_ANTI', 'installed');

// ---- Java 层反退出 ----
function javaAnti() {
  try {
    var P = Java.use('android.os.Process');
    P.killProcess.overload('int').implementation = function (p) { log('PROCKILL_BLOCKED', String(p)); };
  } catch (e) {}
  try {
    var S = Java.use('java.lang.System');
    S.exit.overload('int').implementation = function (c) { log('SYSEXIT_BLOCKED', String(c)); };
  } catch (e) {}
  try {
    var R = Java.use('java.lang.Runtime');
    R.halt.overload('int').implementation = function (c) { log('HALT_BLOCKED', String(c)); };
  } catch (e) {}
}

// ---- 弹幕 hook，等脱壳类出现后安装 ----
function hookDanmu() {
  var MC = Java.use('com.meelive.ingkee.business.room.connection.RoomMessageCenter');
  var inner = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';
  MC.onMessage.overload(inner).implementation = function (m) {
    var d = '', e = '';
    try { d = js(m.data.value); } catch (x) {}
    try { e = js(m.event.value); } catch (x) {}
    push(e, d);
    return this.onMessage(m);
  };
  MC.watchRoomMessage.overload('java.lang.String').implementation = function (s) {
    log('WATCH', s);
    return this.watchRoomMessage(s);
  };
  HOOK_READY = true;
  log('READY', 'full hooks installed');
}

Java.perform(function () {
  javaAnti();
  var tries = 0;
  var timer = setInterval(function () {
    tries++;
    if (HOOK_READY) { clearInterval(timer); return; }
    try {
      hookDanmu();
      clearInterval(timer);
    } catch (e) {
      if (tries % 20 === 0) log('WAIT_CLASS', 'try=' + tries + ' ' + String(e).slice(0, 120));
      if (tries > 240) clearInterval(timer);
    }
  }, 500);
  setInterval(function () {
    if (!MSG_QUEUE.length) return;
    var batch = MSG_QUEUE.splice(0);
    batch.forEach(function (m) {
      var s = m.data || '';
      if (s.indexOf('"tp":"usernu"') < 0) log('MSG', m.event + ' | ' + s);
    });
  }, 3000);
});

rpc.exports = {
  drain: function () { var o = MSG_QUEUE; MSG_QUEUE = []; return o; },
  count: function () { return MSG_QUEUE.length; },
  clear: function () { MSG_QUEUE = []; return true; },
  status: function () { return HOOK_READY ? 'ready' : 'waiting'; }
};
