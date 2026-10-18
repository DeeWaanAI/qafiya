# Qāfiya — Formal Data-Model Specification

**Version:** 1.1 (draft for review) · **Product:** DeeWaanAI Qāfiya · **Tagline:** the Provenance-First Data Model
**Scope:** the data substrate only. Not a file system, not an integration fabric, not the OS.
**Normative language:** MUST / SHOULD / MAY as in RFC 2119.
**v1.1 change:** absorbs the two-layer verification method from the authors' mapping paper (*Skills for Self-Auditing AI-Assisted Work*) — the claim tuple, the defect taxonomy (eleven classes as of mapping paper v0.9: N1–N4, S1–S5, I1–I2; §3.2 covers the ten pre-N4 classes, N4 formula-approximation is the v1.2 extension), the R1–R6 discipline, the coverage metric, and the four provable limits.

## 0. Thesis and method lineage

> *"A claim is not a number or a sentence — it is a link between a sentence, a value, and an artifact, and the link itself is the unit of verification."*

Qāfiya is a data model in which every rendered value or claim is joined to its source by a **binding** — a first-class object that simultaneously (a) proves the value equals its data, (b) is the target of durable edits, and (c) carries a verifiable claim — so that "trust me" becomes "re-run it yourself."

**Lineage.** The two-layer verification *method* (data map + semantic map) is established by the mapping paper, proven on 21 papers. Qāfiya does not re-prove it; it **generalizes it from a periodic manuscript audit into a live data substrate.** The deltas that make Qāfiya a distinct contribution are: **write-back** (the binding is also the edit target), **rendering** (the binding is the source of a generated view), **continuity** (the check is a standing invariant, not a one-time sweep), **generality** (any personal/business data, not just papers), and the **efficiency** axis (tokens/cost). Cite the mapping paper as the method source.

## 1. Entities

| Entity | File | Role |
|---|---|---|
| **Dataset** | `datasets/<name>/` | A named, **frozen** collection of records (source of truth). |
| **Schema** | `…/schema.json` | Declares field names, types, the id-field, media-fields, and permitted derivations. |
| **Record** | `…/data.jsonl` | One JSON object per line; immutable identity by `id`. |
| **Block** | `documents/<name>/blocks.jsonl` | An ordered, typed unit of prose/structure (the document model). |
| **View** | `views/<name>.json` | A declarative, interactive spec; nodes reference bindings, never store values. |
| **Binding** | `…/bindings.jsonl` | **The core primitive** — joins a rendered element/claim to its evidence. |
| **Supersede log** | `…/SUPERSEDED.json` | Quarantine list of retired artifacts; a binding sourcing from one is invalid by construction. |
| **Media** | `media/<blob>` | Images/audio stored as-is; referenced by path, never inlined. |

### 1.1 Identifiers
Every entity has a stable, immutable `id` (ULID recommended). A record's identity is its `id`, **not** its content (§7 invariant 8). Namespaces: records `r_*`, blocks `blk_*`, views `v_*`, bindings `b_*`, datasets `ds:<name>`. **ID hygiene on first contact (R3):** profile every id/key column when a dataset is registered — dtype-inference risk, padding, leading-zero stripping — and record the canonical form; normalize defensively in every query (a stripped zero once produced a false "missing" alarm).

### 1.2 Schema (`schema.json`)
```jsonc
{
  "dataset": "expenses",
  "id_field": "id",
  "fields": {
    "id": "id", "date": "timestamp", "amount": "number",
    "category": "enum[travel,food,tools,other]", "receipt": "media"
  },
  "derivations": ["sum","avg","count","min","max","groupby","filter"]  // closed set, all deterministic
}
```
Types are the JSON primitives plus `id`, `media`, `enum[...]`, `list<T>`. The `derivations` set is **closed** so every `binding.derivation` is machine-recomputable (§3.1).

### 1.3 Block types
`type ∈ { heading, paragraph, list, table, quote, code, media, section }`. A `table` block references a dataset through a binding; a `media` block holds a blob path. Small by design; new types require a version bump.

## 2. The Binding primitive

One object, three jobs. Its provenance fields adopt the mapping paper's **claim tuple** — a value alone is not enough; a claim is *(value, statistic, device, authoritative artifact)*, because the same digits under a different statistic, machine, or run version is a *different claim*.

```jsonc
{
  "id": "b_7f3a",
  "kind": "claim",                       // view | claim | edit
  "target": { "view": "v_q3", "node": "cell:total" },
  "sources": [                            // evidence provenance (MUST be non-empty)
    { "dataset": "ds:expenses", "filter": "period=Q3", "field": "amount",
      "key_path": ["amount"], "verbatim_excerpt": "…raw line/value…" }   // R1/R3 anchoring
  ],
  "derivation": "sum(amount) where period='Q3'",   // deterministic recipe over sources
  "value": 4210.0,                        // cached; MUST equal eval(derivation, sources)
  "statistic": "sum",                     // tuple: the statistic, not just the number
  "device": "local-mlx|cloud-api",        // tuple: which run produced it
  "authoritative_artifact": "datasets/expenses/data.jsonl",   // tuple: which artifact is truth
  "superseded_by": [],                    // if this binding points at a retired artifact → invalid
  "assertion": {                          // present iff kind=claim
    "statement": "Q3 spend fell 12% vs Q2",
    "predicate": "direction",             // see §3.2 for the class set (ten here; N4 in v1.2)
    "expected": -0.12, "tolerance": 0.005,
    "both_sides": { "Q2": 4780.0, "Q3": 4210.0 }   // comparisons MUST record both values
  },
  "writeback": { "dataset": "ds:expenses", "record_id": "r_012", "field": "amount", "op": "set" },  // iff kind=edit
  "provenance": { "created_by": "llm:qafiyah-core", "created_at": "2026-10-07T10:12Z", "source_query": "show Q3 expenses" },
  "check": { "provenance": "PASS", "semantic": "FLAG", "checked_at": "…", "detail": "recompute shows -8%, not -12%" }
}
```

**Job 1 — render source:** the view node resolves its value by following `derivation` over `sources`; the view stores no number.
**Job 2 — edit target:** a manual change is an `edit` binding whose `writeback` names the exact record/field to update atomically.
**Job 3 — audit pointer:** a `claim` binding asserts something and is checked against its own evidence.

## 3. The two-layer check

### 3.1 Layer 1 — data map (deterministic; MUST; a *proof*)
Adapts the mapping paper's two-way verifier (`verify_two_way.py`). It checks, with zero trust in derivatives:
- **Value recompute:** `eval(derivation, sources)` over the *current* dataset must equal `value`; NaN is special-cased (silence about missing values is where phantom numbers hide).
- **Tuple consistency:** reject a claim whose stated `statistic` or `device` disagrees with its linked record — a value that matches only under a different statistic is a **false link**, not a pass.
- **Quarantine:** fail any binding whose `authoritative_artifact` appears in `SUPERSEDED.json` — this is the *stale-version* (N2) defense, enforced structurally.
- **Re-anchor:** on any draft/view change, confirm each bound verbatim quote/value still sits where mapped, so silent edits fail loudly.
- **Gaps are hard stops:** a value with no resolvable source may not be rendered at all — it is deleted or computed into a frozen record first.

Binary outcome: exit 0 or it does not. There is no percentage to negotiate with.

### 3.2 Layer 2 — semantic map (advisory; SHOULD; a *flag*)
Registers and checks sentences that *interpret*. The predicate set maps the mapping paper's observed defect classes to Qāfiya checks (the ten below; the eleventh — N4 formula-approximation, added in mapping paper v0.9 — is deferred to the v1.2 extension note):

| Class | Signature | Qāfiya check |
|---|---|---|
| N1 number-not-in-data | value can't be recomputed from sources | Layer 1 (proof) |
| N2 stale-version | correct value from a superseded run | quarantine + transitive invalidation |
| N3 hand-assembled cell | wrong denominator / pooled rate outside its subgroups | arithmetic cross-check |
| S1 reversed direction | prose points the way data don't | sign/order vs records |
| S2 wrong label/subject | right value, wrong thing (units, sex, stage) | attribution/label vs source field |
| S3 over-claim | "all/always/outperforms" where one row disagrees | scope enumeration |
| S4 phantom analysis | cites a test/table that was never run/deposited | existence gate (needs a bound artifact) |
| S5 exploratory-as-confirmed | a finding that failed its gate keeps confident voice | registry/gate status |
| I1 unverifiable | no bound source exists | **coverage metric** (§4) |
| I2 nothing to regenerate | inputs/configs absent | reproducibility check |

Mechanical where the sentence allows (signs, orderings, recomputed ratios, enumerated scope); **mechanism/causal claims never auto-pass** — the flagger records supporting evidence and hands judgment to a human (R6). Absence claims require the paranoid multi-form search (R1) before being reported, and retracted false flags stay in the log annotated (R5).

States: `PASS | FAIL | FLAG | PENDING | N/A`.

## 4. Coverage / checkability metric (new)

For every rendered artifact, report the **share of claims that are bound to a recomputable source** vs unbound (I1). Coverage is a first-class number, not a caveat: a view with 90% coverage is trustworthy in a way a 30% one is not, regardless of how clean the checked claims are. This is the substrate-level counterpart to the mapping paper's finding that "accessible ≠ verifiable ≠ reproducible."

## 5. Provable limits — the proof/flag boundary (new)

Qāfiya certifies **coherence between a claim and its artifacts, never truth about the world.** Four things it cannot do (inherited from the method's calibration, stated so "verified" is not misread as "true"): (1) it cannot catch an error the data itself *shares* with the claim — agreement then looks like verification; the remedy is an upstream second anchor, which is cost, not software; (2) it cannot see what rounding hides below printed precision; (3) it cannot judge claims whose evidence was never ingested — it marks them unverifiable (I1), lowering coverage; (4) it cannot detect a coordinated fabrication that is internally consistent. Layer 1 is a proof *within* these bounds; Layer 2 is only ever a flag.

## 6. Invalidation & durability (the guarantees)

- **Atomic write-back.** Applying an `edit` MUST write-temp-then-rename; MUST never overwrite in place.
- **Versioned source.** Prior states retained in `history.jsonl`; provenance survives edits and stays re-checkable.
- **Transitive invalidation.** When a record changes, every binding whose `sources` transitively include it → `provenance=PENDING` (dependent claims → `semantic=PENDING`), forcing recompute. This is what stops a *stale-but-passing* claim — the exact failure numeric matching alone misses.
- **Quarantine.** Retiring an artifact adds it to `SUPERSEDED.json`; any binding still pointing at it fails by construction (N2).

## 7. Well-formedness invariants (testable properties)

1. Every data-bearing view node references **exactly one** binding.
2. Every binding's `sources` is **non-empty** and each source resolves to an existing dataset/record/field (else it is I1, not a pass).
3. `value == eval(derivation, sources)` at check time; else Layer 1 FAILs.
4. **Tuple holds:** prose `statistic`/`device` match the linked record; a mismatch is a false link.
5. No binding sources from an artifact listed in `SUPERSEDED.json`.
6. A `claim` binding's `predicate` is evaluable against its derivation result; comparisons record **both sides**.
7. An `edit` binding's `writeback` target exists; applying it triggers §6 invalidation.
8. Ids are immutable; content edits never change an id.
9. A view is a **pure function** of (structure + bindings + current dataset); it mutates data only via an explicit `edit` binding.
10. A `media` block references a path; no binary inlined.
11. A legacy-derived block keeps a pointer to its original file; the original stays source of truth (non-destructive).
12. Existence-of-analysis claims (S4) require a bound artifact; absence is admissible only after the R1 multi-form search.
13. Coverage is reported alongside every check result; an unbound claim is never silently omitted.

Each is unit-testable and maps to a paper claim (§10).

## 8. Storage layout

```
datasets/<name>/  schema.json  data.jsonl  history.jsonl  bindings.jsonl  SUPERSEDED.json
documents/<name>/ blocks.jsonl  bindings.jsonl
views/<name>.json               # declarative spec; nodes carry binding refs
media/<blob>                    # images/audio as-is
```
`data.jsonl` is the frozen current state; `history.jsonl` the append-only version log. SQLite MAY be added as a query **index** — never the source of truth.

## 9. Worked example (three catches, one loop)

1. User: *"show Q3 expenses and the trend."* Model emits `v_q3` + `b_7f3a` (view binding, `sum…Q3`) + `b_9c11` (claim: "fell 12% vs Q2", both_sides recorded).
2. Renderer draws the interactive table; the claim shows "fell 12%" with ▸evidence → `b_9c11`.
3. User edits a cell → `edit` binding writes back to `r_012.amount` atomically; `history.jsonl` logs the prior value.
4. §6 invalidation marks `b_7f3a`/`b_9c11` PENDING. *(Note, verified in code: immediately after the edit the cached value IS stale, so a Layer-1 run at this point correctly FAILs — the loop must first re-render.)* The view re-resolves its values from current data (`refresh`); the claim's assertion text is never touched. Layer 1 now recomputes the total → **PASS** (value matches source).
5. Layer 2 recomputes the trend → actual −8% → `semantic = FLAG: "recompute shows -8%, not -12%"` (S1). Clickable to the rows.
6. Separately, a claim "we ran a seasonality test" with no bound artifact → **S4 phantom-analysis FAIL** until the test exists as a frozen record; and a figure re-rendered from a now-`SUPERSEDED` run → **N2 quarantine FAIL.**

## 10. Non-goals & open items

**Non-goals.** Not a file system (Cai 2024; Generative File Systems 2026). Not an ETL/integration fabric. Not a full W3C PROV store (record-level pointers only). Not a query engine (optional index). Not the OS (separate, later work). Not a re-run of the mapping paper's audit — Qāfiya *generalizes* that method into a writable, renderable substrate.

**Open items for the evaluation design (task #10).**
- Defect-injection corpus built across the **ten classes covered by v1.1** (N4 joins when the v1.2 extension lands); report per-class catch-rate (Layer 1 = proof, expected 100% on value drifts; Layer 2 = flag, report precision/recall — the number the mapping paper did *not* fix, generated here).
- Baselines: human review ("who can see it" column) / Statcheck-style recompute / external-corpus NLP verification (FActScore, AVeriTeC) / no check.
- **Coverage** as a reported metric, not just catch-rate.
- **Efficiency** crossover (tokens, backend-agnostic) per the efficiency plan.
- Success criteria tied to invariants §7.

---
*Method source: the authors' mapping paper (two-layer data+semantic claim verification, v0.4) and its `research-paper-rigor` v2.1.0 / `research-semantic-map` v1.1.1 skills. Companion to the systematic review, design brief, and efficiency plan.*
