# FASE 2 — pre-registro. Carrera 1:1 con retroceso de entrada

**Escrito ANTES de correr nada.** Fecha 2026-09-03. Autorizado por Nico
(«probá niveles de retroceso para distintos niveles de SL y TP con ratio 1 a 1 y
10 tamaños distintos»), que se toma como el OK del STOP del proyecto.

Referente: `docs/NORTH_STAR.md` sha256
`d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.
Población: `hftimpulse_NQ0626_20260903.csv`, sha256 `856d235f…702b`, 6.043
señales, 29 sesiones, NQ 06-26 5t, pre-holdout.

## Por qué esta prueba y no otra

La Fase 1 mostró que las **excursiones máximas** a favor y en contra son
simétricas. Lo que dejó abierto es el **orden**: aunque los máximos empaten, lo
favorable podría llegar **antes**. Con SL = TP la prueba es directamente esa
carrera, sin que la elección de ratio meta un grado de libertad.

Es el diseño correcto para la pregunta que quedaba viva.

## Grilla congelada

| eje | valores | n |
|---|---|---:|
| retroceso de entrada (ticks) | 0, 2, 4, 6, 8, 12, 16 | 7 |
| SL = TP (ticks) | 4, 6, 8, 12, 16, 20, 24, 32, 40, 48 | 10 |
| **celdas** | | **70** |

## Reglas, congeladas

- **Referencia**: cierre de la barra que dispara la señal.
- **Entrada con retroceso R**: se entra si el precio retrocede R ticks contra la
  señal dentro de **60 barras**. Si no retrocede, **no hay trade** (se cuenta como
  no-fill, no como pérdida cero). Con R = 0 se entra en la barra siguiente.
- **Salida**: primer toque de SL o TP. Si no se toca ninguno en **600 barras** o
  llega el fin de sesión, se sale a mercado ahí.
- **Sin cruce de sesión.** Ningún trade sobrevive a la frontera.
- **Ambigüedad SL/TP en la misma barra**: se reportan las **dos** políticas —
  pesimista (asume SL primero) y optimista (TP primero). Con SL = 4 ticks la
  ambigüedad no es despreciable, así que las dos acotan el resultado en vez de
  esconderlo.

## Costos

Round-turn declarado: **1,5 ticks** (spread ~1 tick + comisión ~0,5 tick para NQ).
Se publica sensibilidad a 1,0 / 1,5 / 2,0 / 3,0 ticks, y el **costo de equilibrio**
de cada celda. Los costos son de NQ y no se transportan a ningún otro instrumento.

Nota aritmética que ya se puede anticipar: con SL = TP = S y costo c, el
punto de equilibrio exige una tasa de acierto de `(S + c) / (2S)`. Con S = 4 y
c = 1,5 eso es **68,75 %**. Las celdas chicas están muertas antes de correr, y el
resultado tiene que mostrarlo.

## Inferencia

- **Métrica primaria**: expectativa neta por trade, en ticks.
- **IC 95 % bootstrap clusterizado por sesión**, 4.000 remuestreos. Justificado:
  la Fase 0 midió índice de dispersión 45,9 entre sesiones.
- **Multiplicidad**: 70 celdas. Se reporta el p-valor mínimo con corrección de
  Bonferroni y, por separado, cuántas celdas se esperaría ver «positivas» por azar.
- **Se publica el landscape COMPLETO**, las 70 celdas. Nunca la mejor.

## Criterio de decisión, fijado ahora

- **PROMOVIBLE** si existe una **región contigua** de celdas con IC inferior > 0
  neto de 1,5 ticks. Una celda aislada positiva rodeada de negativas **no cuenta**:
  eso es ruido con forma de hallazgo.
- **NO PROMOVIBLE** si no hay región contigua, o si la única señal aparece con
  costos irrealmente bajos.
- **Expectativa previa declarada**: baja. La Fase 1 encontró el canal direccional
  ligeramente **negativo** (−0,035 desvíos, consistente en 10–300 barras). Este
  test se corre porque mide algo distinto —el orden, no la magnitud— no porque el
  resultado anterior invite a esperar algo.

## Cómo podría refutarse el resultado, en las dos direcciones

- Si sale positivo: hay que verificar que no venga de las celdas donde la
  ambigüedad SL/TP manda (las chicas), y que sobreviva a la política pesimista.
- Si sale negativo: con 70 celdas y este N el MDE por celda queda declarado en el
  informe; un nulo sin MDE no distingue ausencia de efecto de falta de potencia.

## Lo que NO se toca

Holdout intacto. No se prueban EMA ni filtro horario: quedan fuera de esta fase y
de su presupuesto de multiplicidad.
