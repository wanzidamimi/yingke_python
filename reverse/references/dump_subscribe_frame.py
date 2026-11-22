import sys

from reassemble_tcp_frames import parse_frames, reassemble

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]) or key[1] == 1300:
        continue
    frames, _ = parse_frames(stream)
    for frame in frames:
        if frame[4:6] != bytes.fromhex('4c04'):
            continue
        n = int.from_bytes(frame[18:22], 'big')
        body = frame[22:22+n]
        ext = frame[22+n:]
        print('FRAME', frame.hex())
        print('HEADER', frame[:22].hex())
        print('BODY', n, body.hex(), body.decode('utf-8', 'replace'))
        print('EXT', len(ext), ext.hex(), ext.decode('utf-8', 'replace'))
