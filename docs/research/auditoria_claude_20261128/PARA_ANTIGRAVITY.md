# Para la auditoría de Antigravity: trabajo de Claude del 27 y 28-nov (2026-11-28)

Estado: PEDIDO DE AUDITORÍA — índice de lo que Claude hizo desde la última auditoría de Antigravity (`c168a770`), con los puntos donde
más conviene buscar errores. Rama `claude/vibrant-clarke-s9z6e2`, desde `c168a770` hasta `b86f0b2a`.

## Qué auditar
1. **Auditoría de la Espiral (fases 1 y 2):** `REVISION_ESPIRAL_ANTIGRAVITY.md` y `tools/auditoria_espiral_20261128.py`
   (`CARRIL2_VOL_LOCAL_SIN_HOLDOUT.json`).
   - ¿La máscara DESC+REP sobre entrada y salida es correcta?
   - ¿Es justo considerar holdout de la familia de Carril 2 a Dow, Russell y GC (y a EMD)?
   - ¿Los cortes de pre-FOMC por período y la lista de reuniones no programadas son correctos?
   - ¿MVC4 es beta, o hay algo que no vi?
2. **Revisión de su auditoría anterior:** el rechazo del CONFIRMA de CRIPTO-V3-2019 (`cripto_v3_2019_20261127/RESULTADO.md`
   §«Revisión Claude»).
3. **Guardas nuevas K58–K64:**
   - `edgelab/research/alineacion_horaria.py` y su test;
   - `tools/registro_global.py` (sin argumentos ya no consolida);
   - `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` y `LEER_ANTES_DE_CADA_CORRIDA.md` v5 §8.
   - ¿Falta alguna guarda en código para errores que hoy quedaron sólo en la guía (K59–K62)?
4. **Prácticas ATJ-28 a ATJ-31** (`docs/research_funnel_playbook.md`) y las dos palancas nuevas en FACTORES.
5. **Plan en espiral:** `docs/research/PLAN_ESPIRAL_20261127.md`. Antigravity ya ejecutó parte en la fase 2; falta el #2 (mecanismo de T
   por ETF apalancados).
6. **Bonos AR:**
   - `biblioteca_ideas_20261028/OPERACIONES_AMIGO_AL29_AL30_MATRIZ_20261127.md`;
   - el grabador `tools/bonos_masella_grabar.py`, que lee la planilla pública de Masella como CSV;
   - `RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md` §6–§8. La §8 recomendaba TradingView, y su §9 lo corrigió (K62).
7. **Linajes:** las 7 familias de la Espiral quedaron declaradas en `LINAJES.jsonl` con padres. ¿Los padres son los correctos?

## Siguiente paso propuesto, pendiente de Nico
Pre-FOMC: corregir el calendario (sólo reuniones programadas, salida 5 minutos antes del comunicado real) y pre-registrar la lectura de
su HOLDOUT A5 con plan de potencia.
