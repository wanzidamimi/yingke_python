/*
 * 映客协议 hook 脚本（frida）
 * 目标：抓 TCP 长连接的明文 JSON、网关地址、RSA 加解密数据、HTTP 签名
 * 用法：frida -H 127.0.0.1:27042 -p <PID> -l hook_inke.js
 */
'use strict';

var LINE = '============================================================';
function log(tag, obj) {
    try {
        var s = (typeof obj === 'string') ? obj : JSON.stringify(obj);
        console.log('[INKE][' + tag + '] ' + s);
    } catch (e) {
        console.log('[INKE][' + tag + '] <unstringifiable> ' + String(obj));
    }
}
function safeJSON(o) {
    try { return JSON.stringify(o); } catch (e) { return String(o); }
}

/* ---------- 1. RoomMessageCenter: 弹幕明文 JSON ---------- */
function hookRoomMessageCenter() {
    var cls = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter';
    var C = Java.use(cls);
    log('HOOK', 'RoomMessageCenter loaded');

    // 订阅房间：拿到 liveId
    C.watchRoomMessage.overload('java.lang.String').implementation = function (s) {
        log('watchRoomMessage', { liveId: s });
        return this.watchRoomMessage(s);
    };

    // getEvent(JSONObject): 返回 event 名
    C.getEvent.overload('org.json.JSONObject').implementation = function (j) {
        var r = this.getEvent(j);
        log('getEvent', { json: safeJSON(j), result: r });
        return r;
    };

    // a(JSONObject): 返回 String
    C.a.overload('org.json.JSONObject').implementation = function (j) {
        var r = this.a(j);
        log('RoomCenter.a', { json: safeJSON(j), result: r });
        return r;
    };

    // b(RoomMessageCenter, JSONObject): void
    C.b.overload('com.meelive.ingkee.business.room.connection.RoomMessageCenter', 'org.json.JSONObject').implementation = function (self, j) {
        log('RoomCenter.b', safeJSON(j));
        return this.b(self, j);
    };

    // onMessage(RoomConnMessage): 核心消息入口
    var inner = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';
    try {
        var IC = Java.use(inner);
        log('HOOK', 'RoomConnMessage fields: ' + IC.class.getDeclaredFields().map(function (f) { return f.getName() + ':' + f.getType().getName(); }).join(', '));
        IC.toString.implementation = function () {
            var r = this.toString();
            log('RoomConnMessage.toString', r);
            return r;
        };
    } catch (e) {
        log('WARN', 'RoomConnMessage hook fail: ' + e);
    }

    C.onMessage.overload(inner).implementation = function (m) {
        log('onMessage.RoomConnMessage', safeJSON(m));
        return this.onMessage(m);
    };
}

/* ---------- 2. RoomMessageObserver: 观察者回调（各业务分发） ---------- */
function hookObservers() {
    var names = [
        'com.meelive.ingkee.business.room.connection.RoomMessageObserver',
        'com.meelive.ingkee.business.room.connection.PlayRoomMessageObserver',
        'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage'
    ];
    names.forEach(function (n) {
        try {
            var C = Java.use(n);
            var methods = C.class.getDeclaredMethods();
            log('OBSERVER_METHODS', n + ' -> ' + methods.map(function (m) { return m.getName(); }).join(','));
        } catch (e) { log('WARN', 'observer ' + n + ' fail: ' + e); }
    });
}

/* ---------- 3. InKeConnClient: 网关地址 / 连接参数 ---------- */
function hookConnClient() {
    var cls = 'tech.appshatcher.comm.facade.InKeConnClient';
    try {
        var C = Java.use(cls);
        log('HOOK', 'InKeConnClient loaded');

        // Builder 构造：通常在这里设置 host/port/token
        var B = Java.use(cls + '$Builder');
        var bmethods = B.class.getDeclaredMethods();
        log('BUILDER_METHODS', B.class.getName() + ' -> ' +
            bmethods.map(function (m) { return m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')'; }).join(' | '));

        // hook Builder 所有返回 Builder 的方法（setter），打印参数
        bmethods.forEach(function (m) {
            var name = m.getName();
            var ptypes = m.getParameterTypes().map(function (p) { return p.getName(); });
            try {
                var overload = B[name];
                if (!overload) return;
                // 跳过无参
                if (ptypes.length === 0) return;
                var ov = overload.overload.apply(overload, ptypes);
                ov.implementation = function () {
                    var args = [];
                    for (var i = 0; i < arguments.length; i++) args.push(safeJSON(arguments[i]));
                    log('Builder.' + name, args.join(' | '));
                    return ov.apply(this, arguments);
                };
            } catch (e) { /* 某些重载 hook 失败忽略 */ }
        });

        // m/n/o(String, pj.b): 疑似订阅/发送命令
        ['m', 'n', 'o'].forEach(function (mn) {
            try {
                var ov = C[mn].overload('java.lang.String', 'pj.b');
                ov.implementation = function (s, b) {
                    log('ConnClient.' + mn, { arg: s, b: safeJSON(b) });
                    return ov.apply(this, arguments);
                };
            } catch (e) { log('WARN', 'ConnClient.' + mn + ' hook fail: ' + e); }
        });

        // l(bl.b, pj.b)
        try {
            C.l.overload('bl.b', 'pj.b').implementation = function (a, b) {
                log('ConnClient.l', { a: safeJSON(a), b: safeJSON(b) });
                return this.l(a, b);
            };
        } catch (e) { log('WARN', 'ConnClient.l fail: ' + e); }
    } catch (e) {
        log('WARN', 'InKeConnClient hook fail: ' + e);
    }
}

/* ---------- 4. InKeRsaManager: RSA 加解密 ---------- */
function hookRsa() {
    var cls = 'tech.appshatcher.comm.conn.core.rsa.InKeRsaManager';
    try {
        var C = Java.use(cls);
        log('HOOK', 'InKeRsaManager loaded');
        var methods = C.class.getDeclaredMethods();
        methods.forEach(function (m) {
            log('RSA_METHOD', m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')');
        });
        // 通用 hook：所有 public 方法打印入参/返回（限前 500 字符）
        methods.forEach(function (m) {
            var name = m.getName();
            var ptypes = m.getParameterTypes().map(function (p) { return p.getName(); });
            try {
                var fn = C[name];
                var ov = (ptypes.length ? fn.overload.apply(fn, ptypes) : fn.overload());
                ov.implementation = function () {
                    var args = [];
                    for (var i = 0; i < arguments.length; i++) {
                        var a = arguments[i];
                        if (typeof a === 'string') args.push(a.length > 500 ? a.slice(0, 500) + '...' : a);
                        else if (a && a.toString) args.push(a.toString().slice(0, 500));
                        else args.push(String(a));
                    }
                    var r = ov.apply(this, arguments);
                    log('RSA.' + name, { in: args, out: (r && r.toString ? r.toString().slice(0, 500) : String(r)) });
                    return r;
                };
            } catch (e) { /* ignore */ }
        });
    } catch (e) { log('WARN', 'RSA hook fail: ' + e); }
}

/* ---------- 5. 网络签名拦截器 ---------- */
function hookSigner() {
    var cls = 'tech.appshatcher.iknetworksigner.IKSecureSignInterceptor';
    try {
        var C = Java.use(cls);
        log('HOOK', 'IKSecureSignInterceptor loaded');
        var methods = C.class.getDeclaredMethods();
        methods.forEach(function (m) {
            log('SIGN_METHOD', m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')');
        });
    } catch (e) { log('WARN', 'Signer hook fail: ' + e); }
}

/* ---------- 6. String 工具：抓 URL / host 相关字符串 ---------- */
function hookUrls() {
    // 常见连接配置类：打印 toString 时若含 ws/http/ip 则记录
    var clsList = [
        'tech.appshatcher.comm.conn.tcp_channel.TcpChannelFactory',
        'tech.appshatcher.comm.conn.channel.factory.AHChannelFactory'
    ];
    clsList.forEach(function (cls) {
        try {
            var C = Java.use(cls);
            log('HOOK', cls + ' loaded');
            C.class.getDeclaredMethods().forEach(function (m) {
                log('CH_METHOD', cls.split('.').pop() + '.' + m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getSimpleName(); }).join(',') + ')');
            });
        } catch (e) { log('WARN', cls + ' fail: ' + e); }
    });
}

Java.perform(function () {
    log('START', LINE);
    log('TIME', new Date().toString());
    hookRoomMessageCenter();
    hookObservers();
    hookConnClient();
    hookRsa();
    hookSigner();
    hookUrls();
    log('READY', 'hooks installed');
});
