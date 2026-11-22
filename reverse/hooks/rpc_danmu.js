/*
 * Frida RPC 弹幕提取脚本（APP 端）
 * 挂载后用 rpc.exports.get_messages() 拉取缓存的明文弹幕 JSON。
 * Python 端轮询调用，实现"实时提取"（无需复刻私有 TCP/RSA）。
 */
'use strict';

var MSG_QUEUE = [];
var MAX_QUEUE = 5000;

function pushMsg(event, data) {
    MSG_QUEUE.push({ event: event, data: data, t: Date.now() });
    if (MSG_QUEUE.length > MAX_QUEUE) MSG_QUEUE.splice(0, MSG_QUEUE.length - MAX_QUEUE);
}

function jstr(o) {
    if (o === null) return 'null';
    if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
    try { return o.toString(); } catch (e) { return '<err>'; }
}

function installHooks() {
    console.log('[RPC] installing...');
    try {
        var MC = Java.use('com.meelive.ingkee.business.room.connection.RoomMessageCenter');
        var inner = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';

        MC.onMessage.overload(inner).implementation = function (m) {
            var data = '', event = '';
            try { data = jstr(m.data.value); } catch (e) { data = 'ERR'; }
            try { event = jstr(m.event.value); } catch (e) { event = ''; }
            pushMsg(event, data);
            return this.onMessage(m);
        };

        MC.watchRoomMessage.overload('java.lang.String').implementation = function (s) {
            console.log('[RPC] watching liveId=' + s);
            return this.watchRoomMessage(s);
        };
        console.log('[RPC] hooks installed');
    } catch (e) {
        console.log('[RPC] hook error: ' + e);
    }
}

if (typeof Java !== 'undefined' && Java.available) {
    Java.perform(installHooks);
} else {
    console.log('[RPC] Java not available at load time');
}

/* RPC 导出：Python 调用 */
rpc.exports = {
    // 拉取并清空当前消息缓存
    drain: function () {
        var out = MSG_QUEUE;
        MSG_QUEUE = [];
        return out;
    },
    // 只看缓存数量
    count: function () {
        return MSG_QUEUE.length;
    },
    // 清空
    clear: function () {
        MSG_QUEUE = [];
        return true;
    },
    // 健康探针
    ping: function () {
        return 'pong-' + Date.now();
    }
};
