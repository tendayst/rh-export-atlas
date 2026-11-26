# Postmortem: a confident answer to the wrong premise

On 2026-11-24 I published [rh-export-atlas](README.md) — a structural analysis of
the 61.57 GB Lean export of the 2026 Riemann Hypothesis proof. Its central claim:

> 97% of declarations are reachable, so there is no dead code to remove, therefore
> the proof cannot be compressed toward a readable form by pruning. 485× is
> impossible; the historical ceiling for this kind of compression is 3–20×.

Two days later, both halves were wrong.

This page is about *how* the error was made, not what the numbers should have
been. The numbers are in [FINDINGS.md](FINDINGS.md); the correction is at the top
of [README.md](README.md).

---

## Timeline

| when | what |
|---|---|
| 11-20 | Alpöge releases the proof as 17,374,242 lines of Lean |
| 11-23 | Alpöge states the "250,000+ pages" readable version was a **deliberate joke** |
| 11-24 | I parse 1,080,769,508 lines, build the reachability closure, measure 3.05% dead |
| 11-24 | I conclude: no compression space; 485× impossible |
| **11-25** | **Sernau + colleagues + Claude release a 76,000-line rewrite — 224× — by *re-proving*, not pruning** |

I answered a question that was overtaken in under 48 hours.

---

## Error 1: reachability is not necessity

These are different questions:

| question | my measurement answers it? |
|---|---|
| Was this lemma *used*? | **yes** — that is what a reachability closure does |
| Could this theorem have been reached *a shorter way*? | **no** — nothing in the method can see that |

A lemma can be referenced a hundred times and still be replaceable by a single
simpler one. Sernau's note says exactly that: *"Also removed a lot of complexity
(… uses a simpler integrality argument…)"*. He did not delete — he re-proved.

**The measurement stands. The inference does not.** "There is no dead code"
is true and useful; "therefore there is nothing to compress" does not follow, and
I wrote it as though it did.

## Error 2: the premise was never checked

The 250,000-page figure entered this work as a secondary quote — *"he says it's
over 250,000 pages"* — repeated by several outlets. I accepted it and then built
on top of it:

```
250,000 pages
  → 485× compression needed to reach 500 pages
  → historical ceiling is 3–20×
  → therefore not achievable by pruning
  → therefore only re-layering can work
```

Every step after the first is sound. **The first step was fiction.**

Here is the asymmetry that matters:

> I verified 61.57 GB byte by byte, replayed 1,065,214,329 expression nodes, found
> and fixed three parsing bugs — one of which had produced a fully wrong answer.
> **I never once verified the number I was reasoning from.**

Data got an audit. The premise got a citation.

---

## Why it read as professional

Not because the writing was good. Because of three structural features that make
wrong analysis look like right analysis:

1. **The numbers were reproducible.** Anyone can re-run the scripts and get 96.95%.
   Reproducibility is evidence of *execution*, never of *relevance*.
2. **The caveats were honest.** I listed what the closure does not model. That
   reads as rigor, and it is — about the model, not about the question.
3. **The conclusion was conservative.** "It can't be done" sounds like the
   cautious conclusion. It is actually the bold one; "it can be done, differently"
   is the harder claim to make, and it was the true one.

**A wrong answer wrapped in reproducibility, caveats and caution is harder to
dislodge than a wrong answer that looks sloppy.**

---

## Three rules I now apply

**1. Tag every input with its provenance before using it.**
First-hand / second-hand / repeated-by-media. A number that is convenient to
quote — big, round, dramatic — deserves *more* checking, not less. Drama is the
signature of a number that has been laundered.

**2. Separate "what I measured" from "what I concluded", and check whether they
are the same kind of claim.**
Reachability is a *negative* tool: it can refute "nobody uses this". It cannot
establish "nobody *could* do without this". I used a refutation as a proof of
impossibility, which is a category error, not a calculation error.

**3. Treat any "impossible" claim as having a shelf life of days.**
In a field where a 224× reduction can land 48 hours after your analysis, "this
cannot be done" is a claim about *the current state of the art*, not about
mathematics. Say "I don't see how", not "it cannot".

---

## What I would keep

The measurements: format, granularity (175,188 files at 99.2 lines/file vs
Mathlib's 252), the reachability closure, the 3.05% dead fraction sitting *below*
the Mathlib fragment's own 4.24%, the depth distribution with its 14,641-deep
`copy`/`transfer` glue.

None of that was overturned. What was overturned was the story I told on top of
it — and the story is the part that travels.

---

*Correction date: 2026-11-26. If a later development invalidates something here
too, it gets the same treatment: stated at the top, not deleted.*
