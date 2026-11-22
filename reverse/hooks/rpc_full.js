/*
 * 完整方案：反反调试 + 弹幕 hook + RPC 导出
 * 用法：Python frida attach 后加载，rpc.exports.drain() 拉明文弹幕
 */
'use strict';
var MSG_QUEUE = [];
var MAX_QUEUE = 5000;
function push(e,d){ MSG_QUEUE.push({event:e,data:d,t:Date.now()}); if(MSG_QUEUE.length>MAX_QUEUE) MSG_QUEUE.splice(0,MSG_QUEUE.length-MAX_QUEUE); }
function js(o){ if(o==null)return 'null'; if(typeof o==='string'||typeof o==='number'||typeof o==='boolean')return String(o); try{return o.toString();}catch(e){return '<e>';} }
function log(t,s){ console.log('[FULL]['+t+'] '+s); }

// ---- 反反调试：拦截自杀式退出 ----
function antiAnti(){
    try {
        var kill=Module.findExportByName(null,'kill');
        if(kill) Interceptor.attach(kill,{
            onEnter:function(a){ var pid=a[0].toInt32(), sig=a[1].toInt32(); if((sig===9||sig===6)&&pid>0){ this.b=true; } },
            onLeave:function(r){ if(this.b) r.replace(0); }
        });
    } catch(e){}
    try { var ex=Module.findExportByName(null,'exit'); if(ex) Interceptor.replace(ex,new NativeCallback(function(c){ log('EXIT_BLOCKED',String(c)); },'void',['int'])); } catch(e){}
    try { var P=Java.use('android.os.Process'); P.killProcess.overload('int').implementation=function(p){ log('PROCKILL_BLOCKED',String(p)); }; } catch(e){}
    try { var S=Java.use('java.lang.System'); S.exit.overload('int').implementation=function(c){ log('SYSEXIT_BLOCKED',String(c)); }; } catch(e){}
}

// ---- 弹幕 hook ----
function hookDanmu(){
    var MC=Java.use('com.meelive.ingkee.business.room.connection.RoomMessageCenter');
    var inner='com.meelive.ingkee.business.room.connection.RoomMessageCenter$RoomConnMessage';
    MC.onMessage.overload(inner).implementation=function(m){
        var d='',e=''; try{d=js(m.data.value);}catch(x){} try{e=js(m.event.value);}catch(x){}
        push(e,d);
        return this.onMessage(m);
    };
    MC.watchRoomMessage.overload('java.lang.String').implementation=function(s){ log('WATCH',s); return this.watchRoomMessage(s); };
}

Java.perform(function(){
    log('START',new Date().toString());
    antiAnti();
    hookDanmu();
    setInterval(function(){
        if(MSG_QUEUE.length){
            var batch=MSG_QUEUE.splice(0);
            batch.forEach(function(m){
                var s=m.data||'';
                // 只打印非人数刷新的消息，减少噪声
                if(s.indexOf('"tp":"usernu"')<0) log('MSG', m.event+' | '+s);
            });
        }
    }, 3000);
    log('READY','full hooks installed + auto-dump');
});

rpc.exports = {
    drain:function(){ var o=MSG_QUEUE; MSG_QUEUE=[]; return o; },
    count:function(){ return MSG_QUEUE.length; },
    clear:function(){ MSG_QUEUE=[]; return true; },
    ping:function(){ return 'pong-'+Date.now(); }
};
