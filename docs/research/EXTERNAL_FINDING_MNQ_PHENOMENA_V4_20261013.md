# Hallazgo externo registrado: componentes continuos vs etiquetas A/E (MNQ)

Origen: otro agente (Research Ops, PR #117, commit `8a5ce17`, rama `feat/research-ops-supervisor-mvp`). Verificado contra `MNQ_PHENOMENA_MODEL_V4_CLOSEOUT.md` y `_ANALYSIS.json` (números idénticos); no recontado de forma independiente.

- Pregunta: ¿predecir hacia dónde llega primero el punto medio a 60 s mejora con etiquetas A/E (absorción/agotamiento) sobre componentes continuos?
- Brier medio por sesión (3 clases, menor es mejor): históricas 0,6476; continuos 0,6015 (−7,12 %, mejor en 10/10 sesiones); +A/E 0,6016; +E 0,6014 (5/10); +A 0,6016.
- Lectura: la representación continua aporta; A/E no. Orientación: continuos + geometría/llegada a zonas AVZP2/racimos con controles de densidad.
- Límites: 10 de 12 sesiones (2 sin ticks), 70.544 anclas solapadas (no independientes), solo 2 sesiones de ajuste ya inspeccionadas, sin P&L, costos ni holdout. Nivel C (información).
- Dónde persiste: `config/autopilot/evidence_seed.json` (`MNQ_PHENOMENA_CONT_V4`), Brain (episodio `EXTERNAL-research-ops-mnq-phenomena-v4`, lección LOW L-MNQ-CONT-1), este documento. El Brain científico propio del otro agente tiene su propia propuesta (`MNQ_PHENOMENA_MODEL_V4_KNOWLEDGE_PROPOSAL.json`); no se concatenaron ledgers.
