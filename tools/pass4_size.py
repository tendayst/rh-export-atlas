"""
pass4_size.py — proof-term size and depth per expression, then per declaration.

lean4export emits expressions in dependency order (children before parents, so
child id < parent id). That makes both quantities a single forward sweep:

    size[e]  = 1 + sum(size[child])
    depth[e] = 1 + max(depth[child])

No graph is materialised; two flat arrays (4.3 GB + 2.1 GB) hold everything, and
each block is read once in file order.

Output answers the question rh-trim raised but did not publish: which declarations
are the giants, and how concentrated is the checking cost.
"""
import sys
import os
import json
import numpy as np

NDJSON, IDX, META_BASE, OUT = sys.argv[1:5]

meta = json.load(open(META_BASE + '.json', encoding='utf-8'))
roots = [h['value'] for h in meta['headline'].values() if h['value'] >= 0]
N = max(roots) + 1

size = np.zeros(N, dtype=np.float32)   # log2 of the *unfolded tree* size: the DAG
#                                        shares aggressively, so a raw node count
#                                        overflows int64 for deep proofs. depth is
#                                        immune to sharing and is the real metric.
depth = np.zeros(N, dtype=np.uint16)

offsets = [int(x) for x in open(IDX).read().split()]
FILE_SIZE = os.path.getsize(NDJSON)
BLOCK_IDX = 4
blocks = []
b = 0
while b < len(offsets):
    a = offsets[b]
    z = offsets[b + BLOCK_IDX] if b + BLOCK_IDX < len(offsets) else FILE_SIZE
    blocks.append((a, z))
    b += BLOCK_IDX

print(f'{len(blocks)} blocks forward, N={N/1e6:.1f}M', flush=True)

ARITY = {b'app': 2, b'forallE': 2, b'lam': 2, b'letE': 3, b'proj': 1}
KEYS = {b'app': (b'"arg":', b'"fn":'),
        b'forallE': (b'"body":', b'"type":'),
        b'lam': (b'"body":', b'"type":'),
        b'letE': (b'"body":', b'"type":', b'"value":'),
        b'proj': (b'"struct":',)}


def num_after(line, pos, n):
    v = 0
    seen = False
    while pos < n:
        c = line[pos]
        if 48 <= c <= 57:
            v = v * 10 + c - 48
            seen = True
        elif seen:
            break
        pos += 1
    return v if seen else -1


total = 0
for bi, (a, z) in enumerate(blocks):
    with open(NDJSON, 'rb') as f:
        f.seek(a)
        chunk = f.read(z - a)
    idx = 0
    ln = len(chunk)
    while idx < ln:
        j = chunk.find(b'\n', idx)
        if j < 0:
            break
        line = chunk[idx:j]
        idx = j + 1
        p = line.find(b'"ie":')
        if p < 0:
            continue
        if p <= 2:
            q = line.find(b',"', p + 5)
            tok = line[q + 2:q + 10] if q >= 0 else b''
        else:
            tok = line[2:10]
        ie = num_after(line, p + 5, ln)
        if ie < 0 or ie >= N:
            continue
        total += 1
        keys = None
        for kk, vv in KEYS.items():
            if tok.startswith(kk):
                keys = vv
                break
        if keys is None:
            size[ie] = 1
            depth[ie] = 1
            continue
        s = 1.0
        d = 0
        for key in keys:
            pp = line.find(key)
            if pp < 0:
                continue
            ch = num_after(line, pp + len(key), ln)
            if 0 <= ch < ie:
                s += float(size[ch])
                dv = int(depth[ch])
                if dv > d:
                    d = dv
        size[ie] = s
        depth[ie] = min(d + 1, 65535)
    if (bi + 1) % 20 == 0:
        print(f'  block {bi+1}/{len(blocks)}', flush=True)

print(f'expr processed: {total:,}', flush=True)

np.save(OUT + '.size.npy', size)
np.save(OUT + '.depth.npy', depth)

# per-declaration view
import array
raw = array.array('q')
with open(META_BASE + '.decls', 'rb') as f:
    raw.frombytes(f.read())
decls = np.frombuffer(raw.tobytes(), dtype=np.int64).reshape(-1, 2)
vals = decls[:, 1]
ok = vals >= 0
sz = np.where(ok, size[np.where(ok, vals, 0)], 0.0)
order = np.argsort(-sz)
tot = float(sz[ok].sum())

print()
print('proof term by declaration (size = log2 of unfolded tree):')
print(f'  declarations with a proof: {int(ok.sum()):,}')
print(f'  depth: max {int(depth.max()):,}  median {int(np.median(depth[ok])):,}')
print(f'  sum of log2-sizes: {tot:,.1f}  max log2-size: {float(sz.max()):,.1f}')
c = np.cumsum(sz[order])
for frac in (0.25, 0.5, 0.75, 0.9):
    k = int(np.searchsorted(c, tot * frac)) + 1
    print(f'  top {k:>7,} declarations ({k/ok.sum()*100:5.2f}%) hold {frac*100:.0f}% of log2-size')
print()
print('  top 20 by unfolded size:')
for i in order[:20]:
    print(f'    value={int(vals[i]):>12,}  log2size={float(sz[i]):>7.1f}  depth={int(depth[vals[i]]) if vals[i]<N else 0:>5}')

json.dump({'expr_total': total,
           'depth_max': int(depth.max()),
           'depth_median': int(np.median(depth[ok])),
           'log2size_max': float(sz.max())},
          open(OUT + '.json', 'w'))
print('\nwrote', OUT + '.size.npy / .depth.npy / .json')
