# Corridas en R relanzadas por la cola t del tamiz FDR (03/11/2026)

Estado: DESCARTADAS — superadas por el relanzamiento con la cola t (decisión de Nico, `docs/DECISIONES_20261103_COLA_T_FDR.md`).

**Por qué sólo éstas.** La cola t da, celda por celda, un p **mayor o igual** que la cola normal (`tests/research/test_criba_maxt.py`).
Con p más grandes, los q de BH/Storey no bajan (π0 tampoco baja), así que el conjunto nominado con la cola t está **contenido** en el
de la cola normal. Una campaña sin nominadas, o que murió en INTEGRIDAD, TOPES o SIN_REGLA_OPERABLE, no puede cambiar de desenlace.
Se relanzan sólo las que tenían nominaciones FDR > 0 y algo vivo que dependía de ellas:

| Campaña | Desenlace con la cola normal | Por qué se relanza |
|---|---|---|
| U1-6E-CONFIRMA-GBP-C-R | BLOQUEADA en el preflight de ruido | La causa raíz era la cola normal (`PROPUESTA_COLA_T_TAMIZ_FDR_20261103.md`) |
| CVGAP-NQ-R | PISTAS_VIVAS (11 nominadas) | Regla de la canasta v5; ¿siguen nominadas? |
| CVGAP-CFD-NQ-R | BLOQUEADA en el holdout (37 nominadas, 3 candidatas) | Regla de la canasta v5; ¿siguen nominadas? |
| U1-RACIMOS-GRILLA-NQ-R | PISTAS_VIVAS (5 nominadas) | Regla de la canasta v5 |
| U1-ZONAS-AVCL-NQ-R | PISTAS_VIVAS (2 nominadas) | Regla de la canasta v5 |

Con nominaciones FDR > 0 pero desenlace que no puede cambiar: U1-ES/YM/ORO-GRILLA-R y U1-ZONAS-BT2-NQ-R (INTEGRIDAD_FALLA),
U1-ZONAS-ES/NQ-R (SIN_REGLA_OPERABLE), U1-ZONAS-BT2-ES-R y CONF-CVR-CFD-NQ-R (SIN_CANDIDATAS). No se relanzan.
