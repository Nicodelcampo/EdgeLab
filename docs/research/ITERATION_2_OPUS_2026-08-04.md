# Iteración 2 — Opus: inspección de código y refutación de la Iteración 1

**Fecha:** 2026-08-04  
**Rama:** `work/repository-research-iterations`  
**Base:** `cf03f34205e45946afc70c8164c8023881425987`  
**Mandato:** refutar, no expandir. Inspeccionar código, no README.  
**Outcomes de EdgeLab consultados:** no.

## Archivos inspeccionados

| Repositorio | Ruta | Blob SHA |
| --- | --- | --- |
| freqtrade/freqtrade | `freqtrade/optimize/analysis/lookahead.py` | `585bd05d5069879298e276b4151c14beba5afac3` |
| freqtrade/freqtrade | `freqtrade/optimize/analysis/recursive.py` | `735c240b069c2726f6a20e4e35036a2cdc575687` |
| TauricResearch/TradingAgents | `tradingagents/agents/utils/memory.py` | `ff9e94579bfcf256712c6daf0fd4d0fbbb9290c1` |
| hummingbot/hummingbot | `hummingbot/strategy_v2/executors/executor_base.py` | `fa593e8a27ee02b2a4ad804ddc611aca5fef940a` |
| nautechsystems/nautilus_trader | `crates/indicators/src/indicator.rs` | `7a82e5035ef87fc39f41f0e013fdf6a2653ab3b2` |

Commits de origen: `442f0b8fb4c646f22bd9d84c91c1724b904dd289` (freqtrade), `a33fd4c0f134485a43553a2c23a63cb14adbd88f` (TradingAgents), `2bfaccc48dd49e71a5b6d9b3011808e127dd00cd` (hummingbot), `91d057f7a06b3d0b028b38924896c1100ef4dfdf` (nautilus_trader).

## Veredicto de la iteración

> **La Iteración 1 acertó en la topología de tres planos y se equivocó en la calidad atribuida a los instrumentos externos. Freqtrade no aporta gates; aporta la idea de dos gates cuya implementación concreta es estadísticamente débil y reproduce el modo de falla que ya destruyó la credibilidad de `tickbar_diag.py`.**

Si EdgeLab hubiera portado esos analizadores tal como están, habría obtenido un segundo instrumento capaz de emitir “no bias detected” por construcción en los casos que más importan.

---

## 1. Freqtrade `lookahead.py` — el gate es condicional a la población de trades

### Mecánica real

1. `fill_full_varholder()` corre el backtest completo.
2. Se itera `full_varHolder.result["results"]`, es decir **trades ejecutados**.
3. Para cada trade se reconstruyen dos corridas truncadas: una hasta la vela de entrada más una, otra hasta la de salida más una.
4. `report_signal()` verifica si la señal sobrevive en la corrida truncada.
5. `analyze_indicators()` compara indicadores entre corrida completa y truncada.

Esto confirma que el núcleo conceptual es un **prefix/truncation test**, igual que el gate propuesto en la Iteración 1.

### Defectos materiales encontrados

#### D1 — El poder de detección depende de que existan trades

```python
found_signals: int = self.full_varHolder.result["results"].shape[0] + 1
if found_signals >= self.targeted_trade_amount: ...
else:
    logger.info(f"found {found_signals} trades which is less than minimum_trade_amount ...")
    return
```

El análisis se cancela cuando hay pocos trades. Para EdgeLab esto es letal: los detectores viven en colas. Un indicador con 20 eventos en el universo elegible sería declarado “no analizable”, y en el flujo del CLI eso se comunica como falta de datos, no como ausencia de garantía. Además `found_signals` suma `+ 1` a un conteo de filas, lo cual infla el conteo en uno sin justificación visible.

#### D2 — Los sesgos que no producen trades son invisibles

El barrido recorre trades, no barras. Un look-ahead que altera un indicador en barras donde nunca se abrió posición no aparece. En EdgeLab, la atribución de eventos a barras —exactamente el defecto de TICKBAR-001— puede ser errónea sin cambiar ninguna decisión de entrada.

#### D3 — `force_exit` se excluye para evitar falsos positivos

```python
if "force_exit" in result_row["exit_reason"]:
    ... continue
```

La exclusión es razonable para el dominio de Freqtrade, pero crea un subconjunto sistemáticamente no auditado. EdgeLab ya cometió el error inverso al proponer excluir días duplicados conocidos: excluir la clase incómoda no prueba limpieza del resto.

#### D4 — Comparación por desigualdad exacta de flotantes

```python
if self_value != other_value:
```

No hay tolerancia relativa ni absoluta. Cualquier diferencia de último bit —orden de reducción, longitud de ventana, acumulación incremental— se reporta como *look ahead bias*. En un motor de ticks con acumuladores incrementales esto produce ruido masivo, y el ruido termina entrenando al operador a ignorar el gate.

#### D5 — Sólo se inspecciona la primera fila del diff

```python
compare_df_row = compare_df.iloc[0]
self_value = compare_df_row.iloc[col_idx]
```

El reporte registra únicamente nombres de columnas y los valores de la primera fila divergente. No hay magnitud, ni ubicación temporal, ni fracción de barras afectadas. Es precisamente la métrica que EdgeLab necesita cuantificar: `81,78%` frente a `3,91%` son diagnósticos distintos, no el mismo booleano.

#### D6 — Se reconstruye el estado con `deepcopy` de configuración, no con manifest

`prepare_data()` clona la configuración y vuelve a instanciar `Backtesting`. No hay hash de dataset, ni commit, ni firma de entorno. La corrida truncada y la completa son comparables por confianza, no por procedencia verificable.

### Consecuencia para EdgeLab

Se conserva el concepto y se rechaza la implementación. El gate propio debe:

- recorrer **barras/eventos**, no trades;
- correr aunque haya cero eventos, devolviendo `INSUFFICIENT_POWER` explicitado como ausencia de garantía;
- usar tolerancia declarada y separar “diferencia numerérica” de “diferencia estructural”;
- reportar fracción afectada, magnitud y primera divergencia;
- no excluir clases incómodas sin una decisión registrada.

---

## 2. Freqtrade `recursive.py` — el gate mide un solo punto

### Mecánica real

```python
base_last_row = self.full_varHolder.indicators[pair_to_check].iloc[-1]
for part in self.partial_varHolder_array:
    part_last_row = part.indicators[pair_to_check].iloc[-1]
```

- Se comparan corridas con distintos `startup_candle` —por defecto `[199, 399, 499, 999, 1999]`— tomando **exclusivamente la última fila**.
- Se usa **un solo par**: `backtesting.pairlists._whitelist = [self.pair_to_used]`.
- El chequeo adicional de look-ahead compara **un único instante**, a diez velas del inicio.

### Defectos materiales

#### D7 — `break` al primer acierto interrumpe el barrido

```python
else:
    logger.info("No variance on indicator(s) found due to recursive formula.")
    break
```

Si un `startup_candle` coincide con la corrida completa, el bucle termina y no se evalúan los restantes. Un indicador puede ser estable con 199 velas y catastróficamente inestable con 1999 sin que el instrumento lo reporte. Es una **rama de silencio**, hermana del `cuts_ok` inalcanzable de `tickbar_diag.py`.

#### D8 — Un punto temporal no caracteriza inestabilidad

Medir `iloc[-1]` supone que la sensibilidad al warmup es homogénea en el tiempo. En una serie con memoria larga y cambios de régimen —el caso documentado de EdgeLab— la última barra puede haber olvidado la diferencia mientras el interior de la serie sigue divergiendo.

#### D9 — Diferencia relativa sin protección de escala

```python
diff = round((values_diff_other - values_diff_self) / values_diff_self, 12)
```

El guard previo exige que ambos valores sean *truthy* y numéricos, de modo que un valor base de `0` cae en la rama `"nan"` y se pierde información. Con valores cercanos a cero la razón explota y produce números sin significado.

#### D10 — Un solo instrumento

El análisis reduce el whitelist al primer par. Para EdgeLab, cuya campaña exige cobertura por contrato y sesión, un gate que mide un instrumento no puede autorizar una familia.

### Elemento adoptable

```python
if self._strat_scc < 1:
    raise ConfigurationError(...)
```

Exigir declaración explícita de warmup y fallar cerrado si falta es correcto y debe entrar en `IndicatorSpec v0` como campo obligatorio.

---

## 3. TradingAgents `memory.py` — la contaminación es estructural, no accidental

### Confirmación dura

```python
def get_past_context(self, ticker, n_same=5, n_cross=3) -> str:
    entries = [e for e in self.load_entries() if not e.get("pending")]
```

Sólo se inyectan al prompt las entradas **resueltas**, y una entrada se resuelve en `update_with_outcome()` con:

```python
raw_pct = f"{raw_return:+.1%}"
alpha_pct = f"{alpha_return:+.1%}"
```

Es decir: el contexto que el modelo recibe está condicionado por retornos realizados y por una reflexión escrita después de conocerlos. La Iteración 1 lo sospechó desde el README; el código lo confirma sin ambigüedad. **Cualquier reutilización de este componente en la fase generativa de EdgeLab constituiría acceso a outcomes.**

### Defecto adicional no previsto

```python
def _apply_rotation(self, blocks): ...
    if is_resolved and to_drop > 0:
        to_drop -= 1
        continue
```

La rotación **descarta las entradas resueltas más antiguas** y conserva las pendientes. Como bitácora operativa es defendible; como registro científico es inadmisible: elimina justamente la evidencia cerrada, incluidos los resultados negativos que EdgeLab se comprometió a preservar.

### Otros límites

- El almacén es Markdown append-only delimitado por `<!-- ENTRY_END -->`; la identidad de una entrada es una línea de texto entre corchetes.
- No hay hash de contenido, ni commit, ni modelo, ni temperatura, ni versión de prompt.
- La escritura atómica por `tmp_path.replace()` protege contra corrupción, no contra pérdida semántica.
- La deduplicación de pendientes es un `startswith`/`endswith` sobre texto.

### Consecuencia

Del patrón de roles se conserva la idea; de la memoria no se conserva nada. El `ClaimEvidenceRecord` de EdgeLab debe ser content-addressed, inmutable y sin rotación destructiva.

---

## 4. Hummingbot `executor_base.py` — taxonomía útil, runtime inadecuado

### Mecánica real

```python
async def control_loop(self):
    await self.on_start()
    while not self.terminated.is_set():
        try:
            await self.control_task()
            self.evaluate_max_retries()
        except Exception as e:
            self.logger().error(e, exc_info=True)
        finally:
            await asyncio.sleep(self.update_interval)
```

El executor es un bucle asíncrono con `update_interval` por defecto de 0,5 s, alimentado por eventos de conector vía `SourceInfoEventForwarder`, y sellado con `self._strategy.current_timestamp`.

### Refutación de la Iteración 1

La Iteración 1 sugirió usarlo como inspiración de “máquina de estados auditable”. El código muestra que **no es una máquina de estados determinista**: es un poller acoplado a reloj de pared y a callbacks de exchange, con excepciones capturadas y registradas sin abortar. Un instrumento así no puede servir de oráculo reproducible. La afirmación queda reducida a la taxonomía.

### Lo que sí aporta

```python
self.close_type = CloseType.POSITION_HOLD if held_orders else CloseType.FAILED
```

`force_stop_with_position_hold()` formaliza una categoría que EdgeLab no tiene: **terminación forzada con exposición residual persistida**. En términos de EdgeLab, un corte de corrida no puede colapsar en éxito o fracaso; debe distinguir:

- cierre normal;
- abstención declarada;
- fallo;
- residual persistido para reconciliación posterior.

Es exactamente la distinción que faltó cuando una corrida quedó truncada con `EXIT=1` sin dejar output.

### Límite adicional

```python
def get_net_pnl_quote(self) -> Decimal:
    raise NotImplementedError
```

La contabilidad no está en la base: cada executor la implementa. La comparabilidad entre executors no está garantizada por el framework. Trasladado a EdgeLab: la métrica económica debe vivir en un contrato único, no en cada detector.

---

## 5. NautilusTrader `indicator.rs` — el trait no garantiza causalidad

### Mecánica real

```rust
pub trait Indicator {
    fn name(&self) -> String;
    fn has_inputs(&self) -> bool;
    fn initialized(&self) -> bool;
    fn handle_delta(&mut self, delta: &OrderBookDelta) { panic!(...) }
    fn handle_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> { anyhow::bail!(...) }
    fn handle_trade(&mut self, trade: &TradeTick) { panic!(...) }
    fn handle_bar(&mut self, bar: &Bar) { panic!(...) }
    fn reset(&mut self);
}
```

### Hallazgos

#### H1 — La causalidad no está en la interfaz

El trait es push-based: recibe eventos y muta estado. No expone `event_time`, `available_time`, latencia de disponibilidad ni abstención. La corrección temporal la impone el motor y su reloj, no el indicador.

**Consecuencia directa sobre R5:** un micro-oráculo Nautilus puede testear determinismo y orden de eventos del motor, pero **no puede certificar ausencia de look-ahead en una especificación**. Si EdgeLab espera eso del spike, el spike está mal planteado.

#### H2 — Modelo de error inconsistente

`handle_quote` devuelve `anyhow::Result<()>`; `handle_delta`, `handle_trade`, `handle_bar` y `handle_book` hacen `panic!`. Un indicador que reciba un tipo de dato no soportado aborta el proceso. Para un oráculo diagnóstico esto significa que una incompatibilidad de tipos destruye la corrida completa en vez de emitir una abstención registrada.

#### H3 — `initialized()` y `reset()` sí son contratos valiosos

Exigir un predicado explícito de “warmup completo” y un `reset()` obligatorio son dos requisitos que `IndicatorSpec v0` debe heredar. Sin `initialized()`, la frontera entre cola inestable y valor válido queda implícita.

#### H4 — El indicador no declara qué consume

No hay metadata de inputs requeridos: se descubre por panic en tiempo de ejecución. EdgeLab necesita lo contrario: declaración estática verificable antes de ejecutar.

---

## Actualización de hipótesis

| Hipótesis | Estado tras Iteración 2 | Razón |
| --- | --- | --- |
| R1 — DSL pequeña suficiente | Abierta | No probada por inspección externa |
| R2 — Separar proposer y compiler | Reforzada | La memoria de TradingAgents demuestra que sin firewall el plano generativo se contamina por diseño |
| R3 — AST canónico detecta duplicados | Abierta | Ningún repositorio inspeccionado implementa deduplicación semántica de indicadores |
| R4 — Gates estilo Freqtrade detectan futuro y recursividad | **Parcialmente refutada** | El concepto sirve; la implementación tiene rama de silencio, un solo punto, un solo par, tolerancia cero y dependencia de trades |
| R5 — Micro-oráculo Nautilus reproduce una especificación | **Reformulada** | Puede validar determinismo y orden de eventos; no puede validar causalidad de la especificación |
| R6 — Nueva: el registro de evidencia debe ser inmutable y content-addressed | Apoyada | La rotación destructiva de TradingAgents muestra el modo de falla |
| R7 — Nueva: el resultado de corrida necesita cuatro estados, no dos | Apoyada | `POSITION_HOLD` vs `FAILED` de Hummingbot es la analogía del residual persistido |

## Matriz de ataques para el compilador

Cada ataque debe tener un spike-in que el gate esté obligado a detectar.

| # | Ataque | Mecanismo | Detectado por |
| --- | --- | --- | --- |
| A1 | Futuro directo | referencia a barra `t+k` | prefix test por barra |
| A2 | Futuro indirecto por normalización | escala por máximo/desvío de toda la serie | prefix test + auditoría de reducciones globales |
| A3 | Futuro por suavizado bidireccional | filtro centrado o `bfill` | prefix test + prohibición de operadores no causales |
| A4 | Futuro por resample/etiqueta de barra | timestamp de cierre usado como disponible | auditoría `event_time` vs `available_time` |
| A5 | Futuro por frontera de sesión | estado que cruza el corte de sesión | test de frontera con reset explícito |
| A6 | Inestabilidad de warmup | recursión infinita tipo EMA sin `initialized()` | barrido completo de warmup, sin `break` |
| A7 | Dependencia de orden de eventos con timestamps empatados | desempate implícito | replay con permutación de empates |
| A8 | Divergencia de atribución con cortes idénticos | evento asignado a barra vecina | comparación OHLCV + ledger, no conteos |
| A9 | No determinismo por punto flotante | orden de reducción variable | doble corrida con tolerancia declarada |
| A10 | Fuga por deduplicación | especificación renombrada que ya fue refutada | AST canónico y catálogo de muertes |
| A11 | Fuga por selección de familia | ampliar presupuesto tras ver conteos | presupuesto sellado antes del censo |
| A12 | Fuga por memoria del agente | reinyección de resultados previos | firewall de contexto y auditoría de prompt |

Criterio de muerte del compilador: si la batería A1–A9 no se detecta al 100% sobre spike-ins sintéticos, la fábrica no se abre.

## Correcciones al ranking de la Iteración 1

1. **Freqtrade baja de “fuente de gates” a “fuente de dos ideas de gate”.** Su código no debe portarse.
2. **Hummingbot baja de “lifecycle auditable” a “taxonomía de cierre y residual”.**
3. **NautilusTrader se mantiene primero, con alcance recortado:** determinismo y orden de eventos, no causalidad de especificaciones.
4. **TradingAgents baja a “patrón de roles”, con prohibición explícita de su capa de memoria.**
5. Backtrader, FinRL, CCXT y Polymarket CLI no fueron inspeccionados en esta iteración y conservan estado provisional. No se les asigna crédito adicional.

## Límites de esta iteración

- Se leyeron cinco archivos, no cinco proyectos. Las conclusiones aplican a los componentes inspeccionados.
- No se ejecutó ninguno de los analizadores; las fallas se derivan de lectura de código, no de reproducción empírica.
- No se inspeccionaron el reloj, el motor de eventos ni el matching engine de NautilusTrader; H1 se apoya en la interfaz del indicador, no en el runtime completo.
- No se revisó el grafo ni el checkpoint de TradingAgents; la conclusión sobre contaminación se apoya en la capa de memoria, que es suficiente para el veredicto.

## Handoff — Iteración 3 (Opus)

Con la crítica anterior ya cerrada, la tercera iteración debe producir contratos, no prosa:

1. `IndicatorSpec v0` con campos obligatorios: inputs declarados, operadores permitidos, lookback, warmup, predicado `initialized`, reset de sesión, emisión, abstención, `event_time`/`available_time`, complejidad, familia, parent y hash.
2. Forma canónica y hash semántico, con reglas de normalización algebraica mínimas.
3. Sandbox de capacidades: lista blanca de operadores, prohibición de reducciones globales y de acceso a índices futuros.
4. Especificación de los doce spike-ins A1–A12, con resultado esperado y motivo de muerte.
5. Reporte de gate con estados `PASS`, `FAIL`, `ABSTAIN` e `INSUFFICIENT_POWER`, prohibiendo el colapso a booleano.
6. Contrato de corrida con cuatro terminaciones y residual persistido.
7. Plan de implementación acotado, sin agentes y sin outcomes.

Prohibiciones que se mantienen: no portar código de Freqtrade, no reutilizar memoria de TradingAgents, no migrar el motor de EdgeLab a Nautilus, no abrir outcomes, no tocar `bars.build_tick_bars`.
