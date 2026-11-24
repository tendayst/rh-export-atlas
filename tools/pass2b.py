"""
pass2b.py — full-name resolution for the lean4export name table.

Two traps found the hard way:

1. `"pre":0` is a *sentinel* meaning "no parent", not a reference to name id 0.
   Treating it as a parent made every name start with '?'.

2. Numeric names are emitted as `{"in":N,"num":{"i":..,"pre":..}}` — field order
   varies by serializer, so the first regex (which demanded pre first) silently
   dropped every numeral, which dangled ~5M parent references.

Names are emitted in dependency order (parent id < child id), so the table can be
resolved incrementally instead of walking a chain per name.
"""
import re
import sys
import zstandard as zstd

SRC, OUT = sys.argv[1], sys.argv[2]

RE_STR = re.compile(rb'^\{"in":(\d+),"str":\{"pre":(\d+),"str":"((?:[^"\\]|\\.)*)"\}\}$')

parts = {}
pres = {}
max_id = 0


def unescape(b):
    return b.decode('utf-8', 'replace').replace('\\"', '"').replace('\\\\', '\\')


def num_after(line, keypos):
    """Integer value following the `:` of the key starting at keypos."""
    q = line.find(b':', keypos)
    if q < 0:
        return -1
    q += 1
    v = 0
    seen = False
    n = len(line)
    while q < n:
        c = line[q]
        if 48 <= c <= 57:
            v = v * 10 + c - 48
            seen = True
        elif seen:
            break
        q += 1
    return v if seen else -1


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
            if not ln.startswith(b'{"in":'):
                continue
            i = num_after(ln, 1)
            if i < 0:
                continue
            m = RE_STR.match(ln)
            if m:
                pres[i] = int(m.group(2))
                parts[i] = unescape(m.group(3))
                if i > max_id:
                    max_id = i
                continue
            if b'"num"' in ln:
                ii = ln.find(b'"i":')
                pp = ln.find(b'"pre":')
                if ii < 0 or pp < 0:
                    continue
                parts[i] = '#' + str(num_after(ln, ii))
                pres[i] = num_after(ln, pp)
                if i > max_id:
                    max_id = i
        buf = buf[idx:]

print(f'name entries: {len(parts)}, max id: {max_id}', flush=True)

full = {}


def resolve(i):
    stack = []
    j = i
    while j > 0 and j not in full:
        stack.append(j)
        p = pres.get(j, 0)
        if p <= 0 or p >= j:
            break
        j = p
    for k in reversed(stack):
        p = pres.get(k, 0)
        s = parts.get(k, '?')
        if p <= 0 or p >= k:
            full[k] = s
        else:
            full[k] = full.get(p, '?') + '.' + s
    return full.get(i, '?')


missing = 0
with open(OUT, 'w', encoding='utf-8') as f:
    for i in range(max_id + 1):
        s = resolve(i)
        if s == '?':
            missing += 1
        f.write(s + '\n')

print(f'wrote {OUT}, unresolved={missing}', flush=True)
