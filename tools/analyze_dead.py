"""
analyze_dead.py — who owns the dead code?

`reach.reach.bits` is the packed reachability bitmap from pass3 (1 bit per
expression id). A declaration is "live" iff its proof term is reachable from the
five headline theorems.

This answers the question the whole exercise hangs on: the archive is 97%
reachable, but *whose* 3% is dead — Mathlib's (expected, since the export carries
whatever was imported) or the submission's own (that would be real waste).
"""
import array
import sys
import json
import collections
import numpy as np

SUBMISSION_NS = {
    'GlobalTheory', 'Formalism', 'GroundTheory', 'PositivityTheory', 'UpperTheory',
    'ReciprocityTheory', 'PI', 'LateralTheory', 'CrystallineSemistableComparison',
    'FunctorialResolution', 'CompanionTheory',
}
# Reuse on another project: pass the top-level namespaces that belong to the
# submission as argv[1]:
#     python analyze_dead.py "MyTheory,MyLemmaLib"
if len(sys.argv) > 1:
    SUBMISSION_NS = set(x.strip() for x in sys.argv[1].split(',') if x.strip())

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'data')

# declarations table: (name_id, value_root) pairs
raw = array.array('q')
with open(f'{BASE}\\meta.decls', 'rb') as f:
    raw.frombytes(f.read())
decls = np.frombuffer(raw.tobytes(), dtype=np.int64).reshape(-1, 2)

bits = np.fromfile(f'{BASE}\\reach.reach.bits', dtype=np.uint8)
print(f'bitmap bytes: {bits.size:,} -> {bits.size*8:,} slots', flush=True)

names = []
with open(f'{BASE}\\meta.full', encoding='utf-8') as f:
    for ln in f:
        names.append(ln.rstrip('\n'))
print(f'names: {len(names):,}', flush=True)


def owner(full):
    if '.' not in full:
        return 'SUBMISSION' if full else '?'
    p = full.split('.', 1)[0]
    if p in SUBMISSION_NS:
        return 'SUBMISSION'
    if p == '_private':
        return '_private'
    return 'OTHER'          # Mathlib / Lean core


def ns_of(full):
    return full.split('.', 1)[0] if '.' in full else '(root)'


rows = []
vals = decls[:, 1]
ok = vals >= 0
bidx = np.where(ok, vals // 8, 0)
# np.packbits default bitorder='big': element i sits in bit (7 - i%8) of byte i//8
sidx = np.where(ok, 7 - (vals % 8), 0)
alive = ((bits[bidx] >> sidx) & 1).astype(bool)
live_mask = ok & alive

cnt = collections.Counter()
live_cnt = collections.Counter()
ns_stat = collections.defaultdict(lambda: [0, 0])   # ns -> [total, live]

for i in range(len(decls)):
    nm = int(decls[i, 0])
    full = names[nm] if nm < len(names) else '?'
    o = owner(full)
    cnt[o] += 1
    if live_mask[i]:
        live_cnt[o] += 1
    s = ns_stat[ns_of(full)]
    s[0] += 1
    if live_mask[i]:
        s[1] += 1

print()
print(f'{"owner":14s}{"decls":>10s}{"live":>10s}{"dead":>10s}{"live%":>9s}')
for o in ('SUBMISSION', 'OTHER', '_private'):
    t = cnt[o]; l = live_cnt[o]
    print(f'{o:14s}{t:>10,}{l:>10,}{t-l:>10,}{(l/t*100 if t else 0):>8.2f}%')
print(f'{"TOTAL":14s}{len(decls):>10,}{int(live_mask.sum()):>10,}'
      f'{len(decls)-int(live_mask.sum()):>10,}{live_mask.sum()/len(decls)*100:>8.2f}%')

print()
print('per-namespace (top 25 by size):')
print(f'{"ns":34s}{"decls":>9s}{"live":>9s}{"dead":>9s}{"live%":>8s}')
for ns, (t, l) in sorted(ns_stat.items(), key=lambda kv: -kv[1][0])[:25]:
    print(f'{ns:34s}{t:>9,}{l:>9,}{t-l:>9,}{(l/t*100 if t else 0):>7.2f}%')

out = {'by_owner': {o: [cnt[o], live_cnt[o]] for o in cnt},
       'total': len(decls), 'live': int(live_mask.sum())}
json.dump(out, open(f'{BASE}\\dead_ownership.json', 'w'), indent=2)
print('\nwrote dead_ownership.json')
