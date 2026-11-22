console.log('ModuleType=' + typeof Module);
try { console.log('ModuleKeys=' + Object.keys(Module).join(',')); } catch (e) { console.log('ModuleKeysErr=' + e); }
try { console.log('find=' + typeof Module.findExportByName); } catch (e) { console.log('findErr=' + e); }
try { console.log('get=' + typeof Module.getExportByName); } catch (e) { console.log('getErr=' + e); }
try { console.log('Process=' + typeof Process); } catch (e) { console.log('ProcessErr=' + e); }
