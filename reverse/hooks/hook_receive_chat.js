/* 直接打印房间层收到的 JSON，定位聊天接收内容。 */
'use strict';

function log(tag, msg) {
  var line = '[RECV][' + tag + '] ' + msg;
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

function safeJson(obj) {
  try {
    var s = obj.toString();
    return s.length > 3000 ? s.slice(0, 3000) + '...' : s;
  } catch (e) { return '<err>'; }
}

setTimeout(function () {
  Java.perform(function () {
    try {
      var Z = Java.use('zk/e');
      Z.r.overload('org.json.JSONObject').implementation = function (j) {
        log('ZK_R', safeJson(j));
        return this.r(j);
      };
      log('HOOK', 'zk/e.r ok');
    } catch (e) { log('WARN', 'zk/e.r: ' + e); }

    try {
      var P = Java.use('com.meelive.ingkee.business.room.model.manager.PublicMessageManager');
      P.handleMessage.overload('org.json.JSONObject').implementation = function (j) {
        log('PM_HANDLE', safeJson(j));
        return this.handleMessage(j);
      };
      log('HOOK', 'PublicMessageManager.handleMessage ok');
    } catch (e) { log('WARN', 'PM.handleMessage: ' + e); }

    try {
      var M = Java.use('com.meelive/ingkee/business/room/model/manager/RoomManager'.replace('/', '.'));
      M.onMessage.overload('java.lang.String', 'org.json.JSONObject').implementation = function (s, j) {
        log('ROOM_ON', s + ' ' + safeJson(j));
        return this.onMessage(s, j);
      };
      log('HOOK', 'RoomManager.onMessage ok');
    } catch (e) { log('WARN', 'RoomManager.onMessage: ' + e); }

    log('READY', 'receive hook installed');
  });
}, 300);
