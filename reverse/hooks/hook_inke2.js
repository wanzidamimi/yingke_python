/*
 * 映客协议 hook v2：正确打印 JSONObject / 读 RoomConnMessage 字段 / hook 观察者
 */
'use strict';

function jstr(o) {
    if (o === null) return 'null';
    if (typeof o === 'string' || typeof o === 'number' || typeof o === 'boolean') return String(o);
    try { return o.toString(); } catch (e) { return '<err>'; }
}
function log(tag, s) { console.log('[INKE2][' + tag + '] ' + s); }

Java.perform(function () {
    log('START', new Date().toString());

    /* RoomConnMessage: 直接读 data/event 字段 */
    var inner = 'com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';
    try {
        var RC = Java.use(inner);
        var onMsg = RC.onMessage; // maybe not
        // hook RoomMessageCenter.onMessage 并读字段
        var MC = Java.use('com.meelive.ingkee.business.room.connection.RoomMessageCenter');
        MC.onMessage.overload(inner).implementation = function (m) {
            var data = '', event = '';
            try { data = jstr(m.data.value); } catch (e) { data = 'ERR:' + e; }
            try { event = jstr(m.event.value); } catch (e) { event = 'ERR:' + e; }
            log('ONMSG', 'event=' + event + ' data=' + data);
            return this.onMessage(m);
        };
        MC.watchRoomMessage.overload('java.lang.String').implementation = function (s) {
            log('WATCH', 'liveId=' + s);
            return this.watchRoomMessage(s);
        };
        MC.getEvent.overload('org.json.JSONObject').implementation = function (j) {
            var r = this.getEvent(j);
            log('GETEVENT', 'in=' + jstr(j) + ' out=' + r);
            return r;
        };
        MC.a.overload('org.json.JSONObject').implementation = function (j) {
            var r = this.a(j);
            log('CTR_A', 'in=' + jstr(j) + ' out=' + r);
            return r;
        };
        MC.b.overload('com.meelive.ingkee.business.room.connection.RoomMessageCenter', 'org.json.JSONObject').implementation = function (self, j) {
            log('CTR_B', jstr(j));
            return this.b(self, j);
        };
        log('HOOK', 'RoomMessageCenter ok');
    } catch (e) { log('WARN', 'MC: ' + e); }

    /* RoomMessageObserver 接口所有实现类：hook onMessage(...) */
    try {
        var Observer = Java.use('com.meelive.ingkee.business.room.connection.RoomMessageObserver');
        var ms = Observer.class.getDeclaredMethods();
        ms.forEach(function (m) { log('OBS_IFACE', m.getName() + '(' + m.getParameterTypes().map(function (p) { return p.getName(); }).join(',') + ')'); });
    } catch (e) { log('WARN', 'observer iface: ' + e); }

    /* 枚举已加载类里所有名字含 RoomMessageObserver / MessageObserver 的实现，hook 其 onMessage(JSONObject) */
    try {
        Java.enumerateClassLoaders({
            onMatch: function (loader) {
                try {
                    Java.classFactory.loader = loader;
                    var cls = Java.classFactory.use('com.meelive.ingkee.business.room.connection.RoomMessageObserver');
                    // 用 Java.use 已足够，实现类用 enumerateLoadedClasses
                } catch (e) {}
            },
            onComplete: function () {}
        });
    } catch (e) {}

    // hook 所有已加载类中，方法名为 onMessage 且参数含 JSONObject 的（聚焦 room/conn/inkee 包）
    try {
        Java.enumerateLoadedClasses({
            onMatch: function (name) {
                if (!/com\.meelive\.ingkee\.business\.room|com\.meelive\.ingkee\.imchat|com\.ingkee\.gift\.delegate\.barrage/.test(name)) return;
                if (name.indexOf('$') >= 0) return;
                try {
                    var C = Java.use(name);
                    var ms = C.class.getDeclaredMethods();
                    ms.forEach(function (m) {
                        if (m.getName() !== 'onMessage' && m.getName() !== 'update') return;
                        var pts = m.getParameterTypes().map(function (p) { return p.getName(); });
                        // 只 hook 含 JSONObject/String 的方法
                        if (pts.indexOf('org.json.JSONObject') < 0 && pts.indexOf('java.lang.String') < 0) return;
                        try {
                            var fn = C[m.getName()];
                            var ov = fn.overload.apply(fn, pts);
                            ov.implementation = function () {
                                var args = [];
                                for (var i = 0; i < arguments.length; i++) args.push(jstr(arguments[i]).slice(0, 1200));
                                log('OB_CALL', name.split('.').pop() + '.' + m.getName() + '(' + pts.map(function (p) { return p.split('.').pop(); }).join(',') + ') ' + args.join(' | '));
                                return ov.apply(this, arguments);
                            };
                        } catch (e) {}
                    });
                } catch (e) {}
            },
            onComplete: function () { log('HOOK', 'observer scan done'); }
        });
    } catch (e) { log('WARN', 'enum: ' + e); }

    /* InKeConnClient.Builder: hook 所有 setter 打印 toString */
    try {
        var B = Java.use('tech.appshatcher.comm.facade.InKeConnClient$Builder');
        B.class.getDeclaredMethods().forEach(function (m) {
            var name = m.getName();
            var pts = m.getParameterTypes().map(function (p) { return p.getName(); });
            if (pts.length === 0) return;
            try {
                var fn = B[name];
                var ov = fn.overload.apply(fn, pts);
                ov.implementation = function () {
                    var args = [];
                    for (var i = 0; i < arguments.length; i++) args.push(jstr(arguments[i]).slice(0, 800));
                    log('BLD', name + '(' + pts.map(function (p) { return p.split('.').pop(); }).join(',') + ') ' + args.join(' | '));
                    return ov.apply(this, arguments);
                };
            } catch (e) {}
        });
        log('HOOK', 'Builder ok');
    } catch (e) { log('WARN', 'Builder: ' + e); }

    log('READY', 'v2 hooks installed');
});
