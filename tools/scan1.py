"""
scan1.py — pass 1 over lean4export ndjson for the Alpoge RH/GRH proof.

Reads a .zst stream, never materialises the whole file. Counts, per line:
  * expression kind histogram
  * const-node reference counts by name id  (this is the raw degree signal)
  * declaration counts by kind (thm / def / inductive / axiom / quot)
  * max ids seen, so a later pass can pre-size arrays

No JSON parsing: the export is machine-generated and we only need a handful of
integer fields, so byte-level scanning is ~15x faster than json.loads.
"""
import zstandard as zstd
import re
import sys
import json
import time
from collections import Counter

_KINDS = (rb'app|forallE|lam|const|proj|letE|sort|bvar|num|natVal|strVal'
          rb'|quot|mdata|mvar|fvar|synthetic')
# the export emits both {"lam":{...},"ie":N} and {"ie":N,"lam":{...}}
KIND_RE = re.compile(rb'^\{"(' + _KINDS + rb')"|^\{"ie":\d+,"(' + _KINDS + rb')"')
DECL_RE = re.compile(rb'^\{"(thm|def|inductive|axiom|opaque|quot)"')


def stream_lines(path, chunk=1 << 22):
    d = zstd.ZstdDecompressor(max_window_size=2 ** 31)
    with open(path, 'rb') as f:
        reader = d.stream_reader(f, read_across_frames=False)
        buf = b''
        while True:
            c = reader.read(chunk)
            if not c:
                break
            buf += c
            idx = 0
            while True:
                j = buf.find(b'\n', idx)
                if j < 0:
                    break
                yield buf[idx:j]
                idx = j + 1
            buf = buf[idx:]
        if buf:
            yield buf


def first_uint_after(line, key):
    """Value of the first `key` integer field, or -1."""
    p = line.find(key)
    if p < 0:
        return -1
    p += len(key)
    n = 0
    seen = False
    while p < len(line):
        c = line[p]
        if 48 <= c <= 57:
            n = n * 10 + (c - 48)
            seen = True
        elif seen:
            break
        p += 1
    return n if seen else -1


def main(path, limit=None):
    t0 = time.time()
    kinds = Counter()
    const_refs = Counter()
    decls = Counter()
    max_ie = -1
    max_in = -1
    n_lines = 0
    n_expr = 0
    n_const_nodes = 0
    n_bvar = 0

    for line in stream_lines(path):
        if not line:
            continue
        n_lines += 1
        if limit and n_lines > limit:
            break

        m = KIND_RE.match(line)
        if m:
            k = (m.group(1) or m.group(2)).decode()
            kinds[k] += 1
            n_expr += 1
            ie = first_uint_after(line, b'"ie":')
            if ie > max_ie:
                max_ie = ie
            if k == 'const':
                n_const_nodes += 1
                nm = first_uint_after(line, b'"name":')
                if nm >= 0:
                    const_refs[nm] += 1
                    if nm > max_in:
                        max_in = nm
            elif k == 'bvar':
                n_bvar += 1
            continue

        m = DECL_RE.match(line)
        if m:
            d = m.group(1).decode()
            decls[d] += 1
            nm = first_uint_after(line, b'"name":')
            if nm > max_in:
                max_in = nm
            continue

        if line.startswith(b'{"in":'):
            nm = first_uint_after(line, b'"in":')
            if nm > max_in:
                max_in = nm
            kinds['__name_def'] += 1
        elif line.startswith(b'{"il":'):
            kinds['__level_param'] += 1
        elif line.startswith(b'{"meta"'):
            kinds['__meta'] += 1
        else:
            kinds['__other'] += 1

    elapsed = time.time() - t0
    ref_counts = sorted(const_refs.values(), reverse=True)
    out = {
        'file': path,
        'lines': n_lines,
        'expr_nodes': n_expr,
        'const_nodes': n_const_nodes,
        'distinct_const_names': len(const_refs),
        'max_expr_id': max_ie,
        'max_name_id': max_in,
        'kinds': dict(kinds.most_common()),
        'decls': dict(decls.most_common()),
        'top20_const': ref_counts[:20],
        'median_const_refs': ref_counts[len(ref_counts) // 2] if ref_counts else 0,
        'elapsed_s': round(elapsed, 1),
        'lines_per_s': round(n_lines / elapsed) if elapsed else 0,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    # dump full const table separately, it can be large
    with open(path + '.constrefs.tsv', 'w', encoding='utf-8') as f:
        for nm, c in const_refs.most_common():
            f.write(f'{nm}\t{c}\n')


if __name__ == '__main__':
    p = sys.argv[1]
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    main(p, lim)
