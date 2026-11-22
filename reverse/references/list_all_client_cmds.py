import sys
from collections import Counter

from reassemble_tcp_frames import parse_frames, reassemble

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
counts = Counter()
samples = {}
for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]) or key[1] == 1300:
        continue
    frames, _ = parse_frames(stream)
    for frame in frames:
        cmd = frame[4:6].hex()
        counts[cmd] += 1
        samples.setdefault(cmd, frame[:80])
print('CMDS', dict(counts))
for cmd, frame in samples.items():
    print(cmd, frame.hex())
