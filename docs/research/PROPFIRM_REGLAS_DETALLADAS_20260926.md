# Prop firms: extracción detallada de reglas, incluidas las escondidas (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Rama:** `feat/propfirm-ev-20260926`. Sigue a `PROPFIRM_EV_DISENO_20260926.md`.
**Estado:** herramienta y datos de reglas. No corre búsquedas nuevas sobre retornos; cruza ventajas ya medidas.

## 1. Cómo se extrajo

- **Crawler por firma** (`edgelab/propfirm/crawl.py`, config `config/propfirms/crawl.json`):
  - recorre los sitemaps de los centros de ayuda;
  - usa la **API pública de Zendesk**, que devuelve el cuerpo aunque la web dé 403;
  - suma páginas bajadas a mano o con Firecrawl (`config/propfirms/manual/<firma>/*.md`, con la URL en la primera
    línea).
- **Taxonomía de 36 categorías** (`edgelab/propfirm/taxonomy.py`). Cada oración se clasifica por su impacto:
  - `sim`: entra al simulador;
  - `filtro`: decide si la estrategia puede operar esa cuenta;
  - `costo`: cambia el precio del intento.
- **Inventario por firma** (`artifacts/propfirm/crawl/<firma>/inventario.md`). Cada oración queda con su fuente, y hay
  una tabla de cobertura que marca **«0 — sin evidencia, buscar a mano»**. Una categoría en 0 es la señal de una regla
  que puede estar escondida.
- **Cobertura final:**

| Firma | Páginas | Oraciones con reglas | Categorías sin evidencia |
|---|---|---|---|
| Topstep | 63 | 1.222 | ninguna |
| MyFundedFutures | 80 | 1.052 | riesgo por trade, relación riesgo/beneficio |
| Lucid | 59 | 307 | días mínimos, días ganadores, riesgo/beneficio, ganancia extraordinaria, discrecional |
| Apex | 16 (Firecrawl) | 142 | tenencia mínima, martingala |
| Tradeify | 9 (Firecrawl) | 209 | riesgo/beneficio, ganancia extraordinaria, instrumentos |
| TakeProfitTrader | 60 (Zendesk) | 313 | inactividad, retiro mínimo, riesgo/beneficio, martingala |

## 2. Reglas escondidas que cambian la esperanza (ahora simuladas)

| Regla | Dónde aparece | Campo en `Rules` |
|---|---|---|
| Tope distinto por **número** de retiro | Apex 50K: 1.500, 1.500, 2.000, 2.500, 2.500, 3.000; Tradeify Growth: 1.500, 2.000, 2.500, 3.000+ | `payout_caps` |
| La cuenta **se cierra** tras N retiros | Apex: 6 retiros y la PA se cierra | `payout_max_count`, `close_after_max_payouts` |
| Días que cuentan **sólo si ganan un mínimo** | Apex 250 USD/día; Tradeify Flex 150; Topstep 150 | `payout_day_min_profit` |
| **Colchón** no retirable | Apex: DD + 100; Tradeify Daily 2.100; MFFU Rapid 2.100 | `payout_buffer` |
| **Retiro mínimo** | Apex 500; Tradeify 250 | `payout_min_amount` |
| Consistencia **desde el último retiro** | Apex 50 % en la PA | `funded_consistency_cap` |
| Base del retiro: ciclo o total | Tradeify Flex: 50 % del beneficio **total**; Daily: 2× el del ciclo | `payout_basis`, `payout_fraction` |
| Límite diario que pausa o elimina | Apex/Tradeify pausan | `daily_loss_mode` |
| Acceso de **30 días corridos** a la evaluación | Apex | `eval_access_days` |

## 3. Reglas que filtran la estrategia (no se simulan: deciden si aplica)

| Firma | Algoritmos | Tenencia / scalping | Noticias | Cierre obligatorio |
|---|---|---|---|---|
| **Apex** | **Prohibidos** («No Automation or Algorithm Usage») | HFT prohibido; brackets no direccionales prohibidos | se permite la estrategia normal; prohibido perseguir el precio o poner órdenes a ambos lados | antes del cierre de mercado |
| **TakeProfitTrader** | **Prohibidos** (UTP #1 «No Trading Bots or Algos») | penaliza tamaño agresivo en momentos fijos «favorables al simulador» | **sin posición ni órdenes de 1 min antes a 1 min después** de FOMC, NFP y CPI | no se pasa de día |
| Tradeify | Condicional: estrategia propia y exclusiva, sin HFT | en fondeada, **más del 50 % de los trades y de las ganancias con tenencia > 10 s**, o no hay retiro | permitidas, con restricciones | 16:45 ET |
| Lucid | Permitidos (sistemas y copiadores) | HFT prohibido; revisión si > 50 % de las ganancias vienen de trades de ≤ 5 s | **pérdida de la cuenta** en noticias «red folder» en LucidDaily | — |
| Topstep | Condicional en Combine/XFA; **imposible en la Live Funded Account** (la API no está en Live) | prohibidos los algoritmos de scalping que exploten fills irreales del simulador | — | 15:10 CT |
| MyFundedFutures | Condicional: propios, sin HFT, sin explotar el fill del simulador | prohibidos los brackets ajustados que aprovechan la falta de slippage y las múltiples límites al mismo precio | T1 permitido en la evaluación | — |

Otras reglas escondidas registradas en los inventarios:
- **Apex:** prohíbe un TP chico contra un SL desproporcionado (ejemplo explícito: 5 ticks contra 150), operar sin stop
  y usar el umbral como stop. El reporte de violaciones mira el **MAE**, la cobertura y el escalado.
- **Apex, inactividad de la PA:** hacen falta 2 días con 50 USD o más de ganancia en cada ventana móvil de 30 días; si
  no, la cuenta se cierra sin reintegro.
- **Apex, tamaño y límite diario:** contratos y DLL escalan por tramos de ganancia.
- **Apex, pase a Live:** tras 3 retiros seguidos de una misma PA puede mover al trader a Live y cerrarle todo lo
  simulado.
- **Tradeify, límites de compra:** 15 evaluaciones por 30 días, 10 reinicios por evaluación y 5 fondeadas por hogar.
- **Tradeify, actividad:** hay que operar al menos una vez por semana.
- **Tradeify, cambio de reglas por fecha:** los topes cambian con la fecha de compra (1-sep-2026).
- **Topstep:** en XFA Standard el retiro es el 50 % del saldo, hasta 2.000 USD. El día en que se pide el retiro no
  cuenta para el ciclo siguiente.
- **Lucid:** el pase a Live deposita sólo una parte del capital el día 1; el resto queda en escrow.
- **MFFU:** en los planes Rapid, el drawdown de la etapa fondeada es intradía.

**Consecuencia directa para EdgeLab:** toda estrategia de EdgeLab es un algoritmo, así que **Apex y TakeProfitTrader
quedan fuera**. `Rules.admits_algorithms()` lo aplica. En Topstep, además, la automatización no llega a la cuenta Live.

## 4. Cruce con las ventajas medidas (catálogo `config/propfirms/catalogo_detallado_50k.json`, 3.000 caminos)

Ventaja cero = mismo bracket, costos y tamaño, sin ventaja (control de Hall). Aporte = EV − EV sin ventaja.

| Cuenta 50K | IVC-L 40/40 1/día (+0,8 t, no validada) | TBZX macro 20/20 (+0,19 t, no validada) | Ventaja mín. ES 16/16 2/día |
|---|---|---|---|
| Apex EOD (**no aplica: prohíbe algoritmos**) | −210 / aporte +114 | −302 | +2,17 t |
| Tradeify Select Flex | +112 / +185 | +50 | +0,15 t |
| Tradeify Select Daily | +68 / +172 | +10 | +0,37 t |
| Topstep sin activación | +188 / +187 | +134 | −0,19 t (*) |
| MFFU Rapid | +26 / +173 | −40 | +0,49 t |

(*) Un requisito negativo quiere decir que la cuenta da EV ≥ 0 aun con una ventaja levemente negativa. Es el **valor de
opción** de la cuenta: cuota baja, retiro sobre el saldo total, sin tope de cantidad. **No es un edge.** Además, el
precio de Topstep es mensual y el modelo lo cobra por período.

**Lectura:**
- Las reglas escondidas cambian el ranking.
  - Con reglas simplificadas, Apex parecía comparable. Con acceso de 30 días, días calificados de 250 USD, colchón,
    retiro mínimo, topes por número y cierre a los 6 retiros, el EV es **negativo aun con ventaja**. Y encima prohíbe
    algoritmos.
  - Entre las que admiten algoritmos, la de menor requisito es Topstep, seguida de Tradeify Flex.
- Nada de esto cambia la conclusión metodológica: **ninguna de las ventajas del cruce está validada**. `gate()` sigue
  siendo la compuerta.

## 5. Limitaciones

- `verified = False` en todo el catálogo. Las reglas vienen de fuente primaria del 2026-09-26, pero falta la revisión
  humana, y los precios de Apex son de terceros.
- **No se simulan:**
  - el escalado de contratos y de DLL por tramos;
  - la inactividad;
  - el pase a Live a discreción de la firma;
  - la regla de tenencia (es un filtro sobre la distribución de duración de los trades, que la estrategia tiene que
    reportar).
- Faltan los precios de Lucid y TakeProfitTrader, y el monto de la activación de la ruta Standard de Topstep.
