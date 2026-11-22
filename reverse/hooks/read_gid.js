'use strict';
function log(t,m){console.log('[GID]['+t+'] '+m);}
setTimeout(function(){
  Java.perform(function(){
    try {
      var U = Java.use('ul/e');
      log('UL_E_FIELDS', U.class.getDeclaredFields().toString());
      log('STATIC_B', String(U.b));

      var B = Java.use('bl/b');
      log('BL_CLASS', B.class.getName());

      Java.choose('yj/f', {
        onMatch: function(inst) {
          try {
            var o = inst.O();
            var a = o.a.value !== undefined ? o.a.value : o.a;
            log('OBJ_UINT64', String(a));
            log('OBJ_J', String(inst.J()));
          } catch (e) { log('OBJ_ERR', String(e)); }
        },
        onComplete: function(){ log('DONE', 'choose'); }
      });
    } catch (e) { log('ERR', String(e)); }
  });
}, 500);
