# Iteration 4 (GPT) — Adversarial audit and final synthesis

- Date: 2026-08-04
- Audited commit: `b90b3ab3768197f3a184bc3e58b1e2873728300b`
- Artifacts: `specs/indicatorspec_v0.schema.json`, `docs/research/ITERATION_3_OPUS_2026-08-04.md`

## Decision

> **Reject `IndicatorSpec v0` as an implementation specification. Preserve it as a research draft.**

The architecture survives: small declarative language, deterministic compiler, outcome firewall,
append-only evidence and seeded gate tests. The concrete schema does not. Valid documents can exploit
undeclared fields, canonicalization can collapse numerically different programs, and several gates
require observations absent from the proposed execution model.

## 1. Missing attack class: upstream point-in-time leakage

The DSL prevents negative `lag`, but trusts fields supplied by the input producer. If a field was
computed with future data, revised history, a final-session aggregate or a late timestamp, the AST is
syntactically causal and G8 can still pass because both evaluations receive contaminated values.

The schema exposes the hole directly: `field` is an unrestricted string and JSON Schema cannot ensure
it belongs to `inputs.fields`. There is no `event_time`, `available_time`, producer hash, revision rule
or point-in-time cutoff. Thus this node validates:

```json
{"op":"field","field":"session_final_high","lag":0}
```

If the interpreter resolves host columns by name, it leaks the future. If it rejects the node, that
protection exists only in unwritten interpreter behavior, not in the schema claimed to prevent it.
Even a declared `close` can leak when its `available_time` is after the decision cutoff.

**Conclusion:** `lag >= 0` constrains interpreter indexing; it does not prove causal availability. The
data producer belongs to the trusted computing base.

## 2. Canonicalization fails under float64

Iteration 3 sorts operands of `add`, `mul`, `min` and `max`, while requiring deterministic
left-to-right float64 reduction. These commitments conflict:

```text
add(1e16, -1e16, 1)  -> 1
add(1e16, 1, -1e16)  -> 0
```

Sorting both to one representation assigns one `spec_id` to programs that can emit different series.
That is worse than missing a duplicate.

Other unsafe cases:

- `min`/`max` reordering can alter NaN and signed-zero behavior;
- `and`/`or` reordering can alter short-circuit or tri-state abstention;
- `sub(a,b) -> add(a,neg(b))` needs an exact IEEE-754 policy;
- `roll_*(x,1)` is not generically `x`: `roll_std` and `roll_rank` differ;
- family holes omit parameter domains, units and binding locations.

**Correction:** canonicalize JSON representation and proven opcode aliases only. Do not reorder
floating-point operands. A false negative in deduplication is safer than a false equivalence.

## 3. Internal contradictions

1. `spec_id` and `family_id` are required although the compiler is said to assign them and a proposer
   supplying `spec_id` is said to be an error. Proposal and compiled output require separate contracts.
2. `session_boundary` has a default but is optional. Validation does not apply defaults.
3. `numeric.reduction_order` is optional although determinism depends on it.
4. `period_value` is optional for every stream; no conditional rule defines when it is required.
5. Arity is not defined by opcode: `neg` accepts three arguments, `add` one, `if_else` one or two.
6. One `expr` coexists with multiple outputs without an expression-to-output mapping.
7. Output IDs need not be unique.
8. `warmup_bars` is one integer, but G7 requires sweeping “all declared warmup values”.
9. `first_touch_after_creation_bar` is an EXPLORE outcome anchor, not generic indicator availability.
10. `proposer_saw_outcomes: false` is self-attestation, not proof of isolation.

## 4. Gates that are undefined or observe the wrong layer

- **G4:** delaying a legitimate event series normally changes event counts. No null or alignment rule
  distinguishes expected delay from label dependence.
- **G5:** “materially” has no threshold.
- **G7:** the requested warmup sweep is absent from the schema.
- **G8:** truncation schedule and power criterion are undefined and upstream contamination is invisible.
- **G10:** cut boundaries and event-to-bar attribution are not represented by `IndicatorSpec` outputs.
  This is a measurement/bridge gate, not an indicator gate.
- **G11:** charging once per family undercounts a parameter search. Families describe dependence; they
  do not turn many evaluated configurations into one trial.
- **G12:** static inspection cannot prove that files, prompts, model memory, people and processes lack
  access to outcomes. The firewall must be a capability/process boundary.

## 5. Behavioral fingerprint is not a trial merger

Two expressions equal on a small reference slice can diverge elsewhere. Merging them as one trial
optimistically lowers multiplicity when the slice lacks distinguishing power. A fingerprint may flag
a duplicate candidate for audit; it must not automatically merge trial counts. Until dependence can
be estimated defensibly, count every evaluated compiled spec and retain family/fingerprint only as
clustering metadata.

## 6. What survives

- Declarative DSL instead of generated Python.
- Separate proposer, compiler, evaluator and ledger.
- No return-labelled proposal memory.
- Population-level prefix tests, not trade-conditioned tests.
- `PASS`, `FAIL`, `ABSTAIN`, `INSUFFICIENT_POWER`.
- Seeded defects before trusting any gate.
- Immutable, content-addressed evidence retaining negative results.
- NautilusTrader only as a possible determinism/event-order reference.
- Freqtrade only as inspiration for prefix/warmup questions, not reusable gate code.
- Hummingbot only for termination/exposure taxonomy.
- TradingAgents only for role separation; its memory remains prohibited.

## 7. What does not survive

- The optimistic repository ranking from iteration 1; iteration 2 materially downgraded it.
- The claim that AST restrictions alone guarantee causal availability.
- Commutative canonicalization under left-to-right float64.
- Behavioral fingerprint merging trial counts.
- A schema constant as an outcome firewall.
- G10 as an indicator-level gate.
- The present schema as implementation-ready.

There was no consensus. The progression was:

```text
documentation-based optimism
-> source-based downgrade
-> contract proposal
-> contract rejection and narrowed synthesis
```

## 8. Build/no-build decision

The answer is split but unambiguous:

- **Do not build** the adaptive factory, evaluator over project data, behavioral fingerprint or DSR
  path. Integrity remains blocked and the universe remains 193 versus 200.
- **Do not implement** `IndicatorSpec v0` as committed; it failed independently of the data blockers.
- **Permissible before integrity PASS:** revise contracts on paper, validate schemas with synthetic
  instances, specify typed opcode semantics, test canonicalization with adversarial float examples,
  and design interpreter mutants without reading project outcomes.
- **After integrity PASS but before 200 sessions:** infrastructure/gate validation may use a strictly
  separate integrity-clean diagnostic slice, but EXPLORE and any candidate evaluation remain closed.
- **Only after integrity PASS, N>=200, and spike-in PASS:** consider a fixed, non-adaptive pilot with a
  pre-registered finite family. The proposer still receives no verdicts or returns.

## 9. Minimum repair list for a future v0.1

This is not an implementation authorization. A replacement contract must at least:

1. split `ProposalSpec` from `CompiledSpec`;
2. type every opcode and enforce exact arity;
3. bind field references to a signed input schema carrying `event_time` and `available_time`;
4. require all runtime-relevant properties rather than relying on defaults;
5. remove unsafe algebraic reordering;
6. separate indicator availability from outcome anchoring;
7. move attribution parity to the measurement/bridge contract;
8. treat every evaluated parameterization as a trial while recording dependence metadata;
9. replace firewall self-attestation with a capability boundary;
10. define every gate threshold, population, schedule and power rule before execution.

## Final verdict

> The factory idea is scientifically defensible only in a narrower form than iteration 1 proposed and
> iteration 3 specified. The correct next move is **contract repair on synthetic data, not candidate
> generation**. Dirty source data and insufficient sample size block evaluation; defects in v0 block
> implementation. These are independent blockers and neither can excuse the other.
