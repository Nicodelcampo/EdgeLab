# Plan en espiral después del 27-nov: qué renovar y qué abrir con lo aprendido hoy (sin bonos)

Estado: PLAN — propuesta para que Nico elija. No se corrió nada nuevo; cada punto necesita su pre-registro antes de mirar datos.
Base: `confianza_sin_forward_20261127/` (con la auditoría de Antigravity), `trz_extranjeros_20261127/`, `cripto_v3_2019_20261127/`,
`supercartera_v3_20261127/` y `HANDOFF_2026-11-27_CANASTA_EDGE_AUDITORIA.md`.

## Lo nuevo que cambia el mapa
1. **Carril 2 es un mecanismo:** se transfiere a 8 índices y le gana al placebo. Su tamaño en vivo esperado es 0,4–0,6 de Sharpe.
   - Afuera decae desde 2009 y, desde ahí, no le gana a su control.
   - La mitad del resultado es estar comprado: en la REP, el control ganó.
   - Por regla: TOM, Turnaround Tuesday y Double 7 se sostienen afuera; IBS es débil; VBB estaba mal aplicada afuera (VIX de EE. UU.).
2. **T y R no se transfieren a Europa, ni siquiera antes de costos.** Ya se sabía que el salto desde 2020 está en NQ, ES y YM y no en
   MidCap ni Russell. Baja la probabilidad de que sea un mecanismo general de apertura: o es propio de esos índices desde 2020, o es
   ajuste del vendedor.
3. **Cripto:** en dos tramos que nadie miró (2020 y el HOLDOUT), el momentum cruzado (XSMOM) gana y BAB no aporta. La canasta sigue
   NO_CONCLUYENTE.
4. **Cartera:** Carril 2 y macro risk premia tienen correlación 0,04. Los frentes limpios (sin el sesgo del vendedor) dan Sharpe 0,85
   en 2006–2026.
5. **Errores del día que hay que convertir en guardas:**
   - hora de una fuente externa distinta de la documentada (HistData);
   - costo en puntos de un instrumento aplicado en la escala de otro;
   - sacar meses de una muestra después de ver el resultado;
   - una variable de EE. UU. (VIX) usada como si fuera local en otro mercado.

## Propuestas, en orden de aporte por costo
| # | Qué | Usa lo nuevo | Qué gana | Datos | Cómo podría refutarse | Costo |
|---|---|---|---|---|---|---|
| 1 | **Guardas K58–K61** de los cuatro errores de arriba, en código y CI | Los errores de hoy | Que no se repitan: cada uno movió un veredicto | — | — | Bajo |
| 2 | **Mecanismo de T: ETF apalancados.** Una hipótesis: la ventaja de T sigue al rebalanceo de los ETF apalancados (TQQQ/SQQQ, UPRO/SPXL, UDOW/SDOW, TNA/TZA; Baltussen et al. 2021). Predicciones: crece con el AUM relativo al volumen del futuro; es mayor en NQ, menor en RTY/EMD y nula en Europa (casi sin ETF apalancados); el quiebre de 2021-02 coincide con el salto de AUM de TQQQ. La gamma de dealers ya está cerrada como filtro (`F-GEX-DIA-TENDENCIA`, NO_REPETIR), y el 0DTE diario (2022) llega después del quiebre (2021-02): por eso este mecanismo y no ésos | T no se transfiere a Europa ni a RTY/EMD | Si se confirma: un mecanismo y un interruptor ex ante (si el AUM cae, T se apaga). Si no: baja la confianza previa del forward de T | M1 NT8 (ya está) + AUM o acciones en circulación diarias de los ETF (emisores; fuente a verificar) | Sin relación con el AUM, o el ranking entre índices al revés. **Potencia baja:** 5 índices y un quiebre; es una prueba de signo y de orden | Medio |
| 3 | **Carril 2 en MidCap (EMD), instrumento que nunca usó**, con las reglas congeladas | Se transfiere afuera, pero allá decae desde 2009 y no le gana al control: hace falta N en EE. UU. y post-2009 | Más N limpio en el período que importa (2009–2026), con el control N como placebo | M1 NT8 de EMD (ya está) | Regla − control ≤ 0 en EMD desde 2009 | Bajo |
| 4 | **VBB, VZ y EVRP afuera con su volatilidad local** (VSTOXX, VHSI, índice de volatilidad del Nikkei, etc.) | VBB estaba mal aplicada afuera | Corrige una prueba mal hecha; decide si las reglas de volatilidad también se transfieren | Yahoo diario (ya se usa); cobertura de cada índice de volatilidad a verificar | Negativa con la volatilidad local | Bajo |
| 5 | **XSMOM sola en datos nunca usados:** Binance spot 2017-08 → 2019-08, antes de los perpetuos | XSMOM gana en dos tramos vírgenes; BAB no | Más N para la única pata cripto consistente, sin tocar los meses ya vistos | data.binance.vision (ya se usa) | t ≤ 0, o positiva sólo en 2017 | Medio |
| 6 | **Cartera con tamaños esperados en vivo, no históricos:** Carril 2 a 0,4–0,6 de Sharpe, T+R con la confianza rebajada y macro risk premia a su deflactado; reparto entre cuentas Swing (FTMO, propia) y LucidFlex (flat 16:40) | Las confianzas de hoy | Tamaños que no asumen el Sharpe del backtest | Series ya calculadas | — (es asignación, no una prueba) | Bajo |
| 7 | **Integridad de la serie de H3:** `canasta_amplia.py` censura 279 operaciones en DESC y 53 en REP en la frontera; la serie y H3 discrepan (1,07 contra 0,80) | Hallazgo de Antigravity | Una sola serie canónica de Carril 2 | Ya está | — | Bajo |
| 8 | **Z en Europa con futuros reales** (FDAX, FESX) | Z no calibra con CFD | Cierra la transferencia de la intradía | Comprar M1 de futuros de Eurex (decisión de Nico) | — | Alto; baja prioridad, porque T y R ya fallaron afuera |

## Qué no hacer
- **No** repesar Carril 2 por regla con lo visto afuera (TOM/TT arriba, IBS/VBB abajo): sería elegir con datos ya mirados.
- **No** sacar BAB de la canasta cripto por el resultado de 2020: se decide en un pre-registro nuevo, para forward.
- **No** buscar variantes de T y R en Europa: el resultado bruto ≈ 0 cierra esa vía (`NO_REPETIR`).
- **No** operar Carril 2 afuera: desde 2009 no le gana a su control.

## Orden propuesto
- Primero 1, 3, 4 y 7: bajo costo, datos ya disponibles, suben o bajan la confianza de la pata más sólida.
- Después 2: es el que más puede cambiar la decisión sobre la intradía en forward, con potencia baja.
- Después 5 y 6.
- El 8 sólo si Nico compra los datos.

Aporte al referente: ordena los próximos pasos según cuánto acercan a una ventaja neta operable con datos ya disponibles. Cada
fracaso de hoy queda convertido en una prueba que lo explica o en una guarda que impide repetirlo.
