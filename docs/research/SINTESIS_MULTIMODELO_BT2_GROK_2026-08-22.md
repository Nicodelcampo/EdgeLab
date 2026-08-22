# Sintesis multimodelo BigTrap2 — Grok 4.6 — 2026-08-22

**Rol**: auditor (cierre de la revision). **Modelo**: Grok 4.6 (selector del chat de Notion).
**Pesa**: secciones 1–3 de `REVISION_MULTIMODELO_BT2_OPUS5.md` @ `e96652f`.
**No edita** esas secciones. Este archivo **es** la seccion 4.

**Trazabilidad.** Identidad = selector; no verificable desde adentro. La pasada Grok del
encabezado del acta quedo en chat, sin seccion: **no cuenta** como tercera voz. Las tres que
se pesan son Opus 5, GPT y Kimi K3. Visibilidad de las tres + `PARIDAD_BT2_ABSORPTION_2026-08-22.md`.
No es ciega.

**Headline confirmado por Nico**, 2026-08-22 20:55 ART: `ScoreMode = AbsMagnitude`.

## Tabla

| pregunta | Opus 5 | GPT | Kimi K3 | acuerdo |
|---|---|---|---|---|
| Q1 evento real | conteo absoluto: "3 contratos y nada abajo" | lo mismo + lado/mecha/diagonal; 49,7 % es densidad, no cubetas unicas | viejo = degeneracion del ratio; nuevo = TI/desplazamiento, no OFI | **compatible, no bloquea** |
| Q2 evidencia | 49,7 %, vol p50=4, 1 fila; S1 > K0 | 0,497 TRAP/cubeta; vol>=30 empeora medias; F0~S1 | mismos JSON + 647/628/18 del export v1.1.1 | **si, con correccion de lenguaje** |
| Q3 fortaleza | infraestructura 1-tick + fill sin look-ahead | misma + observabilidad del export | misma + paridad medida hoy | **si** |
| Q4 debilidad | el evento no esta definido | artefacto del floor + TI≠OFI + AbsDirectional ≠ absorcion | suscribe ambos + kernel Python no reproduce al .cs | **si** |
| Q5 brecha | 0,72 de 2,5 t (~3,4x) | +0,7226 t; factor 3,46x; S1 no se resta | mismos numeros; estimands separados | **si** |
| Q6 cambio | flujo/desplazamiento, percentil causal; implemento AbsDirectional | cambiar si; no aprobar v1.0; separar los dos modos; TI no OFI | cambiar si; headline AbsMagnitude; AbsDirectional = 2º trial | **si en el verbo; el modo se resuelve aca** |
| Q7 prueba | 3 puertas, discovery 24–30 jun, >=10 sesiones | no ejecutable; Puerta 0; S1 recomputado; headline unico | adopta GPT + prediccion Puerta 1: no pasa (0,95–1,15) | **si en la forma; el piso de 10 se enmienda** |

## Regla de cierre

Si los tres coinciden en Q4 y Q6 → se implementa y se mide. Si difieren en Q1 → primero la definicion.

**Q4: coinciden.** El evento viejo es un artefacto de `max(opuesto,1)`.

**Q6: coinciden en el verbo.** Cambiar la definicion. El desacuerdo es la etiqueta del score,
no el cambio. Opus implemento `AbsDirectional` y lo llamo residuo OFI escala-libre. GPT y Kimi
rechazan esa etiqueta: es proxy de inversa de impacto sobre trade imbalance, y `AbsDirectional`
mide agresion fallida.

**Q1: no bloquea.** Opus describe el caso degenerado. GPT y Kimi agregan lado, mecha, diagonal,
y que 11.964/24.093 es densidad. Precision del mismo objeto. La fraccion de cubetas unicas con
TRAP sigue **no medida**.

**Cierre: se implementa y se mide.** Headline y protocolo en
`ENMIENDA_PROTOCOLO_BT2_ABSORPTION_2026-08-22.md`. Nico confirmo `AbsMagnitude` el 2026-08-22
20:55 ART.

## Headline: `ScoreMode = AbsMagnitude`

1. Fidelidad al nombre. Absorcion = flujo alto con desplazamiento **absoluto** bajo.
   `AbsMagnitude` penaliza `|dPx|`. `AbsDirectional` no: flujo+ y `dPx=-10` tiene denom=1,
   igual que `dPx=0`. Eso es otra hipotesis (agresion fallida).
2. Una puerta, una cadena. Elegir el modo despues de ver MFE es dos trials. El export ya trae
   `signed_flow` y `d_ticks`: la otra cadena es trial 2, no rescate.
3. Falsacion limpia. "El decil de baja respuesta absoluta no rompe 38/36" se entiende solo.

```
ScoreMode            = AbsMagnitude
TapeWindowTicks      = 25
AbsorptionPct        = 90
AbsorptionLookback   = 500
MinHistoryBuckets    = 200
MinStackedRows       = 2
MinTrapFrac          = 0.20
RequireFlowSideMatch = true
```

`AbsDirectional` = trial 2, mismo export, despues de cerrar o fallar el headline.

## Lo que no se decide aca

No reabre H-GC-BT2-1. No corona +3,70 t de vol>=30 (n=122, holdout gastado). No declara
`EXACT` del visor: el harness midio la semantica; el kernel versionado todavia no la implementa.
No agrega una cuarta prediccion de Puerta 1. Viaja la de Kimi: no pasa, ratio 0,95–1,15.

## Orden

1. ~~Nico confirma o veta `AbsMagnitude`.~~ **Hecho**, 2026-08-22 20:55 ART.
2. Protocolo enmendado (ya escrito).
3. Kernel con cortes de sesion + artefacto de paridad (local).
4. NT8 sobre GC 08-26 discovery.
5. Censos target-free.
6. Puertas 1 → 2 → 3.
