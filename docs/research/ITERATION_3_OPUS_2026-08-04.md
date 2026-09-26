# Iteration 3 (Opus) — From findings to executable contracts

- Date: 2026-08-04
- Branch: `work/repository-research-iterations`
- Predecessors: `docs/research/REPOSITORY_RESEARCH_4_ITERATIONS_2026-08-04.md` (iteration 1, GPT), `docs/research/ITERATION_2_OPUS_2026-08-04.md` (iteration 2, Opus)
- Successor: iteration 4 (GPT), audit and synthesis

## 0. Mandate and self-imposed constraint

Iterations 1 and 2 produced prose. Iteration 1 ranked repositories; iteration 2 read source code and
refuted part of that ranking. Neither produced anything a machine can reject.

This iteration is constrained to produce artifacts that **fail loudly**. The deliverable is a schema
plus a set of gate contracts plus a falsification harness. Anything that cannot be expressed as a
rejection rule was deliberately left out.

What this iteration does **not** do, and what must not be claimed on its basis:

- It does not open EXPLORE. Source integrity is still `BLOCKED_SOURCE_INTEGRITY` and the universe is
  193 eligible sessions against a floor of 200.
- It does not implement an adaptive loop. There is no feedback from evaluation to proposal anywhere in
  this design, by construction.
- It does not touch outcomes.
- It does not claim any gate works. Section 6 defines how each gate must earn the right to exist, and
  none has yet been run.

## 1. The one-paragraph design

A proposer emits `IndicatorSpec` documents in a small declarative language that is not Python and has
no opcode capable of reading the future, normalizing over the whole sample, smoothing bidirectionally,
or reading a clock. A compiler canonicalizes each spec, assigns a content hash, charges a
multiple-testing budget against the spec's **family**, and refuses anything that does not validate. An
evaluator runs the compiled spec and returns one of four verdicts per gate. Every run writes an
append-only, content-addressed manifest. The proposer never sees a verdict, a return, or a ranking.

The schema is committed as `specs/indicatorspec_v0.schema.json` in the same commit as this document.

## 2. Why the language is not Python, restated as a decision

Iteration 2 established that a gate which reports "no bias detected" for structural reasons is worse
than no gate. The same logic applies to sandboxing. Public practice for running untrusted generated
Python converges on two options: `RestrictedPython`, whose own documentation states plainly that it
"is not a sandbox system or a secured environment", or full OS-level containment. Both enumerate evil
inside a language that was never designed to be constrained.

EdgeLab does not need a general-purpose language. It needs arithmetic over causal windows. So the
decision is:

> **Capability is denied by absence of opcode, not by prohibition of syntax.**

Consequences that follow directly from the schema, and which therefore require no gate at all:

| Attack | Why no gate is needed |
|---|---|
| A1 direct future access | `lag` has `minimum: 0`. A negative lag is unrepresentable. |
| A2 whole-sample normalization | The only normalization opcode is `zscore_causal` with a finite window. |
| A3 bidirectional smoothing | Every window opcode is backward-looking; there is no centered variant. |
| A6 clock access | No opcode reads wall-clock time, so a spec cannot behave differently across runs. |
| arbitrary code execution | No `import`, no attribute access, no host call, no absolute indexing. |

This is the highest-leverage result of the iteration: five attack classes are removed from the threat
model by expressiveness reduction rather than by detection. Detection was the part that iteration 2
showed cannot be trusted.

The residual risk is honestly stated: the interpreter itself is Python, and a defect in the
interpreter reintroduces every attack at once. The interpreter is therefore in-scope for the
spike-in harness of section 6, and is treated as EdgeLab code under the existing test regime, not as
generated content.

## 3. Canonical AST and the deduplication contract

A generative loop that proposes indicators will re-propose the same indicator in different clothing.
If that is not detected, the multiple-testing budget is silently inflated and every downstream
significance claim is void.

Canonicalization rules for v0, in order:

1. **Structural normalization.** Operands of commutative opcodes (`add`, `mul`, `min`, `max`, `and`,
   `or`) are sorted by the canonical hash of the operand subtree. `sub(a,b)` is rewritten to
   `add(a, neg(b))`; `gt`/`ge` are rewritten to `lt`/`le` with swapped operands.
2. **Identity elimination.** `add(x, const 0)`, `mul(x, const 1)`, `neg(neg(x))`, `not(not(x))`,
   and `roll_*(x, window=1)` where the reduction is idempotent are reduced.
3. **No constant folding across parameters.** A `const` node carrying a `param_name` is never folded,
   because folding would destroy the family structure needed for budget accounting.
4. **Serialization.** Canonical form is emitted as UTF-8 JSON with sorted keys and no insignificant
   whitespace. `spec_id = sha256(canonical_serialization)`.
5. **Family hashing.** Replace every `const` node carrying a `param_name` with a hole marker, then
   recanonicalize. `family_id = sha256(family_serialization)`.

The deduplication claim is deliberately weak and stated as such:

> Canonical hashing detects **syntactic** duplication after normalization. It does **not** detect
> semantic equivalence. Two specs with different ASTs can produce identical series on all data.

The literature on AST-based clone detection is unambiguous that structural equality is a proxy, not
equivalence. Therefore v0 adds a second, empirical layer:

- **Behavioral fingerprint.** After compilation, evaluate the spec on a fixed, small, pre-registered
  reference slice and hash the quantized output series (quantization at the declared `atol`). Two
  specs with different `spec_id` but identical behavioral fingerprint are flagged as an
  **empirical duplicate** and charged as one trial.
- The reference slice must come from an integrity-PASS dataset and must be disjoint from any slice
  used for evaluation. Until integrity is PASS, the behavioral fingerprint layer is unavailable, and
  the honest consequence is that budget accounting is a **lower bound** on the true number of trials.

## 4. The four verdicts, and why two are not enough

Every gate returns exactly one of:

| Verdict | Meaning | Downstream effect |
|---|---|---|
| `PASS` | The attack was tested for and not found, with adequate power. | Spec advances. |
| `FAIL` | The attack was found. | Spec killed. Recorded permanently. |
| `ABSTAIN` | The gate could not run correctly (missing field, numeric failure, corrupt input). | Spec does not advance. Not a negative result. |
| `INSUFFICIENT_POWER` | The gate ran but the sample cannot support the conclusion. | Spec does not advance. Not a negative result. |

Collapsing these to a boolean is forbidden. This is a direct consequence of iteration 2: Freqtrade's
lookahead analyzer cancels itself when the number of trades is below a threshold, and its recursive
analyzer `break`s out of its own sweep at the first candle count showing no variance. Both conditions
surface to the operator as absence of a problem. In EdgeLab they are `INSUFFICIENT_POWER` and
`ABSTAIN` respectively, and neither may be reported as `PASS`.

The same taxonomy is required for run termination, adopting the one genuinely useful idea in
Hummingbot's executor: it distinguishes forced termination that leaves persisted residual exposure
(`CloseType.POSITION_HOLD`) from plain failure (`CloseType.FAILED`). EdgeLab needs the analogous
distinction because a recent diagnostic run died with `EXIT=1` and produced no output, and there was
no vocabulary to say whether partial artifacts existed. Run termination states for v0:
`COMPLETED`, `FAILED_NO_ARTIFACTS`, `TRUNCATED_WITH_PARTIAL_ARTIFACTS`, `ABORTED_BY_OPERATOR`.

## 5. Gate contracts

Gates G1–G3, G6 and the code-execution class are discharged by the schema (section 2) and are recorded
as `STRUCTURALLY_PREVENTED` rather than as passing gates. The gates that must actually be built:

### G4 — Bar-label / signal-availability gate
Run the spec twice on the same slice: once with the declared `emit_at: bar_close`, once with emission
shifted one bar later. If any downstream event count changes by more than the declared tolerance, the
spec depends on the exact labelling convention and is `FAIL`.

### G5 — Session-boundary gate
Evaluate with `session_boundary: reset` and with `carry`. A spec whose event population changes
materially is boundary-sensitive; it is not automatically killed, but the sensitivity is recorded and
the spec must declare the intended behavior. Undeclared sensitivity is `FAIL`.

### G7 — Warmup-stability gate
The idea is Freqtrade's; the implementation is explicitly not. Requirements that fix the four defects
found in `recursive.py`:

- Sweep **all** declared warmup values. No `break` on the first negative. A sweep that terminates
  early is `ABSTAIN`, never `PASS`.
- Compare the **whole** overlapping series, not `iloc[-1]`. Report the fraction of positions that
  differ and the maximum deviation, not a column name list.
- Use the declared `atol`/`rtol`, never exact float inequality.
- Evaluate on all instruments in scope, not `whitelist[0]`.
- Missing `warmup_bars` is a validation rejection, which is the one Freqtrade behavior worth copying.

### G8 — Prefix-invariance gate (the replacement for lookahead analysis)
Truncate the input at time `t`, evaluate, and compare against the same positions in the full-sample
evaluation. The comparison population is **every bar position**, not every executed trade.

This is the central correction of iteration 2. Freqtrade's analyzer iterates over materialized trades
and additionally skips `force_exit` rows to avoid a false positive, creating a declared blind spot. A
detector whose population is downstream of signal generation cannot see a leak that does not generate
a trade — and EdgeLab's detectors live in queues, where most bars generate nothing.

Required outputs: fraction of positions differing, maximum absolute and relative deviation, first
differing position, and the number of truncation points tested. A single truncation point is
`INSUFFICIENT_POWER`.

### G9 — Determinism gate
Two runs with identical inputs and identical declared config must produce bit-identical output
hashes. Any difference is `FAIL`, not tolerance-adjusted. This is the gate NautilusTrader's engine
model genuinely supports; its indicator trait does not, since the trait exposes `name`,
`has_inputs`, `initialized`, `handle_*` and `reset`, and nothing about availability time.

### G10 — Attribution gate
Identical cut boundaries must produce identical attribution. This gate exists because of a live
finding in this project: bar cuts matched at `30994/30994` while event attribution diverged in roughly
81.6% of bars. Cut parity is therefore explicitly **not** evidence of attribution parity, and G9/G10
must be reported separately and never merged into one "parity" claim.

### G11 — Budget gate
Before evaluation, the full parameter grid must be pre-registered with its `family_id` and cardinality.
Evaluating a spec whose family budget was not declared in advance is `FAIL`. Expanding a grid after
seeing any verdict is `FAIL` for the whole family.

Significance reporting must use a deflation that accounts for the number of trials and their
dependence, following Bailey and López de Prado's deflated Sharpe ratio construction: with enough
trials a spurious high Sharpe is guaranteed, and the correction requires the count of **effectively
independent** trials, i.e. clusters, not raw configurations. Because the behavioral-fingerprint layer
of section 3 is unavailable until integrity is PASS, the effective trial count is currently a lower
bound, and any deflated statistic computed now would be **optimistically biased**. The honest position
for v0 is therefore: record the ledger, do not yet publish a deflated statistic.

### G12 — Firewall gate
Static check that no artifact reachable by the proposer contains a verdict, a return, a ranking, or a
`parent_spec_id` derived from an evaluated result. Any breach voids the whole generation and the
affected specs cannot be rehabilitated.

## 6. The spike-in harness — how a gate earns the right to exist

No gate is trusted on inspection. Each gate must be validated by seeded fault injection.

For each attack class, a mutation operator produces a family of specs (or interpreter mutants, where
the attack lives below the DSL) that provably contain the defect. The harness measures:

- **Sensitivity**: fraction of seeded defects detected. Required: 100% on the declared mutant set.
- **Specificity**: false-positive rate on a matched set of clean specs. Required: 0 on the declared
  clean set.
- **Silence rate**: fraction of runs ending in `ABSTAIN` or `INSUFFICIENT_POWER`. Reported always. A
  gate with high silence rate and 100% sensitivity is still not usable, because in production the
  silence is what the operator will actually see.

A gate failing its own spike-in test is marked `BLIND`. Its attack class is then quarantined and any
spec exposed to that class cannot advance. This inverts the usual default: the burden is on the gate
to demonstrate detection, not on the operator to demonstrate a leak.

Mutant sets must be pre-registered by hash, exactly like predictions, so that a gate cannot be tuned
against a mutant set that is subsequently edited.

### Kill criteria for the whole generative program

- If G8 sensitivity is below 100% on the seeded prefix-leak mutants, the factory does not open.
- If G9 cannot demonstrate bit-identical replay, no other gate result is interpretable and the
  program stops.
- If G12 finds any breach, the generation is void.
- If silence rate on real data exceeds 50% for any gate, the gate is reported as uninformative and
  cannot be used to justify advancing a spec.

## 7. Evidence store

Requirements, all of them reactions to specific defects found:

1. **Append-only.** No rotation, no eviction. TradingAgents' memory layer applies rotation that drops
   the oldest *resolved* entries, which destroys precisely the closed evidence. Forbidden here.
2. **Content-addressed.** Every manifest entry carries sha256 of spec, dataset slice, interpreter
   version, config, and output. Freqtrade compares runs by confidence value with no dataset hash and
   no environment signature; that comparison is not reproducible.
3. **Negative results retained permanently.** A `FAIL` is the most valuable record in the store.
4. **Environment captured.** Interpreter version, platform, memory ceiling. Relevant because runs have
   already been shaped by an 8 GB machine with under 1 GB free.
5. **Checkpointed.** A long run must be resumable. The current 201-session census has no checkpointing
   and a truncation loses everything, which is how `TRUNCATED_WITH_PARTIAL_ARTIFACTS` became a needed
   state rather than a hypothetical one.

## 8. Separation of planes, stated as an invariant

```
proposer  --IndicatorSpec-->  compiler  --compiled spec-->  evaluator  --verdict-->  ledger
    ^                                                                                  |
    |                                                                                  |
    +-------------------------------- NO EDGE ------------------------------------------+
```

The missing edge is the design. Iteration 2 confirmed in source that TradingAgents closes exactly this
loop by injecting resolved, return-labelled entries into the prompt. v0 forbids the edge structurally
via `provenance.proposer_saw_outcomes: false` (a `const` in the schema, so unsatisfiable otherwise)
and checks it at runtime via G12.

A loop is scientifically admissible **only** after every gate has passed its spike-in test and only
with the feedback channel restricted to gate verdicts on pre-registered families, never to returns.
That is out of scope for v0 and must not be built earlier.

## 9. Status of the research hypotheses

| Hypothesis | Status after iteration 3 |
|---|---|
| R1 small DSL is sufficient | Supported and now concrete: five attack classes eliminated by expressiveness reduction. |
| R2 proposer/evaluator firewall | Supported; encoded as an unsatisfiable-otherwise schema constant plus G12. |
| R3 canonical AST + dedup | Partially supported. Syntactic dedup specified; semantic dedup needs the behavioral fingerprint, which is blocked on integrity. |
| R4 look-ahead and recursion gates | Reformulated. Concept retained, implementations rejected, replaced by G7/G8 with population-level comparison. |
| R5 micro-oracle | Narrowed to determinism and event ordering (G9). It cannot certify absence of look-ahead. |
| R6 immutable content-addressed evidence | Supported; specified in section 7. |
| R7 four termination states | Supported; specified in section 4. |
| R8 (new) gates must be validated by seeded faults before use | Asserted, not yet tested. This is the single largest open risk in the design. |

## 10. Honest limits of this iteration

- Nothing here has been executed. The schema has not been validated against a single instance, and no
  gate has been implemented or run.
- The behavioral-fingerprint layer is blocked on source integrity, so trial counting is currently a
  lower bound and no deflated statistic should be published.
- The interpreter is the single point of failure that the design does not eliminate; it only moves the
  risk into EdgeLab-owned code.
- Backtrader, FinRL, CCXT and the Polymarket CLI were not inspected in iterations 2 or 3 and
  contributed nothing to this design.
- No claim is made that the gate set is complete. It is only claimed to be falsifiable.

## 11. Handoff to iteration 4 (GPT, audit and synthesis)

Iteration 4 must be **shorter** than iterations 2 and 3 and must not add new machinery. Its job:

1. Attack this design, in this order: (a) find an attack class that is neither structurally prevented
   nor covered by G4–G12; (b) find a way to express a leak inside the v0 opcode set; (c) check whether
   any gate's required output is unobtainable in practice.
2. Verify the canonicalization rules do not collapse two semantically different specs into one
   `spec_id`, which would be a worse failure than missing a duplicate.
3. State plainly whether v0 is buildable in the current blocked state, or whether the correct decision
   is to build nothing until integrity is PASS and the universe reaches 200 sessions.
4. Preserve disagreements between iterations explicitly. Iteration 2 downgraded iteration 1's ranking;
   iteration 4 must not smooth that over into a consensus that never existed.
