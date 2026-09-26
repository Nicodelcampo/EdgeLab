# Prompt para el agente local (Antigravity) — aVol tick formal

Paso 0, siempre:

```bash
git fetch origin research/bigtrap2-local-displacement-null
git checkout research/bigtrap2-local-displacement-null
git merge --ff-only origin/research/bigtrap2-local-displacement-null
git status   # arbol limpio; si esta sucio o el fetch falla, ABSTAIN y reportar
```

HEAD esperado: incluye `b0e0913` o posterior. Verificar con `git cat-file`
DESPUES del fetch (leccion F2.8: no abstener por un grafo atrasado).

Sos el implementador de la formal por ticks de aVolClusterPOI. No reinterpretes
la sonda M1. No ajustes el detector.

## Leer primero, en este orden

1. `specs/avolcluster_tick_formal_v0.json` (la ley de esta corrida)
2. `docs/research/AVOL_TICK_FORMAL_PROTOCOL_2026-08-14.md`
3. `docs/research/AVOLCLUSTER_V21_OUTPUT_AUDIT_2026-08-14.md` (por que random es el benchmark primario)
4. `edgelab/bridge/indicators/avolclusterpoi.py` (kernel v0.5 congelado)
5. `diag/tasa_senales/F2.7_nulo_reflexion_local.py` (maquinaria de carrera a reusar)
6. `edgelab/bridge/bars.py` (build_time_bars, build_footprints, p1a_gate, session_ids)

## Oraculo P2

Si `data/nt8_oracles/avolcluster_v05_20260813.csv` no esta en el repo, copialo
desde `C:\EdgeLab\avolcluster_v05_20260813.csv` y commitealo primero (commit
separado: `chore(avol): add NT8 v0.5 oracle CSV for P2`). Si el archivo no
existe en ninguno de los dos lados, ABSTAIN y pedirlo.

## Datos canonicos (verificar SHA-256 ANTES de correr; mismatch => abortar)

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

Firewall: corte 2026-06-30. Holdout fuera. `outcomes_accessed=false`.

## Tarea

Implementar, aditivo, `diag/tasa_senales/avolcluster_tick_formal.py`:

1. **P2 primero.** Replay del kernel v0.5 sobre `6E_09-26` con ticks en
   [2026-04-10, 2026-06-30], warmup vacio al inicio de la ventana (como NT8).
   Barras M1 desde ticks (`build_time_bars`), footprints + `p1a_gate` (debe
   PASS; si no, ABSTAIN_P1A). Comparar contra las 133 filas ZONE_CREATED del
   oraculo: (lower_tick, upper_tick) exactos, bar_close_time ±1 min.
   P2_PASS exige 100% de match y cero zonas Python extra en la ventana.
   Si FAIL: reportar el diff completo y parar (`ABSTAIN_P2`).

2. **Formal.** Mismo kernel sobre los 4 parquets en orden cronologico
   (la historia de buckets acumula a traves de los archivos; el warmup lo
   maneja el kernel, sin filtros manuales). Carrera de primer pasaje con la
   maquinaria de F2.7: `construir_reflejo`, `zone_lifecycle` (CloseThrough,
   max_age 0, identico en ambos brazos), `first_passage_race`,
   `tick_first_touch` para ties, horizonte 2000 barras M1.
   Poblacion: solo OFF_PRICE (ZONE_CREATED). AT_PRICE no entra a la carrera.

3. **Controles.** Por zona: `control_random` (primario) y `control_nearest`
   (diagnostico, no citable), mismas reglas que el runner M1 v2.1: misma
   sesion, >12 barras de cualquier creadora, semilla deterministica
   `(session, bar)`, mismo `(d, w, side)` anclado en el close del control.

4. **Agregacion.** Media por sesion con ceros adentro, HAC Bartlett
   (lag = ceil(sqrt(n))), IC95, contraste pareado por sesion
   (nunca sqrt(se1^2+se2^2)). Reportar: cats completas, frac_tie
   (informativo; los ticks resuelven), by_side, control_diagnostics.

5. **Etiquetas** con la misma logica que el runner M1 v2.1
   (AVOL_ZONE_EDGE / AVOL_BAR_CONTEXT / AVOL_NO_EDGE / AVOL_FADE_POCKET /
   AVOL_UNDERPOWERED / ABSTAIN_P2 / ABSTAIN_ALIGNMENT). Gates: P2_PASS,
   sesiones >= 30, resolucion >= 0.30, match random >= 0.40.

6. **Tests**: `tests/research/test_avolcluster_tick_formal.py` — mundo nulo
   sintetico, señal plantada, matcher P2 con oraculo sintetico (match exacto
   y un caso con una fila movida => FAIL).

## Entregables

- Commits en la misma rama, arbol limpio, HEAD reportado completo (40 chars).
- `diag/tasa_senales/AVOLT_formal_<sha12>.json` con payload_sha256.
- `docs/research/AVOLT_INFORME_2026-08-14.md`: P2 (match/diff), etiqueta
  emitida por la funcion de etiquetas (no por narrativa), tabla de brazos,
  gates, y UNA sola familia siguiente si alguna etiqueta OPEN aplica.

## Prohibido

Tocar el kernel o sus defaults. Relajar gates. Barrer parametros. Cruzar con
otras familias. Holdout. P&L. Reetiquetar a mano. Si algo bloquea: ABSTAIN
con la causa, no improvisar.
