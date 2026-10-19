# HP007-CAMP-002 — canonical bootstrap

## Authority and precedence

This document supersedes only the branch/bootstrap instructions in section 2 of `PROMPT_ANTIGRAVITY_HP007_CAMP002_REJECTION_REVISIT_2026-09-15.md`. All remaining research, safety, parity, field, episode, inference and deliverable instructions in that document remain mandatory.

## Immutable contractual anchor

- Repository: `Nicodelcampo/EdgeLab`
- Canonical contract branch: `work/universal-contract-regime-v2-20260915`
- Canonical anchor commit: `29cad93d6600ee4c07a7d716be35e4881d78f491`
- Status: `PARTIAL_MULTI_ASSET_CERTIFICATION`
- Enabled roots: `ES`, `MES`, `NQ`, `YM`
- Conditional root: `MNQ`, only with both gap windows excluded by code and reported
- Abstain roots: `6B`, `6E`, `6J`, `GC`, `ZB`, `MBT`

Do not start the campaign from HP007-CAMP-001. Its evidence remains preserved but its execution mechanics are superseded.

## Foundation commits to transplant

The following additive commits contain the causal campaign primitives and prompt:

1. `c417d36c05b0a1484b4bf275ffe56119e3f35f97`
   - `edgelab/research/corridor_campaign_v2.py`
   - `tests/research/test_corridor_campaign_v2.py`
   - `docs/research/HP007_CAMPAIGN_V2_FOUNDATION_2026-09-15.md`
2. `d510e29e69419156bf9ae0d0505c73cc3cc03197`
   - `edgelab/research/void_revisit_episodes.py`
   - `tests/research/test_void_revisit_episodes.py`
   - detailed Antigravity execution prompt

They are additive and should be cherry-picked in this order onto the contractual anchor.

## Exact bootstrap procedure

```bash
git fetch origin --prune
git status --short
git switch --detach 29cad93d6600ee4c07a7d716be35e4881d78f491
git switch -c work/hp007-rejection-revisit-campaign-v2-20260915
git cherry-pick c417d36c05b0a1484b4bf275ffe56119e3f35f97
git cherry-pick d510e29e69419156bf9ae0d0505c73cc3cc03197
```

If the target branch already exists, do not overwrite or force-push it. Inspect its ancestry and either continue only if it descends from `29cad93`, or create a uniquely suffixed replacement branch and document why.

After cherry-picking, amend the working copy of the detailed prompt so its section 2 points to this bootstrap and `29cad93`; commit that documentation-only correction before implementation work.

## Mandatory preflight before development

Record and verify:

```bash
git merge-base --is-ancestor 29cad93d6600ee4c07a7d716be35e4881d78f491 HEAD
git status --short
pytest tests/data/ -q
pytest tests/research/test_corridor_campaign_v2.py tests/research/test_void_revisit_episodes.py -q
```

Preflight output must include:

- exact HEAD and tree SHA;
- clean/dirty tracked state;
- ancestry result;
- collected/passed/failed/skipped tests;
- confirmation that no holdout rows were read;
- presence of the ten lineage columns;
- reset behavior at every `state_reset_flag`.

Do not begin parity or episode outcome work if preflight fails.

## Stage order

1. Bootstrap from `29cad93` and transplant the additive v2 foundation.
2. Implement the four episode censoring reasons in executable code and tests, not documentation only.
3. Audit BigTrap2Absorption parity independently for `ES`, `MES`, `NQ`, `YM`; do not infer cross-asset parity.
4. Build target-free causal zone streams and fields, resetting all state at contract roll.
5. Build and validate the rejection → away → revisit state machine.
6. Audit a secondary indicator; prefer Gaps2 only if a real NT8 oracle proves parity for the exact setup.
7. Perform target-free configuration screening and stream deduplication.
8. Commit and push preregistration separately.
9. Only then generate structural traversal/penetration outcomes. Do not optimize P&L or search for an edge.

## Roll boundary rule

At every `state_reset_flag == True`:

- terminate active episodes as `CENSORED_CONTRACT_ROLL`;
- clear indicator state, zones, touches, fields, normalizers, frozen corridors and pending matches;
- never carry information across standard/micro instruments or contract regimes.

Session, data-edge and max-followup censorship must remain distinct:

- `CENSORED_SESSION_END`
- `CENSORED_CONTRACT_ROLL`
- `CENSORED_DATA_EDGE`
- `CENSORED_MAX_FOLLOWUP`

## First checkpoint

Before any broad parameter sweep, publish one additive checkpoint commit containing:

- branch/base/provenance manifest;
- executable reset and censorship integration;
- BigTrap2Absorption parity matrix for the four enabled roots;
- explicit abstentions where a real oracle is absent;
- target-free smoke census on a small pre-holdout development slice;
- full test evidence.

Stop and report at that checkpoint if parity is not established. Do not compensate for missing parity by proceeding to structural outcomes.