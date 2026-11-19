# Reporte de Claude para auditoría de Antigravity (2026-11-18 → 2026-11-19)

Estado: VIGENTE — pedido de auditoría; se supera cuando Antigravity deje su respuesta (archivo hermano `AUDITORIA_ANTIGRAVITY_…md`).
- **Pedido de Nico:** «¿Podés reportar tu trabajo para que Antigravity lo audite?».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Rama:** `claude/vibrant-clarke-s9z6e2`. Commits de Claude desde `8350f671`: `git log --oneline 8350f671..HEAD --author=Claude`.
- **Regla para el auditor:** fuente antes que recuerdo. Cada afirmación de abajo cita su artefacto; reproducir antes de aceptar. Si algo
  no reproduce, es hallazgo. No abrir REP ni holdout de ninguna familia para auditar.

## 1. Qué se hizo, con su veredicto y artefacto
| # | Campaña / trabajo | Veredicto | Artefacto | Pruebas contadas |
|---|---|---|---|---|
| 1 | OPTION-ALPHA (OA1–OA8, módulo de Gemini) | REFUTADA en DESC: 0/13 en BH, neto negativo en las 8 | `option_alpha_20261118/RESULTADO.md` | 13 |
| 2 | T-REGIMEN (P-97): ¿T de FundedSync sobreajustada desde 2020? | REGIMEN_ROBUSTO: 81/81 variantes positivas desde 2021-02-10, PBO 0,17, 0/81 antes | `t_regimen_20261118/RESULTADO.md`, `PROPUESTA.md`, `VIGILANCIA.md` | 1 (FUNDEDSYNC) |
| 3 | ROBOQUANT (RQ1–RQ8, módulo de Gemini) | 5 nominadas por bruto (RQ1, RQ2, RQ5, RQ6, RQ2−RQ2N), neto negativo; REP bloqueado por K49 (potencia 0,04–0,07) | `roboquant_20261118/RESULTADO.md` | 15 |
| 4 | FRICCION-RQ: curva bruto–stop de RQ2/RQ5/RQ6 | RQ5 TIMING; RQ6 y RQ2 MEJORA_SIN_NETO; bruto en puntos constante; contrato fijo positivo en ES/NQ (exploratorio) | `friccion_rq_20261119/RESULTADO.md` | 18 (ROBOQUANT_A5) |
| 5 | Spread por hora (target-free) | Canónico correcto; la hora ahorra ≈ 4 % en NQ | `spread_hora_20261119/RESULTADO.md` | 0 |
| 6 | EXTERNAS_A5 (las 114 variantes del catálogo c8d0e912) | EN CURSO: fase 0 de fricción sin retornos (NQ 112/114, ES 88, YM 82, GC 0) | `externas_a5_20261118/PREREGISTRO.md` | 114 |
| 7 | Guardas nuevas | K50 (registros .jsonl parsean), K51 (`exigir_contada`) | `tests/test_gobernanza_20261118.py`, `ERRORES_…` §E6, `LEER_ANTES_…` §6 | — |

Además, sobre trabajo de Gemini: reparé `LINAJES.jsonl` (línea vacía y dos objetos pegados de `d07375b4`), enmendé ANTES de correr los
pre-registros de OPTION-ALPHA y ROBOQUANT (potencia en días K49, filtros macro fuera de la corrida, linaje hija de ORB_A5) y verifiqué que
`cargar_ctx_m1nt8_rapido` reproduce `a5_campana._ctx` (o/h/l/c/t/ses/tpx/tstart idénticos en NQ ene–feb 2018; sólo falta el perfil de
volumen).

## 2. Qué auditar (lista concreta, de mayor a menor riesgo)
1. **T-REGIMEN es la conclusión con más consecuencias** (T-NQ quedaría como candidata a tamaño micro).
   - ¿El riesgo inicial de cada variante (`clip(rango de los primeros orb_bars min × 1,25, 2, 100)`, `tools/t_regimen.py`) es el que usa
     el motor de T para su stop con `orb_bars ≠ 15`? Si el stop real no escala así, el R de las variantes 10/20 está mal medido.
   - ¿El quiebre 2021-02-10 (sup-F, p 0,003 contra permutación de meses, `PROPUESTA.md` §2) se eligió sin mirar la grilla? Se calculó con la
     fábrica antes de la grilla; la grilla usa esa fecha fija.
   - ¿`g2.pbo_cscv(s=16)` sobre 68 meses × 81 variantes con R sumado por mes es la métrica correcta? (La PBO baja puede deberse a que todas
     las variantes están muy correlacionadas: es una meseta, pero también es poca diversidad real.)
   - Reproducir: `python tools/t_regimen.py decidir` (usa `GRILLA_OPS.csv.gz` versionado).
2. **FRICCION-RQ §3 (contrato fijo)** es exploratorio y cambió el estimando después de mirar. Revisar que el texto no lo venda como
   resultado, y que el siguiente pre-registro (RQ5+RQ6 en ES+NQ con tamaño fijo) declare el sesgo de haber elegido ES+NQ al ver que YM no
   paga. Los puntos de NQ pesan más los años recientes (precio más alto): ¿hace falta normalizar por precio o ATR?
3. **ROBOQUANT:** la nominación usa calibración M1↔ticks (13/15). Verificar `CALIBRACION.json` y que RQ1 (salida a 8 minutos) sea creíble
   en M1 (el motor trabaja con pseudo-ticks de la vela; K40).
4. **Lanzamiento descartado de FRICCION-RQ:** arrancó antes del conteo, procesó ES y se mató sin escribir resultados (`PREREGISTRO.md` §0).
   Confirmar que no hay `OPS.csv.gz` previo al commit `e8d23a57` en el historial.
5. **VIGILANCIA de T:** cotas del e-proceso [−2, +3,5] declaradas mirando el rango observado [−1,34, +2,99]; ¿son estructurales (stop a 1 R,
   objetivo `baseline_target_r = 3,0`) o deberían incluir hueco de apertura mayor?
6. **EXTERNAS fase 0:** la regla (mediana fricción/riesgo ≤ 0,08 R y ≥ 30 sesiones DESC) se fijó antes; una prueba de tiempo en NQ 2010 ya
   mostró que sólo Dual Thrust pasaba (declarado en el pre-registro). La auditoría de Gemini de X036–X039 con desenlaces en DESC es
   verificación cruzada, no decisión (`COORDINACION_GEMINI.md`).

## 3. Riesgos y debilidades que Claude ya ve
- **Reinicios del contenedor:** cortaron 4 veces procesos largos; la fase 0 y la grilla de T son reanudables por variante (`data/…`). La
  corrida de ROBOQUANT murió una vez por memoria (OOM con la fase 0 en paralelo) y se relanzó completa antes de mirar nada.
- **Sin prueba 2 de T** (datos que el vendedor no vio): falta la fecha de la versión de FundedSync (Nico).
- **Mecanismo de gamma para T** no se volvió a probar (ya medido en canasta, NO_REPETIR).

## 4. Qué falta y en qué orden lo haría
1. Terminar EXTERNAS_A5 (fase 0 → DESC de las que pasen → cruce con la auditoría de Dual Thrust de Gemini).
2. Pre-registrar el tamaño fijo / ∝1/√riesgo como palanca transversal sobre las señales con bruto estable y sin neto (RQ5, RQ6, SOM,
   Franklin), con plan de potencia K49 para REP + holdout ANTES de abrir.
3. T-NQ a candidata micro cuando llegue la fecha de la versión (prueba 2) con la vigilancia de `VIGILANCIA.md`.
4. El catálogo extendido de Option Alpha (#21–#80) no tiene módulo ni corrida: no correrlo (OPTION-ALPHA quedó NO_REPETIR en futuros:
   la ventaja es prima de opciones).
