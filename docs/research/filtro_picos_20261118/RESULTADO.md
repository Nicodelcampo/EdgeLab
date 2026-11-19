# FILTRO-PICOS: esperar picos o un barrido antes de entrar, como capa sobre gatillos de otras reglas (resultado, 2026-11-18)

Estado: RESULTADO — **REFUTADA como capa de edge.** La capa mejora a una base que pierde, pero:
- la mejora sale de esperar o cancelar, no de los picos (no supera al placebo en la réplica);
- ninguna configuración tiene R positivo, ni bruto ni neto.

- **Idea y parámetros:** Nico. **Pre-registro:** `PREREGISTRO.md`.
- **Datos:** `CALIBRACION.json` (90/110 celdas calibran contra ticks), `DESC.json`, `REP.json`, `OPS_DESC_REP.csv.gz`, `EVENTOS.csv.gz`.
- **Herramientas:** `tools/a5_campana.py` y `tools/filtro_picos_a5.py`.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapas EF3 (DESC) y EF4 (REP).
- **Holdout A5:** sin abrir. La compuerta económica no pasa.

## DESC (80 pruebas, BH q 0,10, NQ/ES/YM M1 2006–2022)
**Control de artefacto (AZAR, gatillos al azar):** ninguna configuración le gana a la entrada inmediata (p ≥ 0,20). La capa no crea
ventaja de la nada; las comparaciones son interpretables.

| Base | Contra entrada inmediata (INM) | Contra placebo de la misma espera | R bruto por gatillo: base → con la capa |
|---|---|---|---|
| **LUX** (fade de impulso) | peor en las 8 (−0,015 a −0,028) | peor o igual | +0,034 → +0,006 a +0,019 |
| **IBV0** (fade del borde del IB, Madonna) | mejor en las 8 (+0,09 a +0,16, BH) | sólo B15 mejor (+0,08 a +0,09, BH) | −0,135 → −0,043 a +0,021 |
| **IBV3** (aceptación → continuación) | peor en las 8 | peor | +0,045 → ≈ 0 |
| **ESC** (escalera) | mejor en 6 (+0,01 a +0,02, BH) | igual o peor | −0,02 → −0,01 |

Nominadas: 15. Son 13 contra la entrada inmediata (IBV0 y ESC) y 2 contra el placebo (IBV0 B15n1 y B15n2).

## REP (una vez, LORD++ nivel 0,011)
- **Confirman 8, todas contra la entrada inmediata:** IBV0 A15n1, A15n2, A60n1, A60n2, B15n2, B60n1, B60n2 y ESC A15n1. Diferencias
  de +0,02 (ESC) a +0,15 R (IBV0).
- **No confirman las dos contra el placebo:** IBV0 B15n1 (+0,03, p 0,26) y B15n2 (+0,05, p 0,15).
- **Valor absoluto de lo confirmado:** R bruto por gatillo de −0,07 a −0,04 en IBV0 y ≈ −0,01 en ESC. Neto por gatillo de −0,12 a
  −0,37. Las operaciones que sí entran pierden −0,44 a −1,43 R netas.

## Lectura
- **Lo confirmado es mecánico, no de picos.** Esperar 15–60 velas y cancelar si el precio va al objetivo o se aleja 1·D deja afuera
  parte de los gatillos malos de una base que pierde (el fade del IB). El placebo, que espera sin pedir picos, hace casi lo mismo.
- **Sobre bases que ganan en bruto (LUX, IBV3), esperar siempre empeora:** se pierde el movimiento inmediato. Coincide con
  F-AJUSTE-FINO-NO-PAGA (SOM: entrar 25 minutos más tarde mata el efecto).
- **Económico:** ninguna combinación base × capa tiene R neto positivo. El filtro sólo pierde menos que la base.
- **Cláusulas del pre-registro que se cumplen** (§5):
  - «las que superan a INM no superan al placebo: lo que ayuda es esperar (o cancelar), no los picos»;
  - «el neto no acompaña».
- **Alcance de la muerte:** esta capa (picos blandos de 1 vela, vuelta 0,25·D, cancelación a 1·D, espera 15/60), sobre estas cinco
  bases, en NQ/ES/YM M1 2006–2022. No dice nada de otras capas de entrada sobre bases con ventaja neta, que hoy no existen en el
  dominio M1 de índices.

## Integridad
- **Calibración rehecha con código vigente** (K41). Las tablas v0 están en `docs/research/tablas/FILTRO-PICOS/tablas_v0/` y
  `calibracion_m1_v0/`.
- **Falla del análisis y su causa:** `a5_campana.correr` descartaba las columnas `trig`, `base` y `conf` de OPS. Se arregló con la
  clave `conservar` de CAMPANA.json. Esta corrida las recuperó de EVENTOS por posición, con verificación fila por fila de `k`, `ses`,
  `lado`, `inst` y `bloque` (`filtro_picos_a5._ops`).
- **Holdout:** en HOLDOUT sólo se contaron eventos (`CORRIDA.json`); no se calculó ningún desenlace.
