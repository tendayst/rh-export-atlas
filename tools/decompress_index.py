"""
decompress_index.py — inflate the export to disk and build a sparse line index.

Reachability over a lean4export stream has to run *backwards*: every expression
is emitted after its children (child id < parent id), so "parent reachable =>
children reachable" can only be propagated from high ids to low. A zstd stream is
not seekable, so we inflate once and record the byte offset of every INDEX_EVERY
lines; an index block then costs ~54 MB of RAM, not 61 GB.

Counting newlines per chunk is cheap; fine-grained offsets are only resolved in
the chunks that actually straddle an index boundary.
"""
import sys
import zstandard as zstd

INDEX_EVERY = 1_000_000
CHUNK = 1 << 24

src, dst, idx_path = sys.argv[1], sys.argv[2], sys.argv[3]

d = zstd.ZstdDecompressor(max_window_size=2 ** 31)
offsets = [0]
line_no = 0
written = 0

with open(dst, 'wb') as out, open(src, 'rb') as f:
    reader = d.stream_reader(f, read_across_frames=False)
    while True:
        c = reader.read(CHUNK)
        if not c:
            break
        nl = c.count(b'\n')
        nxt = (line_no // INDEX_EVERY + 1) * INDEX_EVERY
        if line_no + nl >= nxt:
            p = -1
            while True:
                p = c.find(b'\n', p + 1)
                if p < 0:
                    break
                line_no += 1
                if line_no % INDEX_EVERY == 0:
                    offsets.append(written + p + 1)
        else:
            line_no += nl
        out.write(c)
        written += len(c)

with open(idx_path, 'w') as f:
    f.write('\n'.join(str(o) for o in offsets))
print(f'decompressed {written/1e9:.2f} GB, lines={line_no}, index points={len(offsets)}')
