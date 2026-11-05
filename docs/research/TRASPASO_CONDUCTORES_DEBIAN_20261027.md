# Traspaso de los conductores del embudo al Debian (2026-10-27)

Estado: VIGENTE. Los conductores locales (sesión en la nube de Nico) están FRENADOS desde el 2026-10-26 ~22:00 UTC; no se relanzan.
Todo el estado está commiteado en la rama `claude/vibrant-clarke-s9z6e2` (PR #138).

## Dónde está cada cosa
- **Configuración de cada campaña**: `config/autopilot/grillas/campanas/<CID>.json` (24 con `"conductor": "local"`; `LEEME.md` explica
  los campos). Pasar a Debian = cambiar ese campo.
- **Estado de cada campaña** (etapa, fase, handle de Kaggle, cortes, candidatas, MEDIDO.md): `docs/research/<estudio>/embudo/<CID>/`.
  Raíces: `u1_cfd_20261025/embudo`, `u1_zonas_20261025/embudo`, `expansion_zonas_20261023/embudo`, `u1_oro_20261025/embudo`,
  `zonas_gaps_20261025/embudo`. Copiar estos directorios a `autopilot_runs/embudo/` conserva el progreso; si no, cada campaña
  arranca de cero.
- Conductor: `tools/embudo_correr.py <campaña.json> --raiz <dir embudo>` (lock `.conductor.pid`; frenar con `--detener CID`, nunca `pkill -f`).

## Campañas que siguen vivas (no FIN)
| CID | etapa | raíz |
|---|---|---|
| U1-ZONAS-BT2-ES | DESC | u1_zonas_20261025 |
| U1-ZONAS-BT2-NQ | INTEGRIDAD (3 candidatas) | u1_zonas_20261025 |
| U1-RACIMOS-GRILLA-ES | INTEGRIDAD (2 candidatas) | u1_zonas_20261025 |
| U1-RACIMOS-GRILLA-NQ | INDAGA | u1_zonas_20261025 |
| U1-ZONAS-GRILLA-YM | INDAGA (1 candidata) | u1_zonas_20261025 |
| U1-6E-GRILLA | PISTAS (réplica) | u1_cfd_20261025 |
| U1-YM-GRILLA, U1-ES-GRILLA | CONTEO (esperan holdout) | u1_cfd_20261025 |
| U1-ZONAS-ES, U1-ZONAS-AVCL-NQ | CONTEO | u1_zonas_20261025 |
| U1-ZONAS-NQ | CONTEO | zonas_gaps_20261025 (ojo: raíz distinta) |
| U1-ORO-GRILLA | CONTEO | u1_oro_20261025 |
Las CONTEO esperan sesiones del holdout: sólo avanzan en la máquina con la carpeta sellada (`--sellado`).
Terminadas (FIN): EXPZ-NQ/CFD, ZGAP-NQ/CFD (PISTAS_VIVAS), U1-6B-FUT, U1-ZONAS-BT2-YM (PISTAS_VIVAS), U1-6E-FUT, U1-6E-CONFIRMA-GBP,
U1-6B, U1-RACIMOS-GRILLA-YM (SIN_CANDIDATAS), U1-ZONAS-AVCL-ES (SIN_POTENCIA_HOLDOUT). LUXG-* y U1_CRUZADO no tienen estado de embudo acá.

## Pendientes fuera del embudo
- Analizador de celdas no confirmadas (`tools/analizar_embudo.py lanzar|traer`, handles en `docs/research/analizador_embudo_20261026/`):
  faltan varias campañas por el tope de Kaggle; relanzar con `lanzar` (saltea las ya lanzadas).
- ATRAS de EXPZ-CFD y ZGAP-CFD: hechos (`docs/research/atras_20261026/`).
