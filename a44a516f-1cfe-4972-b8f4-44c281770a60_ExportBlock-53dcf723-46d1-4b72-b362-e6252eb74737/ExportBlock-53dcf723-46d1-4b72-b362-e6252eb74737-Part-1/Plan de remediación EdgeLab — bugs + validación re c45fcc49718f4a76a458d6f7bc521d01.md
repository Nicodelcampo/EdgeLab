# Plan de remediación EdgeLab — bugs + validación real del edge ARB

> **Objetivo:** resolver todos los hallazgos de la revisión de código de EdgeLab (jul 2026) y someter el único edge "sobreviviente" (ARB EURUSD) al mismo estándar de validación que mató a las otras 5 estrategias. Ejecutable con Claude Code en tu máquina local.
> 

<aside>
🔎

**Revisión técnica v2 — 21 jul 2026:** corregí varias suposiciones demasiado fuertes del primer plan. Las más importantes: no asumir horarios FX UTC fijos durante todo el año; no cerrar una posición retrospectivamente al último tick anterior a las 16:00; no afirmar que vectorbt resuelve conservadoramente una barra donde TP y SL fueron tocados; no confundir PBO con un simple conteo de configuraciones; y no sumar un costo fijo de spread si el backtest ya ejecuta con bid/ask.

</aside>

## Decisiones que deben congelarse antes de implementar

1. **Semántica de barras:** declarar si el timestamp etiqueta apertura o cierre, intervalo `[inicio, fin)`, origen y offset del resample. Ejemplo recomendado: barra `07:45` = `[07:45:00, 08:00:00)` y su señal queda disponible recién a las `08:00:00`.
2. **Calendario FX:** usar calendario/configuración de sesión versionada; apertura/cierre UTC cambia con DST. Nunca codificar “viernes 22:00–domingo 21:00” como verdad anual.
3. **Capas de costo separadas:** spread observado en bid/ask, comisión explícita y slippage/model risk. Ejecutar con bid/ask ya incorpora spread; volver a restarlo como fee sería doble conteo.
4. **Política de datos incompletos:** si falta el tick ejecutable de salida, marcar día/corrida como incompleto o usar el siguiente tick dentro de una tolerancia declarada. No usar retrospectivamente el último tick anterior al horario de salida.
5. **Relojes separados:** `signal_time`, `decision_time`, `order_time` y `fill_time`. Esto evita look-ahead al evaluar el close de una barra y llenar en ese mismo timestamp.
6. **Veredicto pre-registrado:** congelar hipótesis, familia de parámetros, métrica primaria, costes y reglas de promoción antes de abrir el holdout.

<aside>
⚠️

**Regla de oro para todo el plan:** ningún fix se considera terminado sin (a) un test que falle antes del fix y pase después, (b) un commit atómico con mensaje descriptivo, (c) una entrada en el ledger de auditoría si toca resultados. Esto es coherente con tu CONTRATO_[LLM.md](http://LLM.md) — recordáselo a Claude Code al inicio de cada sesión.

</aside>

# Cómo trabajar este plan con Claude Code

1. **Una fase por sesión** de Claude Code. No mezcles fases: el contexto se degrada y aumenta el riesgo de que "arregle" cosas que no le pediste.
2. **Prompt inicial de cada sesión:** pegá el bloque "Prompt sugerido" de la fase + `CONTRATO_LLM.md` + los archivos listados en "Archivos a tocar". Pedile explícitamente: *"No modifiques ningún archivo fuera de esta lista sin preguntarme."*
3. **Antes de cada fase:** `git checkout -b fase-N-descripcion` y `pytest -q` para confirmar baseline verde.
4. **Después de cada fase:** revisá el diff completo (`git diff main`) vos mismo antes de mergear. No delegues la revisión del diff al mismo LLM que lo escribió.
5. **Orden obligatorio:** Fase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Las fases 3→4→5 son dependientes en cadena; 1, 2 y 6 son paralelizables si querés.

---

# Fase 0 — Higiene y baseline (½ día)

**Objetivo:** poder detectar regresiones antes de tocar nada.

**Archivos a tocar:** raíz del repo, `requirements.txt` (nuevo), `tests/` (nuevo), `strategies/tickfade.py`, `strategies/tick_fade.py`, `edgelab/config.py`.

**Pasos:**

1. Inicializar git si no existe; commit inicial de todo el estado actual como `baseline-pre-remediacion` (tag).
2. Crear `pyproject.toml` con dependencias directas y un lock reproducible (`uv.lock` o equivalente). Evitar usar `pip freeze` como especificación primaria: captura dependencias transitivas y dificulta upgrades controlados. Registrar versión de Python, SO, CPU y versiones de numba/LLVM en `ENVIRONMENT.md`.
3. **Deduplicar** `strategies/tickfade.py` y `strategies/tick_fade.py`: diff línea a línea, conservar uno solo (el que corre el harness), borrar el otro, actualizar imports. Los docstrings mezclados indican merge accidental — verificar que la lógica conservada sea la correcta contra el ledger.
4. Mover rutas hardcodeadas de Windows (`C:\ProyectosQuant\EdgeLab`, `C:\$AVectorBTecosistema\ES_ticks.parquet`, `D:\A  Trading`) a un `config.toml` o variables de entorno con defaults. Un solo punto de verdad en `edgelab/config.py`.
5. Crear `tests/` con pytest y un fixture de ticks pequeño, inmutable y versionado. El canario principal debe comparar el **ledger de trades** (dirección, timestamps, razón de salida y precios en unidades enteras) y luego PnL con tolerancia explícita. Evitar que un float exacto a 4 decimales sea la única garantía: puede variar entre plataformas sin que cambie la lógica.
6. Eliminar el no-op `sum(...)/4.0*4` donde aparezca (buscar con grep).

**Criterios de aceptación:**

- `pytest -q` verde con ≥1 test de regresión de PnL exacto.
- Repo corre en una carpeta nueva clonada solo con `config.toml` editado.
- Un solo archivo tickfade con historia clara.

**Prompt sugerido:** *"Lee CONTRATO_[LLM.md](http://LLM.md). Vamos a hacer higiene del repo sin cambiar ninguna lógica de trading. Cualquier cambio que altere un solo trade o un solo tick de PnL es un bug de esta fase. Tareas: [pegar pasos 1-6]. Al final, corré el smoke test y mostrame el PnL de referencia."*

---

# Fase 1 — Barras fantasma de fin de semana (1 día) 🔴

**Objetivo:** eliminar las barras planas de sábado/domingo que genera `resample('15min').ohlc().ffill()`, que distorsionan la SMA200 y inflan el Sharpe anualizado con `sqrt(96*252)`.

**Archivos a tocar:** `databuild/build_eurusd.py`, `validation/vectorbt_eurusd_tod.py`, `validation/vectorbt_eurusd_portfolio.py`, `validation/vectorbt_eurusd_opt.py`, `validation/vectorbt_eurusd_deep.py`.

**Pasos:**

1. En `build_eurusd.py`, producir junto a cada barra `tick_count`, `first_tick_ts`, `last_tick_ts` y `is_synthetic`. No aplicar `ffill()` indiscriminado. Barras sin ticks no pueden generar señales ni fills; si se conservan para continuidad del índice, deben quedar marcadas y excluirse de indicadores sensibles salvo que una política explícita diga lo contrario.
2. Escribir tests con un calendario FX versionado y semanas que cubran ambos regímenes DST. Asertear que no hay barras operables durante el cierre y que los huecos de datos dentro de mercado abierto se distinguen de un cierre programado. No usar horas UTC fijas para todo el año.
3. **Recalcular la SMA200** tras el fix y cuantificar el impacto: script que compare la SMA200 vieja vs nueva en las 4 ventanas de entrada del ARB (08:45/09:00/11:00/12:00 UTC) y reporte en cuántas señales cambia el filtro (pasa/no pasa). Guardar ese reporte en el ledger.
4. Corregir la anualización del Sharpe: no usar `sqrt(96*252)` fijo; calcular barras reales promedio por año a partir del índice, o anualizar sobre retornos diarios agregados (más robusto).
5. Re-correr los cuatro scripts vectorbt de EURUSD y registrar el delta de métricas (Sharpe, PnL, nº trades) antes/después en `EDGES_DISCOVERED.md` — **sin editar todavía el veredicto del edge**, solo los números.

**Criterios de aceptación:**

- Test de ausencia de barras de fin de semana verde.
- Reporte cuantificado: "la SMA200 corregida cambia la señal en X% de las entradas del ARB".
- Sharpe recalculado con anualización basada en barras reales.

**Prompt sugerido:** *"Bug confirmado: el resample M15 con ffill crea barras planas de fin de semana que contaminan la SMA200 y la anualización. Fix en [archivos]. Primero escribí el test que demuestra el bug (debe fallar), después el fix, después el reporte de impacto sobre las señales del ARB. No toques la lógica de estrategia."*

---

# Fase 2 — Fix de `engine_validator.py` (½–1 día) 🟠

**Objetivo:** que el validador del motor valide de verdad, en vez de usar PnL hardcodeado.

**Archivos a tocar:** `validation/engine_validator.py`, `edgelab/engine.py` (solo lectura), `edgelab/instruments.py`.

**Pasos:**

1. Eliminar los `pnl = 20.0` / `-20.0` hardcodeados: el validador debe calcular el PnL esperado desde los ticks sintéticos usando la especificación del instrumento (tick size, tick value) de `instruments.py`, de forma **independiente** del engine (implementación paralela ingenua en Python puro, sin numba).
2. Incluir `FEES_RT` en el PnL esperado (hoy no aplica fees → cualquier bug de fees del engine pasa invisible).
3. Aplicar `poison_mask()` sobre las ventanas de veneno de ES (2026-03-15..21 y 2026-06-11..16) también en el validador, y agregar un caso de test donde un trade sintético cae **dentro** de una ventana envenenada y se assertea que el engine lo excluye.
4. Agregar casos borde al set sintético: trade que cruza medianoche, TP y SL tocados en el mismo tick (¿qué convención gana? documentarla), gap que salta el SL (slippage), sesión que termina con posición abierta.
5. Integrar el validador al preflight de 4 checks existente como quinto check (o dentro del check synthetic si ya existe un slot).

**Criterios de aceptación:**

- Cero constantes de PnL hardcodeadas (grep `= 20.0` limpio).
- Validador falla si se le inyecta un bug deliberado en fees o en poison_mask (test de mutación manual: romper el engine a propósito, ver que el validador lo agarra, revertir).

**Prompt sugerido:** *"engine_[validator.py](http://validator.py) tiene PnL esperado hardcodeado, no aplica fees ni poison_mask. Reescribilo para que calcule el PnL esperado de forma independiente al engine, desde los ticks sintéticos + specs del instrumento. Después vamos a hacer un test de mutación: yo voy a romper el engine a propósito y el validador tiene que detectarlo."*

---

# Fase 3 — Extensión del motor: salida por timestamp (1–2 días)

**Objetivo:** que el engine soporte `exit_at_time` (ej. cierre forzado 16:00 UTC), requisito para portar el ARB real. Hoy el harness solo tiene `MAX_HOLD_MS`.

**Archivos a tocar:** `edgelab/engine.py`, `edgelab/sessions.py`, `validation/engine_validator.py` (agregar casos), `validation/smoke_test.py`.

**Pasos:**

1. Diseño primero (pedile a Claude Code el diseño **antes** del código): agregar al contrato de estrategia un campo opcional `exit_at_utc: time | None`. Si está seteado, el engine cierra la posición al primer tick con `timestamp >= exit_at_utc` del día de entrada, al precio de ese tick (lado correcto del spread).
2. Definir interacción con `MAX_HOLD_MS`: gana el que ocurra primero. Documentar en el docstring del engine.
3. Definir caso borde: si no hay tick a partir de `exit_at_utc`, usar el primer tick posterior solo si cae dentro de `max_exit_lateness_ms`; en caso contrario marcar `DATA_INCOMPLETE`, invalidar ese día para evaluación y conservar la posición solo dentro de una simulación diagnóstica separada. Está prohibido cerrar retrospectivamente al último tick anterior a la hora objetivo.
4. Implementar en el hot loop de numba con cuidado de no romper el smoke test de Fase 0 (el PnL canario **no debe cambiar** para estrategias sin `exit_at_utc`).
5. Agregar al `engine_validator` 3 casos sintéticos: salida exacta a las 16:00, TP antes de las 16:00 (no debe salir a las 16:00), gap sin ticks post-16:00.

**Criterios de aceptación:**

- PnL canario de Fase 0 idéntico (backward compat).
- 3 casos sintéticos nuevos verdes.
- Convención TP/SL/exit-time del mismo tick documentada.

---

# Fase 4 — Portar el ARB real al harness (1–2 días) 🔴

**Objetivo:** el edge documentado en `EDGES_DISCOVERED.md` (Asian Range Breakout + SMA200) **nunca pasó por el gauntlet**; la versión del harness (`eurusd_session_breakout.py`) es otra estrategia distinta (ventana 07:00–09:00, tp15/sl5, hold 5 min). Portar el ARB verdadero, parámetro por parámetro.

**Archivos a tocar:** `strategies/eurusd_arb.py` (nuevo), `validation/harness.py`, `edgelab/sessions.py`.

**Especificación exacta a implementar (fuente: EDGES_[DISCOVERED.md](http://DISCOVERED.md) + JForex):**

- Rango asiático: **no elegir el endpoint por intuición**. Primero reconstruir la convención exacta del JForex original. Si las barras están etiquetadas por apertura, incluir la barra `07:45` significa que el rango termina a `08:00:00` y no a `07:44:59`; la redacción anterior era contradictoria. Guardar explícitamente `bar_interval=[inicio,fin)` y `range_available_at`.
- Ventanas `08:45`, `09:00`, `11:00`, `12:00`: determinar si nombran apertura de barra, cierre de barra o instante de decisión. Una señal calculada con la barra `[08:45,09:00)` no puede ejecutarse antes de `09:00` más latencia. El test de paridad debe comparar `signal_time`, `decision_time` y `fill_time`, no solo un timestamp ambiguo.
- Filtro: precio vs SMA200 en M15 (con las barras corregidas de Fase 1). Long solo si close > SMA200, short solo si close < SMA200 (confirmar dirección exacta contra el código vectorbt).
- TP 20 pips, SL 50 pips, salida forzada 16:00 UTC (usa Fase 3).
- Fills con ticks reales bid/ask (no mid), fees según spec del instrumento.
1. Escribir la estrategia en el contrato del harness, con la SMA200 precalculada offline desde las barras M15 corregidas (pasada como serie auxiliar; no calcularla en el hot loop).
2. **Test de paridad:** correr el ARB en el harness sobre el mismo período que la validación vectorbt y comparar trade por trade (timestamps de entrada). Diferencias esperadas: fills tick vs mid. Diferencias NO esperadas: señales distintas → bug de port. Generar CSV de trades de ambos lados y un script de diff.
3. Documentar cada discrepancia de señal encontrada (probablemente aparezcan por la SMA200 corregida — eso es información, no error).

**Criterios de aceptación:**

- Mismas señales de entrada (± diferencias explicadas y documentadas una por una) entre harness y vectorbt.
- PnL del harness con ticks reales reportado junto al PnL vectorbt mid-price: la diferencia es tu **costo de fricción real**.

**Prompt sugerido:** *"Vas a portar una estrategia a nuestro harness. La spec exacta es: [pegar spec]. NO es eurusd_session_[breakout.py](http://breakout.py) — esa es otra estrategia. Primero mostrame tu interpretación de la spec en pseudocódigo y esperá mi confirmación antes de escribir código."* (este patrón de confirmación es el núcleo del Plan 2)

---

# Fase 5 — Gauntlet completo sobre el ARB (2–3 días) 🔴

**Objetivo:** someter el ARB al mismo estándar que mató al ORB de ES (MCPT p=0.15). Es la fase decisiva del plan.

**Archivos a tocar:** `validation/mcpt.py`, `validation/gauntlet.py`, `validation/pbo.py`, `validation/spa.py`.

**Pasos:**

1. **Diseñar el MCPT desde la hipótesis nula, no desde el instrumento.** Implementar y comparar al menos dos nulls: (a) randomización/circular shift de la asignación señal→retorno por día, preservando cada trayectoria intradía; (b) permutación por bloques de retornos que preserve autocorrelación y heterocedasticidad. La variante “dejar fijo el rango asiático y permutar solo después de las 08:00” queda como experimento, no como test automáticamente válido. Usar `p=(exceedances+1)/(B+1)`, seed fija y ≥2.000 permutaciones cuando el costo lo permita.
2. Correr **CSCV/PBO real** sobre una matriz sincronizada `período × configuración`, con suficientes bloques y retornos OOS por split. El número de configuraciones exploradas es necesario para declarar multiplicidad, pero **no es el denominador de PBO**. Incluir todas las variantes recuperables de los scripts y CSV, registrando las que no pueden reconstruirse.
3. Correr SPA (test de White/Hansen ya implementado en `spa.py`) contra el universo completo de estrategias probadas y descartadas (Mean Reversion, Friday Fade, variantes de ventanas).
4. Aplicar los umbrales existentes sin excepciones: `MCPT_MAX_P = 0.05`, `PBO_MAX = 0.50`. **Escribir el veredicto en el ledger antes de mirar si te gusta.**
5. Walk-forward temporal adicional: los 18 meses de JForex son una sola muestra; partir en 3 semestres y verificar consistencia de signo del PnL por semestre (el ORB de ES murió exactamente por drift semestral — F4b).

**Criterios de aceptación:**

- p-value MCPT, PBO y SPA del ARB registrados en el ledger con seed fijo y reproducibles.
- Multiplicidad declarada explícitamente (nº total de configuraciones exploradas).
- Consistencia por semestre reportada.

<aside>
🎯

**Resultado honesto posible:** que el ARB muera aquí. Eso no es un fracaso del plan — es el plan funcionando. El doble estándar actual (gauntlet para todo excepto para el único edge "vivo") es el riesgo más caro del proyecto.

</aside>

---

# Fase 6 — Fixes vectorbt: stops OHLC + rango asiático (½ día)

**Archivos a tocar:** `validation/vectorbt_eurusd_portfolio.py`, `validation/vectorbt_eurusd_tod.py`.

**Pasos:**

1. Pasar OHLC a la simulación vectorizada solo como diagnóstico. Si TP y SL caen dentro de la misma barra, OHLC no revela el orden y no debe afirmarse que vectorbt elige siempre el peor caso. Marcar esos trades como `INTRABAR_AMBIGUOUS` y resolverlos con ticks/sub-barras; reportar además límites optimista y pesimista. El resultado promocionable es el del harness tick bid/ask.
2. Unificar la definición del rango asiático según lo decidido en Fase 4 (00:00–07:44:59) en ambos scripts.
3. Re-correr y registrar el delta de métricas vs Fase 1 en el ledger.

**Criterio de aceptación:** los dos scripts usan la misma constante de sesión importada desde `edgelab/sessions.py` (no duplicada localmente), y los stops se evalúan con OHLC.

---

# Fase 7 — Sensibilidad a costos y multiplicidad (½–1 día)

**Objetivo:** el edge neto del ARB es ~2 pips/trade con fees asumidos de 1 pip. Eso es frágil.

**Pasos:**

1. Sweep por componentes: comisión `0…1.5 pips`, slippage adicional `0…2 pips` y multiplicador de spread observado `1.0…2.0`. Con fills bid/ask, el spread base ya está incorporado y no debe restarse otra vez. Graficar PnL, expected shortfall y porcentaje de meses positivos; identificar superficies y costo de quiebre.
2. Medir spread y latencia por ventana, régimen de volatilidad y eventos macro. Comparar el costo de quiebre contra percentiles p50/p90/p99, no solo contra el promedio.
3. Haircut por multiplicidad: reportar el PnL esperado ajustado (p.ej. deflated Sharpe ratio de Bailey/López de Prado, o al menos el PnL de la mediana de configuraciones vecinas en el espacio de parámetros — si solo la config exacta TP20/SL50 gana y TP18/SL45 pierde, es ruido).
4. Test de vecindad de parámetros: grilla TP ∈ {15,18,20,22,25} × SL ∈ {40,45,50,55,60}; el edge debe ser una meseta, no un pico.

**Criterios de aceptación:** gráfico costo-de-quiebre + meseta de parámetros en el ledger.

---

# Fase 8 — Veredicto y documentación (½ día)

1. Actualizar `EDGES_DISCOVERED.md` con el estado real del ARB: PROMOVIDO (pasó gauntlet completo) o RETRACTADO (con el mismo formato honesto de EXP-041/043/044).
2. Actualizar `PLAN.md` con el estado 6/6 o 5/6.
3. Escribir un `POSTMORTEM.md` corto: qué permitió que un edge llegara a "descubierto" sin pasar el gauntlet (respuesta esperada: no había un gate estructural — eso lo resuelve el Plan 2 de infraestructura).
4. Tag de git `remediacion-completa`.

---

# Resumen de esfuerzo y dependencias

| Fase | Esfuerzo | Depende de | Riesgo |
| --- | --- | --- | --- |
| 0 Higiene | ½ d | — | Bajo |
| 1 Weekend bars | 1 d | 0 | Medio (cambia señales) |
| 2 engine_validator | ½–1 d | 0 | Bajo |
| 3 Exit-at-time | 1–2 d | 0, 2 | Medio (hot loop numba) |
| 4 Port ARB | 1–2 d | 1, 3 | Alto (paridad de señales) |
| 5 Gauntlet ARB | 2–3 d | 4 | Decisivo |
| 6 Vectorbt fixes | ½ d | 1 | Bajo |
| 7 Costos/multiplicidad | ½–1 d | 4 | Bajo |
| 8 Veredicto | ½ d | 5, 7 | — |

**Total estimado: ~8–11 días de trabajo efectivo** con Claude Code, en tu Ryzen 5. Las corridas MCPT de 1000 permutaciones sobre ticks son lo más pesado; considerá correrlas de noche o precomputar barras.