# Manifiesto IPC-NIVEL-MES: ¿el nivel con ≥ 3 vueltas atrae al precio hasta barrerlo? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PRE-REGISTRO. Mira desenlaces: **STOP hasta el OK de Nico.** Nada corrido.
**Familia:** IPC (acumulaciones de picos como imán), sub-familia **IPC-NIVEL**, con presupuesto de multiplicidad propio.
No transporta resultados de IPC 25t/500t (NO_ROBUSTO), que usaban otra definición de zona.

## 1. Hipótesis, justificación y refutación
- **Hipótesis (Nico):** un nivel donde el precio se dio vuelta ≥ 3 veces, con mucho recorrido entre vueltas, acumula
  órdenes (stops del otro lado, órdenes límite en el nivel). Una vez formado, el precio vuelve y lo **barre** (lo pasa por
  ≥ 2 ticks) más seguido que lo que daría un paseo sin memoria con la misma volatilidad.
- **Justificación económica:** el nivel es obvio para cualquiera que mire el gráfico; la liquidez que se junta ahí es un
  objetivo para quien necesita llenar tamaño. Un objetivo sin ambigüedad (nivel plano) es operable.
- **Cómo podría refutarse:** P(barrer) no supera al nulo simulado, o no supera a un pivote suelto emparejado (una sola
  vuelta a la misma distancia): sería el efecto de cualquier extremo reciente y no de la acumulación.
- **Aviso de Nico (efectos que se anulan):** el precio puede barrer en unos contextos y respetar el nivel en otros. Un
  promedio nulo no descarta eso: se publican los dos canales (barrer; rebotar hasta alejarse 1 × d) y la distribución
  completa, y la separación por contexto (L2, tendencia) queda **pendiente y registrada**.

## 2. Población (regla de población: espacio de eventos enumerado)
Eventos posibles de la zona: formación (confirmación de la 3.ª visita), visita n-ésima, primer barrido, rebote,
expiración, estado continuo (distancia al nivel). **Se congela: la formación**, porque es el primer instante en que la
zona existe de forma causal. El estado continuo queda para una segunda etapa si la formación muestra algo.

## 3. Definición congelada (target-free, validada)
- Detector `tools/ipc_nivel.py` v2 con `docs/research/IPC_NIVEL_PARAMETROS_CONGELADOS_20260928.json`: ≥ 3 visitas
  separadas por salidas ≥ 14 t; picos monótonos; paso ≤ 2 t contra el pico anterior (3 t desde la 3.ª); zigzag R = 6 t;
  ≤ 200 velas entre picos; misma sesión. Validación: 82 % de acuerdo con Nico en 121 juicios fuera de la muestra de ajuste.
- **Variante estricta IPC-N4:** ≥ 4 picos (90 % de acuerdo).
- **Causalidad:** la zona existe en la vela en que el zigzag confirma el pivote de la 3.ª visita (reversión de R = 6 t);
  nada antes. Si la zona ya fue barrida antes de confirmarse, no hay evento.

## 4. Evento, resultado y nulo
- **Evento:** vela de confirmación. d = distancia en ticks del cierre al nivel.
- **Resultado (carrera):** barre (precio ≥ 2 t más allá del nivel) antes de alejarse 1 × d más en sentido contrario;
  horizonte 200 velas de 25t o fin de sesión; censura aparte.
- **Nulo:** `edgelab/research/espejo_nulo.py::simulate_null` con las mismas barreras, ternas 25t **estrictamente
  anteriores** a la vela del evento (lección de la auditoría 059), centradas, sin agregación (MULT = 1 para 25t).
- **Control C-PIV:** pivote suelto del zigzag, del mismo tipo, a la misma distancia (± 2 t) y edad (± 50 %), de la misma
  sesión, sin zona. Mismo resultado y mismo nulo.

## 5. Pruebas primarias
| # | Contraste | Celdas |
|---|---|---|
| P1 | barre − p0 (zona) | 2 variantes (v2, N4) × 2 lados (techo, piso) = 4 |
| P2 | (barre − p0)(zona) − (barre − p0)(C-PIV) | 4 |

**8 pruebas**, BH q = 0,10, bilaterales. Bootstrap por sesión (1.000); se publican MDE, n y los dos canales.

## 6. Datos y particiones
- **Instrumento:** MES (donde Nico marcó y juzgó). Velas 25t de research-v2 (Lucid), **precio de trade** (MES no tiene
  caché de midquote: riesgo declarado en §8).
- **Descubrimiento:** ago-2025 → mar-2026 (bundles mensuales 25t del visor). Febrero 2026 se usó para los juicios
  **sin desenlace**: se reporta con y sin febrero.
- **Confirmación (una vez, sólo celdas sobrevivientes):** MES abr–jun 2026, Lucid. **Holdout:** oct-2026 en adelante.

## 7. Economía
Entrada en la formación hacia el nivel, objetivo = barrido (+2 t), stop = alejarse 1 × d. Con d mediano ≈ 15–25 t y
fricción MES propia (a estimar; no se transporta la de ES), el exceso necesario es ≈ fricción / d. Se reporta aunque no
pague (Nico: se puede probar a mayor escala).

## 8. Riesgos
- Precio de trade: el rebote bid/ask puede fabricar «barridos» de 1 tick; por eso el barrido exige 2 t.
- La definición acierta 82 %: un nulo puede deberse al detector.
- MES y ES son el mismo índice: un resultado en MES no se transporta a ES sin medirlo.
- Superposición de zonas del mismo nivel: dedupe por construcción; bootstrap por sesión.
