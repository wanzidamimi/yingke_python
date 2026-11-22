/*
 * 映客协议 hook v3：抓 TCP 网关地址（socket connect / Builder 配置）+ 所有 JSON 消息落盘
 */
'use strict';
function jstr(o) {
    if (o === null) return 'null';
    if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
    try { return o.toString(); } catch (e) { return '<err>'; }
}
function log(tag, s) { console.log('[INKE3][' + tag + '] ' + s); }

Java.perform(function () {
    log('START', new Date().toString());

    /* 1. java.net.Socket.connect —— 抓所有出站连接地址 */
    try {
        var Socket = Java.use('java.net.Socket');
        Socket.connect.overload('java.net.SocketAddress', 'int').implementation = function (addr, timeout) {
            log('SOCK_CONNECT', jstr(addr));
            return this.connect(addr, timeout);
        };
        Socket.connect.overload('java.net.SocketAddress').implementation = function (addr) {
            log('SOCK_CONNECT', jstr(addr));
            return this.connect(addr);
        };
        log('HOOK', 'Socket.connect ok');
    } catch (e) { log('WARN', 'socket: ' + e); }

    /* 2. InetSocketAddress 构造 —— 记录 host:port */
    try {
        var ISA = Java.use('java.net.InetSocketAddress');
        // 构造时记录（用 $init）
        var inits = ISA.class.getDeclaredConstructors();
        log('ISA_CTORS', String(inits.length));
    } catch (e) {}

    /* 3. 所有 RoomMessageCenter 消息完整落盘（只打 ONMSG，带 UTF-8）*/
    try {
        var MC = Java.use('com.meelive.ingkee.business.room.connection.RoomMessageCenter');
        var inner = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';
        MC.onMessage.overload(inner).implementation = function (m) {
            var data = '';
            try { data = jstr(m.data.value); } catch (e) { data = 'ERR'; }
            // 只打含 chat/评论的消息 或 全部（这里全打）
            log('MSG', data);
            return this.onMessage(m);
        };
        log('HOOK', 'onMessage ok');
    } catch (e) { log('WARN', 'MC: ' + e); }

    /* 4. hook 连接协议门面所有方法（m/n/o/l）—— 找订阅命令 */
    try {
        var C = Java.use('tech.appshatcher.comm.facade.InKeConnClient');
        ['m','n','o','l'].forEach(function (mn) {
            try {
                var ms = C[mn];
                // 枚举所有重载
                for (var i = 0; i < ms.length; i++) {
                    (function (ov, idx) {
                        ov.implementation = function () {
                            var args = [];
                            for (var k = 0; k < arguments.length; k++) args.push(jstr(arguments[k]).slice(0, 1000));
                            log('CONN.' + mn + '#' + idx, args.join(' | '));
                            return ov.apply(this, arguments);
                        };
                    })(ms[i], i);
                }
            } catch (e) {}
        });
        log('HOOK', 'conn methods ok');
    } catch (e) { log('WARN', 'conn: ' + e); }

    /* 5. hook 配置类：打印所有静态 String 字段（常含 host）*/
    try {
        var CFG = [
            'tech.appshatcher.comm.BuildConfig',
            'com.meelive.ingkee.connectioncomponent.BuildConfig',
            'tech.appshatcher.comm.conn.tcp_channel.socket.RandomChannelId'
        ];
        CFG.forEach(function (n) {
            try {
                var C = Java.use(n);
                var fs = C.class.getDeclaredFields();
                var out = [];
                fs.forEach(function (f) {
                    try {
                        var v = C[f.getName()].value;
                        if (typeof v === 'string' && v.length < 300) out.push(f.getName() + '=' + v);
                    } catch (e) {}
                });
                log('CFG', n + ' -> ' + out.join(', '));
            } catch (e) {}
        });
    } catch (e) {}

    log('READY', 'v3 installed');
});
