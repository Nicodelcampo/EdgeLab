# Relanzamiento causal de 11 campañas cerradas (2026-11-02)

Estado: VIGENTE. Pedido de Nico: «dale, lanzá las 11». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF2 → embudo completo.

## Por qué
Las 11 terminaron en FIN con código que después se corrigió:
- la familia U1 usaba `areas_expansion.disparos` con mirada al futuro;
- CVGAP tenía dos problemas de borde.

Ver `HALLAZGO_LOOKAHEAD_DISPAROS_U1_20261102.md`. Según `GUIA_GRILLA_MASIVA.md`, una corrida lanzada con código que después se
corrigió no se mira: se documenta como descartada y se relanza.

## Qué se relanza
| Original (FIN, descartada) | Nueva campaña |
|---|---|
| U1-6B-FUT-GRILLA, U1-6B-GRILLA, U1-6E-CONFIRMA-GBP, U1-6E-FUT-GRILLA, U1-6E-GRILLA | mismo cid + `-C` |
| U1-RACIMOS-GRILLA-YM, U1-ZONAS-AVCL-ES, U1-ZONAS-BT2-YM, U1-ZONAS-GRILLA-YM | mismo cid + `-C` |
| CVGAP-ES, CVGAP-CFD-ES | mismo cid + `-C` |

- **Igual que la original:** módulo, grilla, períodos, justificación económica, condición de refutación y familia.
- **Distinto:** el código, ahora causal y certificado; el conductor, ahora `local` (esta sesión), con estado en `embudo/` de esta carpeta.
- **Multiplicidad.** Cada DESC vuelve a registrar sus celdas en el contador global: las pruebas descartadas siguen contadas. Los pasos
  de LORD++ salen del libro de cada familia. Es lo conservador.
- **Lo que no cambia.** Las réplicas que estas familias ya miraron siguen consumidas. Si una pista llega a OOS en una ventana ya mirada,
  el embudo lo trata según su regla de réplica.
