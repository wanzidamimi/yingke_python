import os
import re
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SMALI_ROOT = r'd:/Scrapy-project/yingke_python/reverse/smali_out'
BODY_PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_bodies/1795147907026_be3935597831_200.bin'


def candidates():
    out = set()
    pat = re.compile(r'\b[0-9a-fA-F]{64}\b')
    for dp, _, fs in os.walk(SMALI_ROOT):
        for f in fs:
            if not f.endswith('.smali'):
                continue
            try:
                text = open(os.path.join(dp, f), encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for m in pat.findall(text):
                out.add(m.lower())
    return sorted(out)


def try_key(key, body, header):
    aad_options = [None, header]
    for aad in aad_options:
        try:
            plain = AESGCM(key).decrypt(body[:12], body[12:], aad)
            return plain, aad
        except Exception:
            pass
    return None, None


def main():
    raw = open(BODY_PATH, 'rb').read()
    header, body = raw[:8], raw[8:]
    keys = candidates()
    print('candidate_keys=%d' % len(keys))
    for text in keys:
        for keyname, key in (
            ('hex', bytes.fromhex(text)),
            ('ascii32', text.encode()[:32]),
        ):
            if len(key) != 32:
                continue
            plain, aad = try_key(key, body, header)
            if plain:
                print('FOUND key_type=%s key=%s aad=%s' % (keyname, text, aad))
                print(plain[:2000].decode('utf-8', 'replace'))
                return
    print('not found')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
