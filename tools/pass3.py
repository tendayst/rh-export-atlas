"""
pass3.py — backward reachability over the inflated export.

Two things make this less trivial than a DFS:

1. Every expression is emitted after its children (child id < parent id), so
   "parent reachable => children reachable" only propagates from high ids to low.
   We therefore walk index blocks in reverse; inside a block the rule runs to a
   fixed point with numpy.

2. A `const` node is a *reference by name*, not an edge to the definition. The
   proof of `rhOfAll` lives in a separate declaration line. So reachability also
   has to follow const -> (name -> declaration value). This is the edge that makes
   the dependency graph a graph and not a forest.

Output: how much of the 10.8-billion-line archive the five headline theorems
actually reach, and which constants appear in that closure.
"""
import sys
import os
import json
import array
import numpy as np

NDJSON, IDX, META_BASE, OUT = sys.argv[1:5]

meta = json.load(open(META_BASE + '.json', encoding='utf-8'))
roots = [h['value'] for h in meta['headline'].values() if h['value'] >= 0]
if not roots:
    raise SystemExit('no headline roots found')

N = max(roots) + 1
reach = np.zeros(N, dtype=np.uint8)
for r in roots:
    reach[r] = 1

names = open(META_BASE + '.names', encoding='utf-8').read().split('\n')

# name id -> declaration value root (the const->def edge)
_raw = array.array('q')
with open(META_BASE + '.decls', 'rb') as f:
    _raw.frombytes(f.read())
pairs = np.frombuffer(_raw.tobytes(), dtype=np.int64).reshape(-1, 2)
decl_val = {int(nm): int(v) for nm, v in pairs if v >= 0}
print(f'decl table: {len(decl_val)} entries with a value', flush=True)

offsets = [int(x) for x in open(IDX).read().split()]
FILE_SIZE = os.path.getsize(NDJSON)

BLOCK_IDX = 4
blocks = []
b = len(offsets) - 1
while b >= 0:
    lo = max(0, b - BLOCK_IDX + 1)
    a = offsets[lo]
    z = offsets[b + 1] if b + 1 < len(offsets) else FILE_SIZE
    blocks.append((a, z))
    b -= BLOCK_IDX

print(f'{len(blocks)} blocks, reach array {N/1e6:.1f}M entries', flush=True)

ARITY = {b'app': 2, b'forallE': 2, b'lam': 2, b'letE': 3, b'proj': 1}
KEYS = {b'app': (b'"arg":', b'"fn":'),
        b'forallE': (b'"body":', b'"type":'),
        b'lam': (b'"body":', b'"type":'),
        b'letE': (b'"body":', b'"type":', b'"value":'),
        b'proj': (b'"struct":',)}


def head_of(line):
    """The kind token, e.g. b'app' / b'const', or None."""
    p = line.find(b'"ie":')
    if p < 0:
        return None, -1
    if p <= 2:
        q = line.find(b',"', p + 5)
        tok = line[q + 2:q + 10] if q >= 0 else b''
    else:
        tok = line[2:10]
    return tok, p


def uint_at(line, pos):
    v = 0
    seen = False
    n = len(line)
    while pos < n:
        c = line[pos]
        if 48 <= c <= 57:
            v = v * 10 + c - 48
            seen = True
        elif seen:
            break
        pos += 1
    return v if seen else -1


const_reached = set()
total_lines = 0
total_expr = 0

for bi, (a, z) in enumerate(blocks):
    with open(NDJSON, 'rb') as f:
        f.seek(a)
        chunk = f.read(z - a)

    ies, k1, k2, k3 = [], [], [], []
    block_consts = []
    idx = 0
    ln = len(chunk)
    while idx < ln:
        j = chunk.find(b'\n', idx)
        if j < 0:
            break
        line = chunk[idx:j]
        idx = j + 1
        tok, p = head_of(line)
        if tok is None:
            continue
        total_lines += 1
        ie = uint_at(line, p + 5)
        if ie < 0 or ie >= N:
            continue
        total_expr += 1
        if tok.startswith(b'const'):
            nm = uint_at(line, line.find(b'"name":') + 7)
            if nm >= 0:
                block_consts.append((ie, nm))
            ies.append(ie); k1.append(-1); k2.append(-1); k3.append(-1)
            continue
        keys = None
        for kk, vv in KEYS.items():
            if tok.startswith(kk):
                keys = vv
                break
        if keys is None:
            ies.append(ie); k1.append(-1); k2.append(-1); k3.append(-1)
            continue
        vals = []
        for key in keys:
            pp = line.find(key)
            vals.append(uint_at(line, pp + len(key)) if pp >= 0 else -1)
        while len(vals) < 3:
            vals.append(-1)
        ies.append(ie); k1.append(vals[0]); k2.append(vals[1]); k3.append(vals[2])

    if ies:
        ie_a = np.array(ies, dtype=np.int64)
        c1_a = np.array(k1, dtype=np.int64)
        c2_a = np.array(k2, dtype=np.int64)
        c3_a = np.array(k3, dtype=np.int64)
        bc_ie = np.array([ie for ie, _ in block_consts], dtype=np.int64) if block_consts else None
        bc_nm = np.array([nm for _, nm in block_consts], dtype=np.int64) if block_consts else None
        for outer in range(50):
            progressed = False
            # (a) expression edges, to a fixed point inside the block
            for _ in range(200):
                m = reach[ie_a] > 0
                if not m.any():
                    break
                new = []
                for arr in (c1_a, c2_a, c3_a):
                    ch = arr[m]
                    ch = ch[ch >= 0]
                    if ch.size:
                        new.append(ch)
                if not new:
                    break
                tgt = np.concatenate(new)
                zero = reach[tgt] == 0
                if not zero.any():
                    break
                reached_targets = tgt[zero]
                reach[reached_targets] = 1
                progressed = True
            # (b) const -> declaration value
            if bc_ie is not None:
                m = reach[bc_ie] > 0
                if m.any():
                    cand = bc_nm[m]
                    fresh = [int(nm) for nm in cand if int(nm) not in const_reached]
                    if fresh:
                        const_reached.update(fresh)
                        tgt = [decl_val[nm] for nm in fresh if nm in decl_val]
                        if tgt:
                            tgt_a = np.array(tgt, dtype=np.int64)
                            zero = reach[tgt_a] == 0
                            if zero.any():
                                reach[tgt_a[zero]] = 1
                                progressed = True
            if not progressed:
                break

    if (bi + 1) % 10 == 0:
        print(f'  block {bi+1}/{len(blocks)} reach={int(reach.sum())} consts={len(const_reached)}',
              flush=True)

total = int(reach.sum())
print(f'lines_with_expr={total_lines} expr_seen={total_expr} reachable={total}')
hit_names = sorted(names[nm] for nm in const_reached if nm < len(names))
print(f'const names reached: {len(hit_names)} (distinct {len(set(hit_names))})')

# persist the reachability bitmap: 1 byte -> 1 bit, so 1.07e9 nodes costs 133 MB.
# every later question (what is dead, how big is each declaration's proof) reads this.
np.packbits(reach).tofile(OUT.replace('.json', '') + '.reach.bits')

json.dump({'reachable_expr': total,
           'expr_seen': total_expr,
           'roots': roots,
           'consts_reached': len(const_reached),
           'reachable_const_names': hit_names},
          open(OUT, 'w', encoding='utf-8'))
