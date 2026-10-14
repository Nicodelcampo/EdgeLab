# Pendientes para Nico — release `liquid_tick_v1` (2026-10-14)

## Estado
- Publicado (PRIVADO): `nicolasbuttaro/edgelab-liquid-ticks-20261014`, estado `CANDIDATE_NOT_RESEARCH_APPROVED`.
  14 activos, un Parquet por activo (`data/<ACTIVO>_ticks.parquet`), contrato líquido causal por sesión, sin holdout
  (trade date >= 2026-10-01). Descarga verificada: 31 archivos con tamaño + SHA-256 contra el manifiesto.
- **Cómo entra un agente:** leer `README_AGENTES.md` del dataset; usar `edgelab/data/liquid_release/release_reader.py`
  (`load_manifest`, `read_asset`). Informe completo: `docs/infra/LIQUID_RELEASE_20261014.md`; D01–D23 en `ISSUE_RESOLUTION_LOG_20261014.json`.
- Espacio de Kaggle etiquetado (41 datasets con prefijo de estado) e índice `KAGGLE_SPACE_INDEX.md/json` dentro de `edgelab-data-catalog`.
  **No se borró nada.** Candidatos a borrar mañana: los `[REEMPL]`, `[ARCHIVO]`, `[CUARENTENA]` (lista en el índice).
- Rama local `data/liquid-release-20261014` con los commits; **no se pudo pushear** (git pide credenciales).

## Exports que faltan (detalle por contrato y rango: `MISSING_EXPORTS_20261014.md` / `.csv`)
Se exportan con el AddOn `EdgeLabTickHistory` (un archivo por día, UTC).
- **P0 (sesiones excluidas o indeterminadas):** 321 sesiones aprox. Lo grueso: MGC 2025-08-01→2025-10-06 (46 ses.) y MGC 06-26/08-26;
  MYM 2025-08→2026-08 (42 ses. sin ningún contrato) y MYM 06-26/12-26; RTY 2025-08→2025-12 (44 ses.);
  YM 06-26 y 09-26; MNQ 09-26 (12 ses.); y los 2026-09-28→30 de 6B, 6E, 6J, ES, NQ (cola del período sin export).
  Navidad (2025-12-25) y 2025-11-27 aparecen por activos con ticks parciales: confirmar si el export existe.
- **P1 (hoy se usa parquet derivado, falta el texto original):** RTY (≈230 sesiones, casi todo el año), MYM (31), MES (8), MNQ (5), ES/NQ (1).
- Tras exportar: se re-corre el mismo proceso (`tools/build_release.py` → verify → publicar nueva versión).

## Decisiones tuyas
1. Aprobar o ajustar la política de liquidez (hoy propuesta, `approved_by=None`).
2. Licencia/redistribución de datos CME (ILA); mientras tanto todo privado.
3. Calendario oficial CME (hoy derivado de los datos; D06 bloqueado hasta tenerlo).
4. Credenciales git para pushear la rama.
