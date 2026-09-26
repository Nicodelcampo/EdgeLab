# Justificación de población — generalizar a ES (F3)

**Fecha** 2026-08-10 · **NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Regla que exige este documento** — `CLAUDE.md`: «Ninguna población se congela
sin enumerar antes, por escrito, el espacio de eventos y estados del que se la
extrae, con su justificación y su condición de refutación.»

---

## 1. El espacio de instrumentos disponible — enumerado completo

`data/nt8/` contiene material crudo o ingerido para: **6E** (único en
producción hasta hoy), **YM, ES, NQ** (parquet canónico + catálogo del bridge
habilitados hoy), y **6B, 6J, GC, MES, MGC, MNQ, BTC, MBT, ZB** (parquet
existe para varios; catálogo del bridge no los conoce; sin ingesta verificada
para el resto).

## 2. Por qué ES ahora, y no los otros

- **YM ya se descartó como generalización de HOY**: se ingirió y habilitó
  (`YM_INGESTA_Y_HABILITACION_2026-08-10.md`) pero no se corrió ningún análisis
  target-free sobre él todavía — sirve para una tanda futura, no compite con ES
  por el mismo motivo (tiempo de esta tanda).
- **ES es el más líquido y el más distinto de 6E** de los tres habilitados hoy:
  6E es FX, ES es índice de renta variable — la generalización más informativa
  posible con lo que hay listo, porque si el hallazgo de F1.1 sobrevive a un
  cambio de clase de activo completo, sobrevive a mucho más que a ruido de
  instrumento.
- **NQ queda para una corrida posterior**: mismo motivo que YM, prioridad de
  tiempo, no descarte. Ambos con parquet y catálogo ya listos — el costo de
  correrlos después es sólo cómputo, no plomería nueva.
- Los instrumentos sin ingerir (**6B, 6J, GC, MES, MGC, MNQ, BTC, MBT, ZB**)
  quedan fuera de esta tanda explícitamente — no evaluados, no descartados.

## 3. La población — calendario, no reelegido, reutilizado con verificación

**No se redefine qué es un "día de estudio".** Se reutiliza el mismo calendario
de 201 sesiones que `dias_research()` ya validó para 6E (mismo filtro de
holdout, mismos tipos de día `COMPLETO`/`CIERRE_SEMANAL`). Lo que cambia es
**a qué archivo de contrato mapea cada fecha** — de `6E_*.parquet` a
`ES_*.parquet` — y ese mapeo se construye por **cobertura real verificada**
(rango de timestamps del parquet ES, no una asunción de que los calendarios de
6E y ES coinciden). Si una fecha del calendario 6E no tiene cobertura ES, el
módulo **falla fuerte** en vez de омitir la fecha en silencio — la misma
disciplina de no angostamiento que rige los manifiestos de datos.

**Por qué reutilizar el calendario de 6E es correcto y no un atajo**: ES y 6E
cotizan en el mismo complejo CME, con el mismo calendario de feriados de EE.UU.
No es una asunción sin verificar — la verificación es precisamente el paso 3
de arriba (falla si no cubre).

## 4. Qué se mide — mismo protocolo que 6E, sin adaptar la pregunta al dato

**F0.2 (censo)** y **F1.1 (nulo local, sólo nulo-B — el corregido y de
referencia)**, con la misma semilla (`20260810`), la misma ventana local
(±180 barras), el mismo `bar_spec` (`time:1`) y los mismos parámetros de
BigTrap2 por defecto. Ningún grado de libertad nuevo: es una réplica, no un
ajuste.

## 5. Condición de refutación — declarada ANTES de correr

**Si el hallazgo de F1.1 no generaliza** —si en ES la tasa de toque de las
zonas reales no se distingue de la del nulo local, o la brecha es
sustancialmente menor que en 6E (arbitrariamente: menos de la mitad, <23 pp
en vez de ~47)— **el hallazgo queda acotado a FX, no a "BigTrap2"**, y hay que
decirlo así en el registro, no re-explicarlo a posteriori. No hay ajuste de
parámetros que rescate una réplica fallida: una réplica que falla es
información, no un error a corregir.

## 6. Qué NO cubre esta justificación

No cubre NQ (justificación futura si se decide correrlo). No cubre extender
`dias_research()` en sí —la calendario canónica de 6E— a otros instrumentos: el
mapeo fecha→archivo de ES vive en un módulo nuevo y autocontenido, no modifica
el archivo de universo de 6E. No cubre ningún test de outcomes — sigue bajo el
mismo STOP que todo lo demás.

---

## Aporte al referente

Dejar esta decisión escrita, con su condición de refutación declarada antes
del resultado, es la corrección directa al defecto que costó el corpus de H1:
una población nunca se elige por default.
