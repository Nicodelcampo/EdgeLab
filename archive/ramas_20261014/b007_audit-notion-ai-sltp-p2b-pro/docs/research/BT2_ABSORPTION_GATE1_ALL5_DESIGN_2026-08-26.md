# Gate 1 GC all5 — diseño de replicación expandida post-outcome

Fecha: 2026-08-26

## Estado y alcance

Esta corrida **no reescribe** la Gate 1 clean76 ni restaura su firewall confirmatorio. Los outcomes ya fueron abiertos. El objetivo es ejecutar una replicación expandida, mecánica y auditable con los cinco Parquets canónicos entregados.

Etiquetas obligatorias:

- `CAMPAIGN_OUTCOMES_OPENED=true`
- `confirmatory_eligible=false`
- `promotion_eligible=false`
- `EDGE_DECLARED=false`
- `POST_OUTCOME_EXPANDED_REPLICATION`

## Nueva muestra

La muestra es una cadena no solapada de 234 fechas CME:

| Contrato | Ventana asignada | Sesiones |
|---|---|---:|
| GC 12-25 | 2025-08-04 a 2025-11-25 | 82 |
| GC 02-26 | 2025-11-26 a 2026-01-28 | 44 |
| GC 04-26 | 2026-01-29 a 2026-03-27 | 42 |
| GC 06-26 | 2026-03-30 a 2026-05-27 | 42 |
| GC 08-26 | 2026-05-28 a 2026-06-30 | 24 |
| **Total** | 2025-08-04 a 2026-06-30 | **234** |

Regla de admisión:

1. Un solo contrato por fecha CME.
2. Sólo etiquetas de lunes a viernes.
3. Se preservan cierres reducidos de feriados: son sesiones reales, no truncamientos silenciosos.
4. Se excluyen las etiquetas técnicas de fin de semana con 1–6 filas.
5. Se excluye `GC 12-25|20250801`: borde izquierdo parcial con 3.515 filas y aproximadamente una hora de tape.

### Censura izquierda

El segmento GC 12-25 queda anclado a disponibilidad. No existe GC 08-25 para verificar el crossover de volumen de su borde inicial. Por eso la muestra se declara `left_censored=true`; no se representa como una reconstrucción completa de toda la cadena front-month.

## Arreglo estructural del runner

El runner original cargaba contratos completos de varios meses. GC 12-25 supera 16 millones de filas y esa estrategia no es segura en memoria.

El runner all5 procesa cada sesión con una ventana causal y acotada:

- sesión seleccionada;
- sesión válida inmediatamente anterior como warm-up;
- horizonte duro dentro de la fecha CME;
- fill en el primer tick canónico estrictamente posterior a la señal.

El warm-up reconstruye los 500 buckets de 25 ticks usados por el percentil causal de absorción. En el primer caso de GC 12-25 usa todo el prehistórico disponible (`20250801`). Ningún outcome futuro entra al cálculo de señal.

## Estimando e interpretación

Se conserva:

```text
d_hat_s = median_i(MFE_i_ticks) - median_i(MAE_i_ticks)
```

La inferencia mantiene peso igual por sesión y Wild Cluster Bootstrap Webb de seis puntos.

`d_hat` es un contraste de excursiones de trayectoria:

- no es P&L realizado;
- no es neto de comisiones;
- no incluye slippage;
- no autoriza decir “ticks netos”;
- un contraste frente a `N_RAND` sólo vale frente a ese null emparejado;
- un intervalo secundario que contiene cero falla el control al 95%; no se redondea para declararlo positivo.

Aun con N mayor a 133, la precisión recuperada por tamaño muestral no recupera la elegibilidad confirmatoria perdida al abrir outcomes.

## Archivos de contrato

- `specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json`
- `specs/bt2_absorption_gate1_all5_input_registry_2026-08-26.json`
- `specs/bt2_absorption_gate1_all5_post_outcome_replication_2026-08-26.json`
- `docs/research/BT2_ABSORPTION_GATE1_ALL5_ADMISSION_AUDIT_2026-08-26.json`
- `edgelab/research/bt2_gate1_all5.py`

La corrida produce `gate1_all5_result.json` con resultados por sesión, conteos de eventos, exclusiones, hashes y el contrato de interpretación.
