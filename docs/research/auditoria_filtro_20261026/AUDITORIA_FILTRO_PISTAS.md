# Auditoría — ¿el embudo es demasiado estricto? (por qué sólo sobrevive U1-CRUZADO)

Estado: VIGENTE (hallazgo; las propuestas de §4 esperan decisión de Nico: son semántica de validación)
Fecha: 2026-10-26. Pedido de Nico: «me parece raro que sólo U1 de USATECH haya sobrevivido; justo el primero que hice».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Respuesta corta
Sí, hay una asimetría real. U1-CRUZADO se evaluó **antes** de que existiera el embudo de grilla masiva: regla específica, réplica directa.
Las familias posteriores (EXPZ, ZGAP) pasaron por (a) FDR sobre ~240.000–335.000 celdas evaluables en el DESC y, sin nominadas, (b) la
réplica de **pistas**, donde cada una de las 20 se exige con un umbral de LORD++ dividido por 20. **Esa segunda compuerta tiene 1–2 % de
potencia** para un efecto de la mitad del DESC en una réplica de 6 meses, y cuando no rechaza **cierra la familia como SIN_CANDIDATAS**.
Es matar sin potencia, lo que el propio proyecto prohíbe («un nulo sin potencia no mata», decisión 2 del 2026-10-24) y lo que el OOS ya
evita (NO_CONCLUYENTE). La etapa de pistas quedó sin ese chequeo.

## 2. Lo que mostraron las réplicas (datos bajados de los kernels `embudo-*-rep-20260401`; ventana abr–sep 2026)
| campaña (ejecución) | pistas con media > 0 en la réplica | canasta igual-ponderada de las 20 pistas, por sesión | umbral por pista | potencia típica por pista |
|---|---|---|---|---|
| ZGAP-NQ (futuro NQ) | **18 / 20** | **+5,2 pts, IC90 [+0,35; +10,0], p 0,042** | p ≤ 0,00055 | ≈ 0,02 |
| EXPZ-NQ (futuro NQ) | **16 / 17** evaluables | +2,6 pts, IC90 [−1,4; +7,0], p 0,15 | p ≤ 0,00055 | ≈ 0,01 |
| EXPZ-CFD | 10 / 19 | −0,5, p 0,61 | p ≤ 0,00018 (**«un rechazo era imposible»**, igual se cerró) | 0 |
| ZGAP-CFD | 3 / 18 | −1,3, p 0,91 | p ≤ 0,00018 | 0 |

Lectura: en el **futuro NQ** las dos familias se encogen mucho respecto del DESC (sesgo de selección esperado: +18 → +4,5 de media en
EXPZ-NQ) pero **siguen positivas casi todas**; con el CFD como ejecución, no. Bajo el nulo esperaríamos ~50 % positivas. Las pistas
están correlacionadas (celdas vecinas), así que 18/20 no equivale a 18 pruebas independientes; la canasta por sesión es la forma honesta
de juntarlas y da p 0,042 en ZGAP-NQ. **Esto es post-hoc** (la canasta no estaba pre-registrada y la ventana abr–sep ya se miró): no
confirma nada, pero muestra que la familia no estaba muerta: estaba sin potencia.

## 3. Otras compuertas revisadas
- DESC con FDR (q 0,10) sobre cientos de miles de celdas: es correcto como control, y con linaje «información» no se infla. Exige efectos
  grandes en el DESC; por eso existe la ruta de pistas (ATJ-25), que es la que falla.
- OOS: mata sólo con potencia y en el régimen actual: correcto.
- INTEGRIDAD (placebo ≤ 25 % de la regla, latencia): no mató a ninguna de las familias revisadas.
- `min_ops_oos` (30): sólo endurece la elección de candidatas raras; no cerró familias.
- Análisis viejos con FWER (max-T, Holm): ya inventariados en `RELANZAMIENTO_ANALISIS_VIEJOS_20261025.md`; varios se relanzaron.

## 4. Propuestas (requieren OK de Nico: cambian la semántica de validación; se aplican hacia adelante)
1. **Pistas con potencia**: si la réplica no tiene potencia ≥ 0,8 para el 50 % del efecto del DESC al umbral de la pista, el veredicto es
   **SIN_POTENCIA (viva)**, no SIN_CANDIDATAS. Igual que el OOS. Incluye el caso «rechazo imposible» de EXPZ-CFD.
2. **Prueba agregada pre-declarada**: además de las pistas una por una, la **canasta igual-ponderada de las k pistas** como UNA prueba
   (bootstrap por sesiones) con el nivel completo de LORD++ del lote. Detecta un edge difuso (muchas celdas vecinas débiles) que la prueba
   individual no puede ver.
3. **Reclasificar** EXPZ-NQ, EXPZ-CFD, ZGAP-NQ y ZGAP-CFD de «SIN_CANDIDATAS» a «SIN_POTENCIA en pistas» en el registro. No confirma nada.
4. Para **ZGAP-NQ y EXPZ-NQ**, que no usaron su holdout: congelar AHORA (antes de mirar el holdout) la canasta de sus 20 pistas como regla
   única y llevarla al holdout a N fijo por el protocolo de apertura. Es la única confirmación limpia posible: la ventana abr–sep ya se miró.

Mientras Nico decide, **U1-ZONAS-AVCL-NQ quedó frenada antes de su etapa de pistas** (PISTAS PENDIENTE, sin lanzar), para que el criterio
se fije antes de ver su resultado.

## 5. Cómo podría refutarse
Si en el holdout la canasta de pistas de ZGAP-NQ/EXPZ-NQ da ≈ 0 con potencia, la lectura de «edge difuso» cae y la estrictez del embudo no
habría costado nada. Si da positiva, el filtro estaba matando familias reales.

## 6. Aplicado (Nico aprobó las cuatro propuestas, 2026-10-26)
1. **Pistas con potencia** y 2. **canasta como una prueba**: `escalera.canasta_pistas` + `escalera.veredicto_pistas`; `embudo._fin_pistas`
   corre primero la canasta (su propio paso de LORD++, nivel completo) y después las pistas. Veredictos: CANASTA_CONFIRMADA,
   PISTAS_CONFIRMADAS, REFUTADA (canasta en contra con potencia) → SIN_CANDIDATAS; SIN_RECHAZO / SIN_POTENCIA → fase **PISTAS_VIVAS**
   (viva). Tests: ruido no confirma ni mata, canasta en contra refuta, edge difuso lo confirma la canasta.
3. **Reclasificadas** EXPZ-NQ, EXPZ-CFD, ZGAP-NQ, ZGAP-CFD → PISTAS_VIVAS (veredicto SIN_RECHAZO: con potencia para la mitad del efecto
   del DESC la canasta no lo alcanza, pero no está en contra). Canasta calculada sobre la réplica ya mirada: no confirma.
4. **Holdout de canastas** (`tools/holdout_canasta.py`: acta → conteo sin P&L → decisión con el paso reservado):
   - **ZGAP-NQ: acta registrada** (`ZGAP-NQ-CANASTA`, apertura única de ZONAS_GAPS, α reservado 0,00189, **N = 530 sesiones**: potencia
     0,8 para la media de la réplica, +5,2 pts por sesión con desvío 32). Al ritmo de ~250 sesiones por año, decide en ≈ 2 años.
   - **EXPZ-NQ: acta NO registrada.** Con su media de réplica (+2,6) y el nivel de LORD++ actual (0,0019) harían falta ≈ 1.560 sesiones
     (> 6 años); con 500 la potencia es 0,22. Abrir el holdout así gastaría la única apertura de EXPANSION_ZONAS casi seguro sin poder
     decidir. Queda viva (PISTAS_VIVAS) esperando una forma de ganar potencia (más instrumentos con la misma regla, o normalización).
U1-ZONAS-AVCL-NQ siguió a su etapa de pistas con el criterio nuevo (fijado antes de ver su resultado).
