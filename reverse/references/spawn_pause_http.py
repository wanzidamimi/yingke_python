#!/usr/bin/env python3
"""用 Frida Python API 暂停 spawn，等 hook 装好后再恢复 App。"""
import sys
import time

import frida

DEVICE = '127.0.0.1:5555'
PKG = 'com.meelive.ingkee'
SCRIPT = r'd:/Scrapy-project/yingke_python/reverse/hooks/hook_http_min.js'
READY_MARK = 'ol/b.a ok'
WAIT_READY = 20
AFTER_RESUME = 50

received = []


def on_message(message, data):
    if message.get('type') == 'send':
        line = str(message.get('payload'))
        received.append(line)
        print(line, flush=True)
    elif message.get('type') == 'error':
        print('FRIDA_ERROR: %s' % message.get('description'), flush=True)


def main():
    manager = frida.get_device_manager()
    device = manager.get_device(DEVICE)
    print('spawning %s' % PKG, flush=True)
    pid = device.spawn([PKG])
    print('SPAWN_PID=%d' % pid, flush=True)
    session = device.attach(pid)
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        source = f.read()
    script = session.create_script(source)
    script.on('message', on_message)
    script.load()

    deadline = time.time() + WAIT_READY
    while time.time() < deadline and not any(READY_MARK in x for x in received):
        time.sleep(0.2)
    print('READY=%s' % any(READY_MARK in x for x in received), flush=True)

    device.resume(pid)
    print('RESUMED pid=%d' % pid, flush=True)
    time.sleep(3)
    try:
        script.exports_sync.install()
        print('INSTALL_CALLED', flush=True)
    except Exception as exc:
        print('INSTALL_ERR=%s' % exc, flush=True)
    time.sleep(AFTER_RESUME)
    try:
        script.unload()
    except Exception:
        pass
    try:
        session.detach()
    except Exception:
        pass
    print('DONE', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
