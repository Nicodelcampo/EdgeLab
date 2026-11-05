# Revisión del atlas de contexto y vetos en R: fricción en R y lado inferido (04/11/2026)

Estado: VIGENTE — revisión de `RESULTADO_CONTEXTO_Y_VETOS_R_20261104.md` (rama `gemini/filtros-20261104`, mergeada en
`claude/vibrant-clarke-s9z6e2`). No cambia ninguna regla en producción. Sin datos nuevos: usa trayectorias ya guardadas.

## 1. La fricción en R explica una parte grande de los efectos «de contexto»

El P&L de cada operación se mide en R como `(pnl − fricción) / riesgo`. La fricción es fija en puntos por instrumento (costos
canónicos), así que **pesa más en R cuanto más chico es el stop**. Cualquier etiqueta que se correlacione con el tamaño del stop (ATR
bajo, volumen bajo, stop ancho S3) hereda ese efecto mecánico, sin que el mercado se comporte distinto.

Medido sobre las trayectorias de 8 de las 11 reglas (`programa_r_20261103/trayectorias/`, DESC + réplica, 846 operaciones), con terciles
del riesgo dentro de cada regla:

| Tercil del stop | n | Riesgo mediano (pts) | Fricción en R | Neto (R) | Bruto (R) |
|---|---|---|---|---|---|
| chico | 285 | 17,6 | 0,087 | +0,126 | +0,213 |
| medio | 279 | 39,8 | 0,040 | +0,136 | +0,176 |
| grande | 282 | 51,3 | 0,026 | +0,251 | +0,277 |

- Entre el tercil grande y el chico, el neto difiere en **+0,125R**, pero el bruto difiere en **+0,064R**. **La mitad de la diferencia es
  fricción.**
- Es del mismo orden que los efectos que el atlas confirma para `ctx_atr_rel=bajo` (−0,07 a −0,08R) y `ctx_vol_rel=bajo` (−0,06 a −0,07R).
  También explica parte del `+0,12R` del stop ancho S3.

**Qué se hace:**
- `grilla_generica.correr` guarda desde hoy, en la misma pasada, `marginales_globales_bruto`: los mismos marginales (ejecución y contexto)
  sobre el bruto `pnl / riesgo`.
- Se repite el meta-análisis sobre el bruto. Un efecto que **desaparece en bruto es fricción**, no contexto de mercado. Para eso el filtro
  correcto es un **piso de riesgo en ticks** (o elegir el stop mirando la fricción), no un veto por volatilidad.
- Un efecto que **se mantiene en bruto** es contexto real.

## 2. En 3 de las 11 reglas el lado de la operación está inferido, no medido

`tools/atlas_contexto_r.py::_operaciones_11_reglas` inventa datos que no tiene para U1-CRUZADO, TORI-NQ-R y CONF-CVR-CFD-NQ-R:
- el **lado**, que deduce del movimiento de las 30 velas previas (a favor en continuación, en contra en reversión), porque sus archivos de
  desarrollo no guardan el lado;
- el **TP**, que fija con un múltiplo constante del riesgo.

Las etiquetas orientadas por lado (`veto_muro`/imán, `ctx_vwap_favor`, `ctx_tendencia_favor`, `ctx_eficiencia_contra`, `veto_huida`)
pueden quedar invertidas en esas reglas.

**Consecuencia:** la evaluación de `atlas_veto_sin_iman_estructural` sobre las 11 reglas (8/11 reglas mejoradas, LOMO 14/14,
p_nulo 0,0195) mezcla 8 reglas con lado real y 3 con lado adivinado. Antes de citarla:
- volver a medir esas 3 reglas con el lado y el TP reales (relanzando `ANALIZAR_REGLA` con `operaciones=True`, que sí guarda la
  trayectoria), o
- reportar el resultado sólo sobre las 8 reglas con trayectoria completa.

El congelamiento prospectivo desde noviembre sigue valiendo, pero sobre el lado real de cada operación.

## 3. Otros cambios del merge

- `grilla_generica.correr`: el cálculo de contexto común va dentro de `try`. Si falla en un instrumento, queda
  `contexto_comun_error` en el resultado y la campaña sigue (antes la tumbaba).
- Kernels reconstruidos (`tools/reconstruir_kernels.py`): el CI de la rama de Gemini estaba en rojo por `test_kernel_u1_indaga_al_dia`.
- Contador global de pruebas: la cadena de hashes se volvió a encadenar con la única entrada nueva de Gemini
  (`programa_r/contexto_vetos_r/20261104`). `TrialRegistry.verify()` da válido.

## 4. Siguiente paso (requiere corrida)

Relanzar las etapas MARGINALES del atlas con el código mergeado (que ya guarda el bruto) y repetir el meta-análisis en bruto y en neto,
lado a lado, para S3/T3, `ctx_atr_rel`, `ctx_vol_rel`, `ctx_hora_ny` y `veto_muro`.

Aporte al referente: evita adoptar como «contexto de mercado» un efecto que es fricción en R, y deja medible esa separación en toda
campaña futura.
