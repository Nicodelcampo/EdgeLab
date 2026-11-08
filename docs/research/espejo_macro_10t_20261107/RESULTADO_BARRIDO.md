# Resultado: barrido ESPEJO-MACRO-10T sin lógica condicional (07/11/2026)

Estado: VIGENTE. Pre-registro: `PREREGISTRO_BARRIDO.md`. Embudo en R con costos canónicos y velas de 10 ticks; holdout sin tocar.

| Activo | Evaluables (de 23.328) | FDR | Réplica abr–sep (canasta de pistas, R/op) | Desenlace |
|---|---|---|---|---|
| NQ | 3.666 | 0 | **−0,18** (IC90 −0,29 a −0,07), 0 de 9 confirmadas | PISTAS_VIVAS (sin potencia; la canasta va **en contra**) |
| GC | 2.890 | 0 | −0,15 (IC90 −0,36 a +0,07), 0 de 3 | PISTAS_VIVAS (sin potencia) |
| YM | 504 | 0 | — | SIN_CANDIDATAS |
| ES | 0 | — | — | SIN_CANDIDATAS (el tope de 400 velas no entra en ES) |

## Lectura

- **La regla del espejo, tal como está, no muestra ventaja.** En NQ las mejores pistas del DESC pierden en la réplica, con el IC90 entero
  por debajo de cero (1.794 disparos en DESC).
- **ES e YM casi no tienen eventos** por la escala en velas. Lo cubre la variante en tiempo (`PREREGISTRO_TIEMPO.md`, en curso).
- **Siguiente:** la lógica condicional (qué picos tomó la ida, `../espejo_picos_20261107/PREREGISTRO_BORRADOR.md`) se mide como familia
  hija contra esta base.
