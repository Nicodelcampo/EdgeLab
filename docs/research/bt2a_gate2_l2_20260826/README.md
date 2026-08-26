# BT2A Gate 2 + Gate L2 audit package

Status: implementation hardened; outcome runs not authorized.

## Ordered reading

1. `../BT2A_GATE2_L2_START_HERE_2026-08-26.md`
2. `01_GATE1_AND_ANTIGRAVITY_AUDIT.md`
3. `02_GATE2_FIRST_PASSAGE_CONTRACT.md`
4. `03_GATE_L2_CONTEXT_CONTRACT.md`
5. `04_WEB_RESEARCH.md`
6. `05_EXECUTION_PLAN.md`
7. `06_HARDENING_IMPLEMENTATION.md`
8. `07_FINAL_HARDENING_AUDIT.md`
9. `CLAUDE_CODE_LOCAL_AUDIT.md`
10. `STATUS.json`

## Use

- Use `07_FINAL_HARDENING_AUDIT.md` as the current implementation and blocker summary.
- Keep Gate 1 as the frozen detection definition.
- Treat Gate 2 as post-outcome diagnostic until its spec is reviewed, frozen, and separately authorized.
- Treat Gate L2 as target-free validation until extraction provenance, hashes, causal joins, and sample power pass.
- Keep `EDGE_DECLARED=false`.
- Do not open new P2 or L2 outcomes, do not freeze the Gate-2 spec implicitly, and do not use `--resume` on the old partial sweep.
