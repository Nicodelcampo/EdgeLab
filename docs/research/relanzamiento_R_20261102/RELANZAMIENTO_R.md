# Relanzamiento de todas las campañas con el P&L medido en R (2026-11-02)

Estado: VIGENTE. Decisión de Nico: «sí, relanza todo». Motivo y alcance: `docs/research/MEDIR_EN_R_20261102.md`. Referente:
`docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Qué se relanza
- **68 campañas, con cid `<original>-R`** (`CAMPANAS.json`). Son todas las del embudo con estado; si existe la versión causal `-C`, se
  relanza ésa.
- **Igual que el original:** módulo, grilla, períodos, justificación, refutación y familia, con código causal.
- **Distinto:** `"estadistico": "R"`. Todas las etapas (DESC, pistas, réplica, OOS, topes, acta y holdout) miden el P&L neto en R.

## Multiplicidad y holdout
- Cada DESC vuelve a registrar sus celdas en el contador global. Los pasos de LORD++ salen del libro de cada familia: es lo conservador.
- Las familias que ya abrieron el holdout (las 12 nominadas y las 3 forzadas) tienen su apertura vigente desde 20261001. Si una versión
  `-R` llega a ACTA, el embudo aplica sus reglas de reuso de ventana. No hay apertura nueva sin acta registrada antes.
- Los resultados en puntos no se borran: quedan como lo medido con el estimando anterior.

## Conducción
4 conductores locales (`tools/embudo_correr.py`) desde esta sesión, con estado en `embudo/`. El chequeo diario los retoma si el contenedor
se reinicia.

## Resultado (2026-11-03 01:30 UTC): 68 de 68 en FIN, ninguna candidata llega al holdout en R
| Estado | n |
|---|---|
| PISTAS_VIVAS (sin potencia para decidir) | 33 |
| SIN_CANDIDATAS | 23 |
| INTEGRIDAD_FALLA | 4 |
| SIN_REGLA_OPERABLE | 2 |
| BLOQUEADA | 6 |

- **Nominadas por el FDR en R que no pasaron** (6 familias):
  - **INTEGRIDAD_FALLA** (ninguna candidata pasa placebo o latencia): U1-ES, U1-ORO, U1-YM y U1-ZONAS-BT2-NQ.
  - **SIN_REGLA_OPERABLE** (pasaron integridad, pero ningún tope conserva el resultado en las dos mitades): U1-ZONAS-ES y U1-ZONAS-NQ.
    U1-ZONAS-ES tuvo además OOS −0,11R, no concluyente (potencia 0,15).
- **Bloqueadas:**
  - 4 por kernels de Kaggle que no aparecieron (404 tres veces): PREAPERTURA-NQ, PRERANGE-BASE-YM, PRERANGE-ZONAS-NQ y RANGO0100-ES.
    Se relanzan: el estado bloqueado queda archivado.
  - CVGAP-CFD-NQ-R: su familia ya usó su única apertura del holdout. Es correcto, por diseño.
  - U1-6E-CONFIRMA-GBP-C-R: preflight de ruido con 2 nominadas por el FDR. Causa raíz pendiente; la familia FX ya estaba en contra con
    potencia.

**Lectura.** Medido en R, el embudo encontró nominaciones que en puntos no aparecían, pero ninguna sobrevivió la integridad o los topes.
No hay edge confirmado en R en estas 68 familias, y eso es coherente con el holdout de octubre (≈ 0R).
