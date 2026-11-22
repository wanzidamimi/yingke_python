Process.enumerateModules().forEach(function (m) {
  if (m.name.indexOf('libc') >= 0 || m.path.indexOf('arm64') >= 0) {
    console.log('MOD ' + m.name + ' ' + m.path + ' base=' + m.base);
  }
});
