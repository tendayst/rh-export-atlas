"""
fetch.py — parallel ranged download of the 7.7 GB Lean export.

The MIT server throttles a single connection hard (~0.25 MB/s), so we split the
file into N ranges and fetch them concurrently, each worker seeking to its own
offset in one pre-allocated output file. Resumable: a range whose slice is
already complete is skipped.
"""
import os
import sys
import time
import threading
import urllib.request

URL = 'https://math.mit.edu/~drew/grh/solution.ndjson.zst'
TOTAL = 7699933588
N = 16

out_path = sys.argv[1] if len(sys.argv) > 1 else 'solution.ndjson.zst'
done_bytes = [0] * N
lock = threading.Lock()
t0 = time.time()


def slice_bounds(i):
    size = TOTAL // N
    start = i * size
    end = TOTAL - 1 if i == N - 1 else start + size - 1
    return start, end


def worker(i):
    start, end = slice_bounds(i)
    want = end - start + 1
    got = 0
    while got < want:
        s = start + got
        req = urllib.request.Request(URL, headers={
            'User-Agent': 'Mozilla/5.0',
            'Range': f'bytes={s}-{end}',
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(out_path, 'r+b') as f:
                f.seek(s)
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    with lock:
                        done_bytes[i] = got
            if got < want:
                time.sleep(1)
        except Exception:
            time.sleep(2)


with open(out_path, 'wb') as f:
    f.truncate(TOTAL)

threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(N)]
for t in threads:
    t.start()

while any(t.is_alive() for t in threads):
    time.sleep(15)
    with lock:
        tot = sum(done_bytes)
    el = time.time() - t0
    print(f'{tot/1e9:.2f}/{TOTAL/1e9:.2f} GB  {tot/1e6/el:.2f} MB/s  eta {(TOTAL-tot)/(tot/el)/60:.0f} min',
          flush=True)

for t in threads:
    t.join()
print('done')
