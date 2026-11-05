# Plan del paquete del 2026-10-31: qué se aprovecha, qué se descarta y qué quedó hecho

Estado: VIGENTE. Fecha: 2026-10-31. Pedido de Nico: «releé todo para determinar todo lo que conviene aprovechar del paquete, armá el
plan para implementar todo e implementalo; apruebo el pre-registro, lanzalo».
Fuente: `Paquete_EdgeLab_Mensajes_Extraccion_Auditoria_y_Corpus_20261031.zip` (65 archivos): la extracción de alto valor, la auditoría
externa del PR #162, el paper de Tori Trades, los documentos de @theagent_trades, @quantguild/@quantfinancetogo y las 999 estrategias
guardadas. El paquete no se versiona (corpus de terceros); este documento resume lo que se tomó.

## 1. Criterio
Se aprovecha lo que ataca los dos cuellos medidos: **potencia** (grillas de 10⁶ celdas que seleccionan ruido; 0 de ~480 pistas
confirmadas) y **pago** (10 de 12 reglas con acta con W/L 0,23–0,35). Todo entra como familia chica (cientos de celdas),
pre-registrada, por el embudo. Nada de lo que el paquete eligió mirando el OOS se usa como evidencia.

## 2. Qué se implementó (este PR)
| # | Del paquete | Qué quedó | Celdas/canal | Campañas |
|---|---|---|---|---|
| 1 | Salida por tiempo de parada τ (paper de Tori, ec. 1) | `areas_expansion.simular_cierre_linea` (opcional; sin línea es bit a bit el simulador de siempre) y `grilla_generica` con `lineas_salida` | — | — |
| 1a | La regla del paper medida tal cual, con θ̃ y t_NW (Prop. 3.5–3.6) | `tau_tendencia.py` (+ control FIJO_2R dentro de la familia) | 648 | TAU-NQ, TAU-ES, TAU-GC |
| 1b | τ como salida de las reglas con acta | `variante_tau.py` + `vtau_*.py` + `tools/variante_tau_actas.py`: mismas entradas, DESC, comparación pareada por sesión, BH q 0,10 | 4 celdas × 10 reglas | 10 kernels ANALIZAR_REGLA |
| 2 | Ventana Asia 01:00–01:15 ET + una reentrada (@theagent_trades) | `rango_ruptura.py` + `rango_asia0100.py` | 648 | RANGO0100-NQ/ES/GC |
| 3 | Pre-apertura 09:15–09:30 ET (S-tier) y zona muerta 11:30–13:00 | `rango_preapertura.py` | 648 | PREAPERTURA-NQ/ES/YM |
| 4 | ER de Kaufman con corte de sesión (el parche V2 tenía el bug del salto overnight) | `regimen_sesion.py` (`er_sesion`, `rv_relativa`, `minuto_ny`); ER es perilla de baja cardinalidad en las familias nuevas | — | — |
| 5 | Momentum de la última media hora (Gao et al. 2018; flujo 0DTE) | `eod_momentum.py` | 243 | EOD-ES/NQ/YM |
| 6 | KALMAN-FADE en más instrumentos | sin cambios de código; anexo de pre-registro | 216 | KALMAN-FADE-NQ (pre-registro del 30-oct), -ES, -GC |
| — | Prueba forward de ASIA-NQ (las 20 pistas) | ya pre-registrada (PR #171); arranca con las sesiones desde el 2026-11-02 | — | — |

Pre-registros: `SPEC_TAU_TENDENCIA.md`, `SPEC_RANGOS.md`, `SPEC_EOD_MOM.md`, `PREREGISTRO_KALMAN_ES_GC.md`,
`PREREGISTRO_VARIANTE_TAU_ACTAS.md` (esta carpeta). Cada campaña declara su linaje en `LINAJES.jsonl` (TAU hereda de TORI, RANGO0100
de ASIA-BOS, PREAPERTURA de OTR930 en NQ y ES) y el embudo la registra en el contador global antes de cada etapa con desenlaces.
Controles: `tests/research/test_salida_linea.py` y `tests/research/test_paquete_20261031.py` (causalidad, líneas sin futuro, paridad
lote/escalar, ruido sin efecto, efecto plantado, variante ORIGINAL idéntica al experimento base).

## 3. Qué NO se usa, y por qué
| Del paquete | Motivo |
|---|---|
| «ASIA-CORE-NQ» con las pistas p2/p3 (+$55/op, p 0,003) | Son las 2 mejores de 20 elegidas en el OOS: la misma selección que invalidó las canastas ortogonales. La prueba limpia es la de las 20 (PR #171). La ventana 01:00 y la reentrada sí se toman, como familia nueva. |
| «Filtro ER ≥ 0,25 multiplica ×2,7 la media de CVGAP» | Partido mirando el OOS, n = 15 y 21, y los `er` salen del parche con el bug de frontera de sesión. Queda como hipótesis: el ER correcto entra como perilla pre-registrada en las familias nuevas. |
| Tabla de PF/DD del «Iteración V2» | Datos sintéticos con el efecto programado (`auditar_equity_filtros_y_nt8.py`). |
| Streak sizing de @theagent_trades | Falacia del apostador sin autocorrelación negativa demostrada; acelera la ruina con trailing drawdown. |
| t de la regresión del precio en niveles | Diverge como √n bajo paseo aleatorio (Prop. 3.6 del paper). Se usa t_NW sobre retornos. |
| Grillas > 10⁵ celdas con 30–80 operaciones por celda | La causa medida de la falta de potencia. |

## 4. Lo que queda para otros (no se toca acá)
- **Canasta de 7**: su pre-registro está firmado; pesos por PCA/pods, tope dentro del kernel y freno diario por hora real de cierre
  cambiarían la prueba. Si se quieren, van en un pre-registro nuevo y no reabren este holdout. El tope en el kernel es el pendiente #1
  de Gonza (`PENDIENTES_PRIORIZADOS_20261031.md`).
- **Zonas HFT por cuantiles del activo** (HFTNQ satura en ES con 4.845 zonas por sesión y casi no da en YM): rama de Gonza del PR #159.
- **Kalman con R adaptativo y velocidad OU**: sólo si KALMAN-FADE sobrevive en alguna de las tres (espiral: se construye sobre lo vivo).
- **Barbell V1/V2 runner** y **régimen de 3 estados para las 12 reglas**: después de ver si τ mejora el pago (1b); hoy serían más
  perillas sobre entradas cuyo OOS ya se miró.

## 5. Conducción
Las campañas nuevas y KALMAN-FADE-NQ declaran `"conductor": "local"`: el Debian está en PAUSE y 53 commits atrás sin estos módulos.
Las conduce la sesión en la nube con `tools/embudo_correr.py --conductor local`, estado en `docs/research/paquete_20261031/embudo/`.
Al reconciliar SV1 (pendiente de Gonza) estas campañas se le pasan con su estado; nunca dos conductores a la vez.
