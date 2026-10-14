# EdgeLab bridge snapshot provenance

`edgelab/bridge/` and `edgelab/research/avolclusterpoi_funnel.py` were recovered verbatim from the private Kaggle code snapshot `nicolasbuttaro/edgelab-code-20260928` during the MGC infrastructure work.

The bridge contains the existing indicator and parity implementations needed to add HFTZones, BigTrap2, BigTrap2Absorption, aVolCluster/POI, volume-cell POI and related families without reimplementing their semantics.

Rules:

- recovered code is not evidence of edge;
- frozen/parity-sensitive indicator semantics must not be modified inside funnel adapters;
- each adapter requires synthetic, prefix and parity tests before entering D0;
- artifacts produced by older canonicalization or roll policies remain stale;
- D2 and statutory holdouts stay closed until a family is frozen and promoted.
