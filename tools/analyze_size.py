"""
analyze_size.py — read the arrays pass4 produced and summarise them.

pass4 finished its sweep but its own summary step indexed one past the end
(a declaration's value root is one larger than the largest theorem root, so the
array sized from the roots is one short). The data was already on disk, so this
re-reads it with the bounds clamped, and never touches the 61 GB ndjson again.
"""
import array
import json
import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'results')

size = np.load(f'{BASE}\\sizes.size.npy', mmap_mode='r')    # float32, log2 unfolded tree
depth = np.load(f'{BASE}\\sizes.depth.npy', mmap_mode='r')   # uint16
N = size.shape[0]
print(f'arrays: N={N:,}')

raw = array.array('q')
with open(f'{BASE}\\meta.decls', 'rb') as f:
    raw.frombytes(f.read())
decls = np.frombuffer(raw.tobytes(), dtype=np.int64).reshape(-1, 2)
names = [l.rstrip('\n') for l in open(f'{BASE}\\meta.full', encoding='utf-8')]

vals = decls[:, 1]
ok = (vals >= 0) & (vals < N)
print(f'declarations: {len(decls):,}  with valid value: {int(ok.sum()):,}')

vi = vals[ok]
d = depth[vi].astype(np.int32)
s = size[vi].astype(np.float32)

print()
print('=== depth (proof-term nesting, immune to DAG sharing) ===')
print(f'  max    {int(d.max()):,}')
print(f'  p99.9  {int(np.percentile(d, 99.9)):,}')
print(f'  p99    {int(np.percentile(d, 99)):,}')
print(f'  median {int(np.median(d)):,}')
print(f'  mean   {float(d.mean()):.1f}')
print()
print('=== log2 of unfolded tree size (shared structure expanded) ===')
print(f'  max    {float(s.max()):.1f}   (= ~2^{float(s.max()):.0f} nodes)')
print(f'  p99    {float(np.percentile(s, 99)):.1f}')
print(f'  median {float(np.median(s)):.1f}')

tot = float(s.sum())
order = np.argsort(-s)
c = np.cumsum(s[order])
print()
print('=== concentration ===')
for frac in (0.25, 0.5, 0.75, 0.9):
    k = int(np.searchsorted(c, tot * frac)) + 1
    print(f'  top {k:>7,} declarations ({k/len(s)*100:5.2f}%) hold {frac*100:.0f}% of total')

okidx = np.where(ok)[0]
print()
print('=== the 20 largest proof terms ===')
for i in order[:20]:
    j = okidx[i]
    nm = int(decls[j, 0])
    full = names[nm] if nm < len(names) else '?'
    print(f'  depth={int(d[i]):>5}  log2size={float(s[i]):>6.1f}  {full[:88]}')

print()
print('=== the 12 deepest proof terms ===')
od = np.argsort(-d)
for i in od[:12]:
    j = okidx[i]
    nm = int(decls[j, 0])
    full = names[nm] if nm < len(names) else '?'
    print(f'  depth={int(d[i]):>5}  log2size={float(s[i]):>6.1f}  {full[:88]}')

summary = {
    'depth_max': int(d.max()),
    'depth_p999': int(np.percentile(d, 99.9)),
    'depth_p99': int(np.percentile(d, 99)),
    'depth_median': int(np.median(d)),
    'depth_mean': round(float(d.mean()), 2),
    'log2size_max': round(float(s.max()), 2),
    'log2size_p99': round(float(np.percentile(s, 99)), 2),
    'log2size_median': round(float(np.median(s)), 2),
    'concentration': {},
}
for frac in (0.25, 0.5, 0.75, 0.9):
    k = int(np.searchsorted(c, tot * frac)) + 1
    summary['concentration'][f'{int(frac*100)}pct'] = k

json.dump(summary, open(f'{OUT}\\size_depth.json', 'w'), indent=2)
print('\nwrote results/size_depth.json')
