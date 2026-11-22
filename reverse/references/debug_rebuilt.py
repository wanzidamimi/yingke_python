import sys
from reassemble_tcp_frames import reassemble, parse_frames

path = sys.argv[1]
for key, stream in reassemble(path):
    if 1300 not in (key[1], key[3]):
        continue
    frames, used = parse_frames(stream)
    print('STREAM', key, 'len', len(stream), 'frames', len(frames), 'used', used)
    print(' hex', stream[:64].hex())
    if frames:
        print(' first frame len', len(frames[0]), 'cmd', frames[0][4:6].hex(), 'bodylen', int.from_bytes(frames[0][18:22], 'big'))
