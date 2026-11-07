# Guía para el agente del Debian: estrategias por régimen y cómo aprender de las corridas (07/11/2026)

Estado: VIGENTE — directiva de Nico (07/11): «que el agente trabaje sobre el estado actual del repo, entienda la importancia de las
estrategias por régimen y tenga la capacidad de leer las corridas anteriores e inspirarse en ellas para diseñar las nuevas».

## 1. Por qué régimen

Nico busca estrategias que funcionen **ahora**, aunque no siempre. Un régimen con pocos meses pero **muchas operaciones y estabilidad entre
días** tiene potencia: la unidad de evidencia es el **día**, no la operación. Se rota la cartera entre estrategias de régimen y se agregan
familias nuevas al pool.

## 2. Lo que ya se midió (no repetirlo)

| Hallazgo | Dónde |
|---|---|
| Elegir por racha reciente NO le gana a la calidad estática (Δ −0,235 R/op, t −2,94); autocorrelación mensual −0,06 | `regimen_corto_20261106/RESULTADO_HREG1_WALKFORWARD_20261107.md` |
| P0_MICRO (1 mes IS → 1 mes OOS) rechazado contra nulos; sólo P4b pasó (23 ventanas) | `regimen_corto_20261106/RESULTADO_REGIMEN_ESTRUCTURAL_20261106.md` |
| Los «filtros de contexto» del atlas (ATR y volumen relativos, NY 9:30–12, stop ancho, imán) eran **fricción en R** | `programa_r_20261103/contexto_bruto_neto/RESULTADO_BRUTO_NETO.md` |
| Piso de riesgo frente a la fricción: refutado (u = 0,10 queda para validar desde noviembre) | `programa_r_20261103/RESULTADO_PISO_RIESGO_20261104.md` |
| Desvío por operación ≈ 0,66 R: 3 meses (~60 ops) detectan ~0,21 R; para +0,1 R hacen falta ~270 ops | `MENSAJES_AL_AGENTE_DEBIAN.md` (07/11) |
| Canasta estática PREAPERTURA-ES/NQ: recomputo idéntico; holdout +0,12 / +0,07 R/op, EN CURSO | `regimen_corto_20261106_recomputo/` |

## 3. Herramientas (usarlas; no reconstruirlas)

- **Cubos de operaciones** (etapa `CUBO`) y **motor de régimen offline** (`edgelab/research/regimen_offline.py`,
  `tools/cubos_regimen.py`). Toda regla de régimen se prueba en segundos, sin Kaggle, en walk-forward contra **tres controles**: azar,
  **calidad estática** y **nulo de signo por sesión**, que repite la selección y corrige la multiplicidad. Varias definiciones se
  corrigen juntas (`nulo_signo_multi`, `VARIANTES`).
- **Toda campaña nueva genera su cubo** (`python tools/cubos_regimen.py lanzar <CID>`): así entra al pool de rotación.
- **Embudo en velas de N ticks:** `"ticks_por_barra": N` en la campaña.
- **Marginales en bruto:** `marginales_globales_bruto` sale en cada corrida. Todo filtro común se juzga también en bruto; si sólo
  mejora en neto, es fricción.

## 4. Cómo leer corridas anteriores para inspirarse (sin engañarse)

- Leer `RESULTADO*.md`, `MEDIDO.md` de cada `embudo/<cid>/` y los `*MEDIDO_Y_NO_MEDIDO*.md`. El índice de conocimiento
  (`edgelab/autopilot/conocimiento.py`) ya los busca: «qué se midió, qué dio, por qué murió».
- **Inspirarse sí, reusar la muestra no.** Una idea sacada de mirar resultados es una HIPÓTESIS: se confirma con datos que no participaron
  (réplica nueva, papel desde noviembre o holdout bajo protocolo) y cuenta en el contador global y en el linaje (familia hija).
- **Patrones que se repiten:**
  - las pistas sin FDR rara vez replican;
  - la fricción en R explica muchos «efectos»;
  - stops chicos frente a la fricción hacen frágil una regla;
  - los detectores secuenciales suelen mirar el futuro (el certificado de causalidad lo atrapa: correrlo siempre).
- Diseñar familias con **muchos días independientes** (varios activos y sesiones) y stops grandes frente a la fricción. **No** bajar
  umbrales para operar más dentro del mismo día.

## 5. Ejecución

Todas las operaciones van en **futuros**: el CFD es sólo fuente de señal (decisión de Nico, 04/11). La paridad NT8 se mide con
`nt8/strategies/` (`EdgeLabCvgapESC`, `EdgeLabSignalReplay`).
