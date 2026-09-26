> **SUPERADO (2026-09-21).** Este plan nombra `corridor_engine.js` y `crosshair_density_profile.js` como motores del visor.
> Por decisión de Nico hay UNA definición de corredor (`density_field.py`, HP-007) con un puerto JS verificado
> (`density_field.js`); ambos archivos fueron archivados. Vigente: `docs/research/VIEWER_UNIFICATION_PROPOSAL_20260921.md`.

# EdgeLab viewer unification plan

## Decision

`viewer/nt8_bridge/index.html` is the only canonical production entrypoint. Research, certification and diagnostic pages remain specialized fixtures and must not diverge into competing products.

## Remote inventory

The current canonical shell already contains multi-chart tabs and `tick_25`, HFT liquidity corridors, fixed and volume-consumption modes, causal `available_ts`, corridor certification/invariance tests, and the multi-asset 25t builder.

The separate `feat/crosshair-density-profile-20260918` lineage adds a bounded deterministic density-profile kernel and tests, but its `index.html` is byte-identical to the current shell. This branch preserves the kernel without inventing a second viewer.

## Canonical files

- Production shell: `viewer/nt8_bridge/index.html`
- Feature registry: `viewer/nt8_bridge/viewer_manifest.json`
- Liquidity engine: `viewer/nt8_bridge/corridor_engine.js`
- Density kernel: `viewer/nt8_bridge/crosshair_density_profile.js`
- Multi-asset builder: `tools/build_multiasset_25t_hft_bundles.py`

## Specialized pages

`hft_corridor_preview.html`, `hft_corridor_certified.html`, `index_invariant.html` and `store_viewer.html` are fixtures, not alternate production versions.

## Non-negotiable invariants

1. No zone is tradable before `available_at`.
2. Tick identity preserves sequence where available.
3. Viewport changes cannot alter corridor membership or price geometry.
4. 25t bundles are data inputs, not embedded source-of-truth code.
5. A local feature requires source hash, diff, fixture and test before integration.
6. Holdout screenshots may verify rendering but cannot tune parameters.

## Pending local reconciliation

Antigravity must provide the unpublished M5 causal arrow/connector, formation-vs-active styling, any real volume-profile panel beyond the density kernel, and the local all-instrument 25t manifest. Those changes will be ported into modules and the canonical `index.html`; the local HTML will not become another entrypoint.

## Acceptance

One canonical URL; manifest and Playwright tests pass; corridors are causal; density/profile is deterministic and bounded; every available 25t instrument loads through the manifest; missing bundles fail visibly; no holdout-dependent defaults.
