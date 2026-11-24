# rh-export-atlas

Structural statistics on the Lean 4 export of the claimed 2026 Riemann Hypothesis
proof by Levent Alpöge (released 2026-11-20 at <https://alpo.ge/remark.pdf>),
computed directly from the kernel-level proof export rather than from source text.

**What this is:** measurements, not a verification. Nothing here re-checks the
proof; the Lean and Mathlib communities certified it separately (a joint statement
on 2026-11-21, with the full check log at
<https://math.mit.edu/~drew/grh/>). This repository asks a different question:

> *What shape does a 17-million-line machine-generated proof actually have?*

**License note.** The proof itself carries no license statement. This repository
therefore publishes only the method, the tools, and derived statistics — never the
Lean source. Every number below can be regenerated from the public mirror.

---

## Headline numbers

| Quantity | Value |
|---|---|
| Archive | 175,188 Lean files, 17,374,242 source lines |
| Compressed export | 7,699,933,588 bytes (7.7 GB) |
| Inflated ndjson | **61.57 GB / 1,080,769,508 lines** |
| Expression nodes | **1,065,214,329** |
| Name entries | 14,065,150 |
| Declarations | **1,484,726** |
| Declarations with a proof term | 1,460,442 |

| Reachability from the five headline theorems | Count | Share |
|---|---|---|
| Expression nodes reachable | 1,033,000,914 | **96.98%** |
| Declarations live | 1,439,433 | **96.95%** |
| Declarations dead | 45,293 | **3.05%** |

The two independent measurements (node-level and declaration-level) agree to
0.03 percentage points.

---

## 1. The archive is shallow and wide

| | Files | Lines | **Lines/file** |
|---|---|---|---|
| Submission | **175,188** | 17,374,242 | **99.2** |
| Mathlib v4.33.1 | 8,322 | ~2,100,000 | **252** |

21× as many files as Mathlib, at 40% of the depth. This is a generator
signature, not a human one: 99-line modules whose names mostly re-export the
module below them.

It also explains a number that circulated after release. `keithadler/rh-trim`
published a minification table:

```
files  175,188 -> 30,698   (-82.5%)
lines 17,374,242 -> 13,850,849  (-20.3%)
```

Cutting five sixths of the files while losing only one fifth of the lines looks
like a 4:1 waste ratio. It is not: **the removed files were thin export shells**,
not discarded mathematics. The declarations inside them remain reachable.

## 2. Almost nothing is dead

Reachability is computed as a genuine dependency closure, from the proof terms of
the five headline theorems, over two edge kinds:

* **expression → sub-expression** (`app.fn`, `app.arg`, `forallE.body`, …)
* **`const` node → the declaration it names** — the edge people forget

That second edge is why source-text call-graph tracing gets this wrong. A `const`
node carries only a name id; the proof lives in a separate `thm`/`def` line. Skip
that edge and the graph looks like two disconnected forests, which invites the
conclusion that most of the archive is unreferenced. It isn't.

| Owner | Declarations | Live | Dead | Live % |
|---|---|---|---|---|
| Submission (11 own namespaces + root) | 1,185,460 | 1,148,919 | 36,541 | **96.92%** |
| `_private` | 112,431 | 111,603 | 828 | **99.26%** |
| Mathlib / Lean core | 186,835 | 178,911 | 7,924 | 95.76% |
| **Total** | **1,484,726** | **1,439,433** | **45,293** | **96.95%** |

The submission wastes *less* than the Mathlib fragment it depends on (3.08% vs
4.24%). Dead declarations number **45,293**, not millions.

## 3. 79% of the archive is new

Mathlib contributes 186,835 declarations to this export; the submission
contributes 1,185,460 — i.e. **six times Mathlib's footprint** in six weeks.

| Namespace | Declarations | Share |
|---|---|---|
| `GlobalTheory` | 620,019 | 41.8% |
| `Formalism` | 235,902 | 15.9% |
| `_private` | 112,431 | 7.6% |
| `GroundTheory` | 76,714 | 5.2% |
| `PositivityTheory` | 65,407 | 4.4% |
| `UpperTheory` | 60,030 | 4.0% |
| `ReciprocityTheory` | 44,239 | 3.0% |
| `PI` | 31,214 | 2.1% |
| `CategoryTheory` *(Mathlib)* | 20,588 | 1.4% |
| `LateralTheory` | 13,705 | 0.9% |
| `CrystallineSemistableComparison` | 9,133 | 0.6% |
| `FunctorialResolution` | 6,489 | 0.4% |
| `CompanionTheory` | 6,175 | 0.4% |

The namespace names are themselves a table of contents: a positivity layer, a
reciprocity layer, three parallel "theory" layers, period integrals, and a
9,133-declaration `CrystallineSemistableComparison` — i.e. the comparison theorem
of p-adic Hodge theory, rebuilt rather than borrowed.

## 4. Granularity, not content

Reference-degree distribution over constant names (0.65% sample, first 50 MB):

| Times referenced | Share of names | Share of references |
|---|---|---|
| 1 | **69.4%** | 26.3% |
| 2 | 13.3% | 10.1% |
| 3–5 | 10.6% | 14.5% |
| 6–10 | 3.6% | 10.3% |
| 11–100 | 2.9% | 26.1% |
| 101+ | 0.1% | 12.8% |

And 47.4% of all *names* (not declarations) live under `inst.` — typeclass
instances. The archive is dominated by instance resolution machinery, not by
mathematical statements.

---

## What this does and does not say

**Does say.** The archive is 97% reachable and 79% original; the dead fraction is
3%, smaller than Mathlib's own. The proof is not padding wrapped around a short
argument. Its shape is: enormous granularity (175k files × 99 lines, 666k
instance names), near-total reachability, and six Mathlibs of new declarations.

**Does not say.** Nothing about correctness — that was settled (subject to peer
review) by the kernel checks. Nothing about whether the mathematics is good, or
whether the argument can be compressed. In particular:

> Reachability at 97% closes the "just delete the dead code" route to a readable
> proof. There is no waste to delete. Compressing 250,000 pages toward 500 pages
> requires **re-layering the abstraction**, not pruning.

The 485× gap between the archive and a human-readable paper is a granularity gap,
not a redundancy gap.

## Caveats

1. Reachability is a closure over proof terms and `const → declaration` edges. It
   does not model instance search, `simp` lemma selection, or reducibility hints.
   A declaration marked live is *referenced*; it is not necessarily *essential*.
2. Owner classification is by namespace prefix. The eleven submission namespaces
   and the root namespace are the submission's; everything else is attributed to
   Mathlib/Lean core. `_private` is reported separately because its ownership is
   inferred.
3. The reference-degree distribution comes from the first 50 MB of the export
   (0.65%), not the full file.
4. These are measurements taken by one person over two days with a hand-written
   streaming parser. Three parsing bugs were found and fixed during development —
   including one that produced a fully wrong "most of it is dead" answer. Treat
   the numbers as reproducible claims, not as published results.

## Reproduce

```bash
python tools/fetch.py data/solution.ndjson.zst        # 16-thread ranged download, ~6 min
python tools/decompress_index.py data/solution.ndjson.zst data/solution.ndjson data/solution.idx
python tools/scan1.py data/solution.ndjson.zst        # kind histograms, ref degrees
python tools/pass2a.py data/solution.ndjson.zst data/meta
python tools/pass2b.py data/solution.ndjson.zst data/meta.full
python tools/pass3.py data/solution.ndjson data/solution.idx data/meta data/reach.json
python tools/analyze_dead.py
```

Requirements: ~90 GB free disk (7.7 GB compressed + 61.5 GB inflated), ~4 GB RAM
for the reachability pass, Python 3.10+, `zstandard`, `numpy`.

Two engineering notes worth copying:

* A single HTTP connection to the MIT mirror is throttled to ~0.25 MB/s. Sixteen
  parallel range requests reach ~20 MB/s.
* `json.loads` manages ~60k lines/s on this data. A hand-written byte scanner
  doing the same work reaches ~970k lines/s. At 1.08 billion lines that is the
  difference between five hours and twenty minutes.

## Files

| Path | Contents |
|---|---|
| `tools/` | Streaming parser, reachability pass, analysis scripts |
| `results/summary.json` | All headline figures in machine-readable form |
| `results/namespaces.tsv` | Per-namespace declaration and live/dead counts |
| `results/dead_ownership.json` | Live/dead split by owner |
| `data/` | **not committed** — generated locally by the scripts above |

## Using this on another project

Nothing in `tools/` is specific to the Riemann Hypothesis except two literals, and
both are now optional arguments:

| What | Where | Default |
|---|---|---|
| Theorems to root the closure at | `pass2a.py` argv[3] | the five RH theorems |
| Namespaces belonging to the submission | `analyze_dead.py` argv[1] | the eleven RH namespaces |

On any other `lean4export` archive:

```bash
python tools/pass2a.py export.ndjson.zst meta "mainTheorem,keyLemma"
python tools/pass2b.py export.ndjson.zst meta.full
python tools/pass3.py export.ndjson export.idx meta reach.json
python tools/analyze_dead.py "MyTheory,MyLib"
```

`pass3.py` reads the roots out of `meta.json`, so it follows automatically.

What the pipeline gives you for any project:

* reachability from a chosen set of theorems (node-level and declaration-level)
* a live/dead split per namespace, and by submission vs dependency
* granularity statistics (module size, instance share, reference degrees)
* a proof-term depth histogram

The RH defaults reproduce the published numbers exactly, so the parametrization is
verified in both directions.

## License

Split deliberately:

* **Code** (`tools/`) — MIT, see [LICENSE](LICENSE).
* **Data and prose** (`results/`, `README.md`, `FINDINGS.md`) — CC0 1.0 public
  domain dedication, see [LICENSE-DATA](LICENSE-DATA). These are measurements of
  a public artifact; facts should not need permission to be reused.

Neither covers the proof's own Lean source, which is not in this repository and
carries no license statement of its own.

## Attribution

The proof is Levent Alpöge's, made with Claude, and was independently verified by
the Lean and Mathlib communities (Andrew Sutherland's check log is the reference).
The parallel verification and minification work by `keithadler/rh-trim` and the
`leanprover-community/riemann-hypothesis` comparator setup are what made a
structural reading of this archive possible at all.
