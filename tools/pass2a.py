"""
pass2a.py — forward pass: build the name table, the declaration table, and locate
the five headline theorems.

lean4export names are de Bruijn-ish: a name is either a plain string, a numeral,
or "pre" + string where pre is an earlier name id. So the table is built in
emission order and later entries resolve against earlier ones.

Only integers and short strings are kept; no expression bodies. Output is a small
JSON sidecar plus two binary blobs that the backward pass mmaps.
"""
import sys
import re
import json
import array
import zstandard as zstd

SRC = sys.argv[1]
OUT = sys.argv[2]

# Which theorems to root the later reachability pass at. Pass a comma-separated
# list of short names as argv[3] to use this tool on any other project:
#     python pass2a.py export.ndjson.zst meta "mainTheorem,keyLemma"
DEFAULT_HEADLINE = {
    'riemannHypothesis',
    'riemannZeta_eq_zero_re',
    'LFunction_ne_zero_of_half_lt_re',
    'LFunction_eq_zero_re',
    'LFunction_eq_zero_re_of_isPrimitive',
}
HEADLINE = (set(x.strip() for x in sys.argv[3].split(',') if x.strip())
            if len(sys.argv) > 3 else DEFAULT_HEADLINE)

name_str = {}          # name id -> str component
name_pre = {}          # name id -> parent name id (-1 = root)
decl_name = {}         # decl name id -> value root expr id
decl_kind = {}
decl_table = []        # (name_id, kind, value_root)

RE_STR = re.compile(rb'^\{"in":(\d+),"str":\{"pre":(\d+),"str":"((?:[^"\\]|\\.)*)"\}\}$')
RE_NUM = re.compile(rb'^\{"in":(\d+),"num":\{"pre":(\d+),"i":(\d+)\}\}$')
RE_LPARAM = re.compile(rb'^\{"il":(\d+),"param":(\d+)\}$')
RE_THM = re.compile(rb'^\{"(thm|def|opaque)":\{.*?"name":(\d+),.*?(?:"type":(\d+),)?"value":(\d+)\}')
RE_IND = re.compile(rb'^\{"inductive":\{')


def main():
    max_name = 0
    max_decl = 0
    d = zstd.ZstdDecompressor(max_window_size=2 ** 31)
    with open(SRC, 'rb') as f:
        reader = d.stream_reader(f, read_across_frames=False)
        buf = b''
        while True:
            c = reader.read(1 << 22)
            if not c:
                break
            buf += c
            idx = 0
            while True:
                j = buf.find(b'\n', idx)
                if j < 0:
                    break
                ln = buf[idx:j]
                idx = j + 1
                if not ln:
                    continue
                if ln.startswith(b'{"in":'):
                    m = RE_STR.match(ln)
                    if m:
                        i = int(m.group(1)); pre = int(m.group(2))
                        name_str[i] = m.group(3).decode('utf-8', 'replace')
                        name_pre[i] = pre if pre != i else -1
                        if i > max_name:
                            max_name = i
                        continue
                    m = RE_NUM.match(ln)
                    if m:
                        i = int(m.group(1)); pre = int(m.group(2))
                        name_str[i] = '#' + m.group(3).decode()
                        name_pre[i] = pre if pre != i else -1
                        if i > max_name:
                            max_name = i
                        continue
                elif ln.startswith(b'{"thm"'):
                    nm = _uint(ln, b'"name":')
                    val = _uint(ln, b'"value":')
                    if nm >= 0 and val >= 0:
                        decl_table.append((nm, 'thm', val))
                        if nm > max_decl:
                            max_decl = nm
                    continue
                elif ln.startswith(b'{"def"'):
                    nm = _uint(ln, b'"name":')
                    val = _uint(ln, b'"value":')
                    if nm >= 0 and val >= 0:
                        decl_table.append((nm, 'def', val))
                        if nm > max_decl:
                            max_decl = nm
                    continue
                elif ln.startswith(b'{"opaque"'):
                    nm = _uint(ln, b'"name":')
                    val = _uint(ln, b'"value":')
                    if nm >= 0:
                        decl_table.append((nm, 'opaque', val if val >= 0 else -1))
                        if nm > max_decl:
                            max_decl = nm
                    continue
                elif ln.startswith(b'{"inductive"'):
                    # inductive blocks carry several names; record the type names
                    for m in re.finditer(rb'"name":(\d+)', ln):
                        decl_table.append((int(m.group(1)), 'inductive', -1))
                    continue
            buf = buf[idx:]

    # resolve full names
    def resolve(i, depth=0):
        parts = []
        while i >= 0 and depth < 64:
            parts.append(name_str.get(i, '?'))
            i = name_pre.get(i, -1)
            depth += 1
        return '.'.join(reversed(parts))

    headline_ids = {}
    for nm, kind, val in decl_table:
        full = resolve(nm)
        short = full.split('.')[-1]
        if short in HEADLINE and short not in headline_ids:
            headline_ids[short] = {'name_id': nm, 'full': full, 'kind': kind, 'value': val}

    meta = {
        'n_names': max_name + 1,
        'n_decls': len(decl_table),
        'headline': headline_ids,
    }
    with open(OUT + '.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # binary blobs for the backward pass: name strings (newline separated, id order)
    with open(OUT + '.names', 'w', encoding='utf-8') as f:
        for i in range(max_name + 1):
            f.write(resolve(i) + '\n')
    a = array.array('q')
    for nm, kind, val in decl_table:
        a.append(nm); a.append(val)
    with open(OUT + '.decls', 'wb') as f:
        a.tofile(f)

    print(json.dumps(meta, indent=2, ensure_ascii=False))


def _uint(line, key):
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


if __name__ == '__main__':
    main()
