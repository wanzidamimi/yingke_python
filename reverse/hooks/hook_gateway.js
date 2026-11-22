/*
 * 抓 TCP 网关：hook Socket/通道工厂/连接管理器，找弹幕 TCP 的 host:port
 */
'use strict';
function js(o){ if(o==null)return 'null'; if(typeof o==='string'||typeof o==='number'||typeof o==='boolean')return String(o); try{return o.toString();}catch(e){return '<e>';} }
function log(t,s){ console.log('[GW]['+t+'] '+s); }
Java.perform(function(){
    log('START',new Date().toString());

    // 1. 所有 Socket 构造与 connect（含 Netty/NioSocketChannel 以外的 java.net.Socket）
    try {
        var S=Java.use('java.net.Socket');
        S.$init.overload().implementation=function(){ log('SOCK_NEW',''); return this.$init(); };
        var connects=S.class.getDeclaredMethods().filter(function(m){return m.getName()==='connect';});
        log('SOCK_CONNECT_METHODS',String(connects.length));
    } catch(e){ log('WARN','socket '+e); }

    // 2. InetSocketAddress 构造（createUnresolved / 构造器）
    try {
        var ISA=Java.use('java.net.InetSocketAddress');
        var cs=ISA.class.getDeclaredConstructors();
        log('ISA_CTORS',String(cs.length));
        // hook 常见构造 String,int
        try { ISA.$init.overload('java.lang.String','int').implementation=function(h,p){ log('ISA','host='+h+' port='+p); return this.$init(h,p); }; } catch(e){}
        try { ISA.$init.overload('java.net.InetAddress','int').implementation=function(a,p){ log('ISA_ADDR','addr='+js(a)+' port='+p); return this.$init(a,p); }; } catch(e){}
    } catch(e){ log('WARN','isa '+e); }

    // 3. TcpChannelFactory 全部方法
    try {
        var T=Java.use('tech.appshatcher.comm.conn.tcp_channel.TcpChannelFactory');
        T.class.getDeclaredMethods().forEach(function(m){
            var n=m.getName(); var pts=m.getParameterTypes().map(function(p){return p.getName();});
            try {
                var fn=T[n]; var ov = pts.length? fn.overload.apply(fn,pts): fn.overload();
                ov.implementation=function(){
                    var a=[]; for(var i=0;i<arguments.length;i++) a.push(js(arguments[i]).slice(0,600));
                    var r=ov.apply(this,arguments);
                    log('TCP.'+n, a.join(' | ')+' -> '+js(r).slice(0,300));
                    return r;
                };
            } catch(e){}
        });
        log('HOOK','TcpChannelFactory ok');
    } catch(e){ log('WARN','tcp '+e); }

    // 4. ConnectionServiceImpl 方法（可能含 host 配置）
    try {
        var C=Java.use('com.meelive.ingkee.conn.impl.ConnectionServiceImpl');
        C.class.getDeclaredMethods().forEach(function(m){
            log('CONNIMPL_METHOD', m.getName()+'('+m.getParameterTypes().map(function(p){return p.getSimpleName();}).join(',')+')');
        });
    } catch(e){ log('WARN','connimpl '+e); }

    // 5. 枚举所有已加载类，找类名含 connect/gateway/socket/host 且方法返回 String 的
    try {
        Java.enumerateLoadedClasses({
            onMatch: function(n){
                if(!/(host|gateway|serveraddr|connaddr|socketconfig)/i.test(n)) return;
                if(!/meelive|appshatcher|inke/i.test(n)) return;
                try {
                    var C=Java.use(n);
                    C.class.getDeclaredFields().forEach(function(f){
                        try { var v=C[f.getName()].value; if(typeof v==='string'&&/^https?:|^\d+\.\d+\.\d+\.\d+|:\d+/.test(v)) log('HOSTFIELD', n+'.'+f.getName()+'='+v); } catch(e){}
                    });
                } catch(e){}
            },
            onComplete: function(){ log('HOOK','scan done'); }
        });
    } catch(e){}

    log('READY','gateway hooks installed');
});
