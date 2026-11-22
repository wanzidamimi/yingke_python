/*
 * 反反调试：阻止加固检测 frida 后主动退出。
 * hook kill / exit / System.exit / pthread_exit，记录并拦截来自可疑调用的退出。
 */
'use strict';
function log(t,s){ console.log('[AA]['+t+'] '+s); }
Java.perform(function(){
    log('START', new Date().toString());

    // libc kill / raise / exit
    try {
        var kill = Module.findExportByName(null, 'kill');
        if (kill) {
            Interceptor.attach(kill, {
                onEnter: function(args){
                    var pid = args[0].toInt32(); var sig = args[1].toInt32();
                    // 只拦截发给自己进程的 SIGKILL(9)/SIGABRT(6)
                    if ((sig === 9 || sig === 6) && pid > 0) {
                        log('KILL_BLOCKED', 'pid='+pid+' sig='+sig+' caller='+this.returnAddress);
                        this.block = true;
                    }
                },
                onLeave: function(ret){ if(this.block) ret.replace(0); }
            });
            log('HOOK', 'kill @ '+kill);
        }
    } catch(e){ log('WARN','kill '+e); }

    try {
        var exit = Module.findExportByName(null, 'exit');
        if (exit) {
            Interceptor.replace(exit, new NativeCallback(function(code){
                log('EXIT_BLOCKED', 'code='+code);
            }, 'void', ['int']));
            log('HOOK', 'exit @ '+exit);
        }
    } catch(e){ log('WARN','exit '+e); }

    // android.os.Process.killProcess / System.exit
    try {
        var Process = Java.use('android.os.Process');
        Process.killProcess.overload('int').implementation = function(pid){
            log('PROC_KILL_BLOCKED', 'pid='+pid);
            // 不真正杀
        };
        log('HOOK', 'Process.killProcess');
    } catch(e){ log('WARN','Process '+e); }

    try {
        var Sys = Java.use('java.lang.System');
        Sys.exit.overload('int').implementation = function(code){
            log('SYS_EXIT_BLOCKED', 'code='+code);
        };
        log('HOOK', 'System.exit');
    } catch(e){ log('WARN','System '+e); }

    log('READY', 'anti-anti installed');
});
