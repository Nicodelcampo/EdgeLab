# Auditoría de debilidades frente al referente + tres defectos de gates — 2026-08-15

Acta de la sesión de auditoría del 15-ago (chat, sin créditos restantes del auditor).
Se registra acá para que no viva sólo en un chat que se pierde.

**Estado de verificación**: los hallazgos A1/A2/A3, B y C los reportó el auditor y
**fueron re-verificados contra el código desde la máquina local** antes de asentarlos.
Cada uno cita archivo y línea. Lo que no pude verificar queda marcado como tal.

---

## Parte 1 — Debilidades frente al referente

El referente no es «tener un lab limpio». Es **encontrar un edge válido y aplicable que
gane neto en una cuenta real**. Debilidad = lo contrario de esa jerarquía.

### 1. Cero expectativa neta

`EDGES_DISCOVERED.md` dice: ninguno. H1 murió en **−2,47 ticks/evento** (bruto +0,30,
fricción −2,77). El imán de BigTrap2 está cerrado. El prerange no es edge. El ledger de
promoción (`promotion_registry.jsonl`) no existe.

Todo el trabajo de esta semana —re-corte, `verify_tree`, store, P-25…P-34— **no mueve
el ítem 1 de la jerarquía**. El propio referente lo dice: paridad exacta no es edge;
zona bien guardada no es edge.

### 2. Sin validez OOS económica

El holdout está bien sellado (eso es fortaleza). El problema es el complemento: **no hay
candidato G3 al que abrirlo**. Mientras tanto la V1 de Kaggle sí tiene holdout físico.
Se protegió el sello y se filtró por otro lado.

### 3. La robustez está escrita, no ejercida

G2 existe, se corrigió (G2-A1) y se testeó sobre sintéticos con verdad conocida **antes**
de ver un ganador. Ninguna campaña real lo corrió. `APPROVED_G2_CONTRACT_SHA256S` está
vacío: nadie puede materializar `statistically_supported`. L3 PreRange salió inemitible
por inanición de placebos.

**Abrir siete indicadores al store antes de una campaña formal es lo contrario de G2**:
cada config se cobra al `N_eff`.

### 4. No hay ejecutable

No hay reglas completas de entrada/salida/sizing/kill switch. No hay paper ni shadow.
W7 (costos por instrumento) sigue vacío; H1 usó 2,768 ticks de 6E y **está prohibido
transportarlos**. Sin costos propios, G3 es teatro.

### 5. No hay control de riesgo de despliegue

No hay candidato live, así que no hay DD live ni kill switch. El riesgo real hoy es otro:
**research risk** — gastar el presupuesto de hipótesis en infraestructura.

### 6. Los medios se volvieron el fin

El ritual «aporte al referente» se cumple en cada commit y a menudo describe un hash. F9
está pausada hasta «una campaña formal sobre los 5 indicadores»; esa campaña no corrió y
se abrió un programa de 7. `EDGES_DISCOVERED.md` todavía llama al imán «hipótesis
provisional» **después de F2.8**. El acta D-1…D-8 declara cierres que `PENDIENTE.md` no
asienta. Mismo modo de falla de siempre: dos lecturas internamente coherentes.

### Del propio corpus

- **Sesgo de diseño**: casi todo el corpus de BigTrap2 midió *el toque*. Creación,
  invalidación, estado continuo y toque n-ésimo quedaron heredados, no elegidos.
- **`sequence` no es secuencia de exchange** (verificado en 1.015.587.419 filas, P-28).
  Cualquier microestructura que asuma orden intra-timestamp no está soportada.
- **F4 constitucional nunca se corrió** — la pregunta de máxima potencia: ¿cambia la
  distribución de retornos dado el estado?

---

## Parte 2 — Fortalezas (lo que sí sirve al referente)

No son cortesía: sin ellas esto sería otro backtester más.

1. **Muertes honestas.** H1, imán, prerange: registradas, sin relajar gates. Es
   literalmente el ítem metodológico del referente («maximizar la probabilidad de
   rechazar falsos»).
2. **Holdout en código, no en un README.** El corte UTC ingenuo se midió (871 filas en
   el parquet ancla; 101.364 sobre los 11 en cuarentena) y se cerró.
3. **Cuatro clases de validez definidas antes de tener un ganador.** G2 escrito y
   enmendado sobre sintéticos, en los dos sentidos.
4. **Target-free real** en la construcción de kernels. El store as-of existe.
5. **Censo de lo no medido.** Tras el sesgo del toque, el event-space quedó escrito.
6. **Fail-closed** en licencia, holdout, `verify_tree`, re-corte: prefieren rojo ruidoso
   a verde falso.
7. **Referente explícito + ritual de aporte.** El problema es incumplirlo, no no tenerlo.

**Lectura corta**: el proyecto es **fuerte en no engañarse y débil en acercarse a una
cuenta**. Esa distancia no se recorta con otro árbol de parquets.

---

## Parte 3 — Tres defectos de gates, verificados contra el código

El auditor primero reportó que `coverage.py` no se llamaba desde ningún módulo. **Él
mismo lo refutó** leyendo el código, y lo confirmo: `store.publish_run()` termina en
`_cov.propagate_coverage(root)` (`store.py:393-400`, con `propagate_coverage=True` por
default), y es esa función la que escribe `parity_state="parity_covered"`.

Lo que apareció en su lugar es peor.

### A1 · Una paridad con WARN se registra como EXACTA

**Verificado**: `edgelab/bridge/store.py:268-276`

```python
def _parity_state(parity):
    ...
    if gate == "FAIL":
        return "parity_failed"
    if gate in ("PASS", "WARN"):
        return "parity_exact"
```

`WARN` y `PASS` colapsan al mismo estado. Una paridad con advertencias queda sellada
como `parity_exact` e **indistinguible de una limpia**.

**Por qué importa hoy, con un caso concreto**: la paridad de HFTZones2 del 15-ago dio
`WARN` sin frontera de madurez (31 `STATE_ORDER_DIFF` + 4 `FEATURE_DIFF`) y `PASS` con
ella. Las dos corridas existen y están publicadas en
`docs/research/paridad_hftzones2_12d_2026-08-15.json`. **Si se hubiera publicado la
primera al store, habría quedado marcada `parity_exact`.** El gate no habría mentido
por malicia: colapsa dos veredictos distintos en una etiqueta.

Es de la misma familia que P-34: **la etiqueta no se deriva del contenido**.

**Decisión de Nico** — es semántica de gating, nadie más la toca.

### A2 · Dos semánticas de «covered» en el mismo archivo

**Verificado**: `edgelab/bridge/coverage.py`

El docstring y las matrices dicen que `parity_covered` exige que **todas las ramas**
estén cubiertas, vía `branches_of` (l. 24), `config_branches` (l. 35), `is_covered`
(l. 50). Pero `propagate_coverage` (l. 131+) **no usa ninguna de las tres**: decide con
`coverage_blockers(s, man)` (l. 176-180), que compara identidad dura + igualdad de params
salvo los coverage-neutral.

`is_covered` sólo aparece referenciada **dentro de su propia definición** (l. 53). La
contabilidad de ramas es **código muerto respecto de la propagación**.

Riesgo: alguien lee el docstring, cree que las ramas se verifican, y no.

### A3 · `parity_covered` es inalcanzable para 4 de 5 kernels

**Verificado**: `edgelab/bridge/coverage.py:64-71`

```python
COVERAGE_NEUTRAL = {
    "Gaps2": {...},
}
```

**Una sola entrada.** Para los otros cuatro kernels `_neutral()` devuelve conjuntos
vacíos, así que **cualquier** diferencia de params bloquea la cobertura.

Consecuencia dura: **la decisión D-6 («paridad representativa» para el trío P-16) no
tiene camino ejecutable** para 4 de 5. No por falta de cableado —el cableado está— sino
por falta de entradas justificadas en la lista blanca. El consumo formal en G2+ exige
`parity_exact` o `parity_covered`; hoy los indicadores «representativos» quedan fuera.

**Decisión de Nico**: cargar entradas en `COVERAGE_NEUTRAL` es ampliar qué diferencias
se consideran irrelevantes para la paridad. Cada entrada necesita justificación escrita
por parámetro, como la de `Gaps2` (que cita §8.3.1 para cada campo).

### B · Tres fuentes se contradicen sobre VolTicksPOC2

**Verificado parcialmente** (los archivos existen y dicen lo que sigue; no verifiqué
cuál tiene razón):

| Fuente | Dice |
| --- | --- |
| `docs/parity_coverage/VolTicksPOC2.md:8` | **PASS — 23/23, 0 diffs** |
| `docs/nt8_bridge.md` (tabla «Paridad real NT8») | pendiente |
| `docs/parity_coverage/README.md` | «ningún oráculo real existe todavía» |

Los tres no pueden ser ciertos. El auditor corrigió además su propia afirmación previa:
hay **al menos dos** oráculos reales, no uno.

**Pendiente**: reconciliar con archivos a la vista, no de memoria. Los conteos de suite
de `nt8_bridge.md` datan del 24-jul y pueden estar viejos.

### C · `N_eff` no existe como mecanismo

`max_configs` es un techo duro, no un presupuesto de investigación. `docs/nt8_bridge.md`
lo dice literal: «no existe como mecanismo automático todavía». Confirma el agujero del
capítulo 2 de la estructura de investigación.

### Dos hallazgos operativos

- **El campaign runner no tiene resume**: siempre recomputa. `publish_run` es idempotente,
  así que es seguro pero caro.
- **Gaps medidos en 6E**: «115 gaps de 2t + 2 de 3t + 0 de ≥5t» en 2 días. El supuesto de
  **1 tick de slippage por pata probablemente sea optimista en 6E**. Toca directamente al
  escenario base del simulador.

---

## Parte 4 — Hallazgo de método (explica errores previos del auditor)

La rama **default del repo es `cde6d93a75…` y no tiene `docs/` en absoluto**. Toda
lectura vía MCP sin `ref` explícito cae ahí y contesta «no existe».

Por eso el auditor afirmó que `docs/data_contract.md` y `docs/promotion_registry.jsonl`
no existían: **eso queda sin verificar, no negado**. Registrado acá con su motivo en vez
de borrado, que es la práctica correcta.

Consecuencia de reparto: el auditor **sí** puede leer código con `ref` explícito, así que
buena parte de lo que se le había asignado a Claude no le correspondía.

---

## Parte 5 — Soluciones, contrastadas contra literatura

La literatura que el propio contrato cita va en la misma dirección: Bailey / López de
Prado (cada trial extra sube el PBO; el DSR se desinfla con el `N_eff` de **todo lo
intentado**, no de lo publicado) y Harvey 2017 (tests no reportados + sin ajuste por
múltiples pruebas = resultados que no se sostienen).

Por eso **no** es solución «terminar P-25…P-34 y después research»: eso agranda la
debilidad 3.

| Debilidad | Qué hacer | Qué NO |
| --- | --- | --- |
| Sin neto | Una familia: `aVolClusterPOI` sola, target-free, nulo propio | Campaña de 7 indicadores al store como si fuera descubrimiento |
| Sin OOS | Holdout cerrado hasta G3. Borrar la V1 de Kaggle | «Abrir un poquito» o recortar julio |
| Robustez ociosa | Manifiesto de campaña, `N_eff` declarado **antes**, G2 sobre ese objeto. Hashear G2-A1 en la allowlist | Mergear `g2-a1-*` al vuelo; relajar L3 |
| No ejecutable | W7: costos por instrumento, desglosados, antes de cualquier P&L | Reusar 2,768 ticks de 6E |
| Medios = fin | F4 constitucional (manifiesto + OK) antes de `research-v3` / store masivo. Alinear board, `EDGES_DISCOVERED` y acta **en el mismo commit** | Medir progreso en GiB podados o P-NN cerrados |

### Orden operable

1. **Board = acta** (o el acta es ficción).
2. **Costos** de ES/NQ/YM/6E por escrito (W7).
3. **Manifiesto F4** de `aVolClusterPOI` — una hipótesis, event-space enumerado, cómo se
   refuta.
4. Si F4 sobrevive: **una** monetización, G1 → G2.
5. Store / v3 / paridad HFT / aVolCell: **higiene, no camino crítico**.

`research-v3` y el fix de P-33 están bien. **No son el referente.**

---

## Parte 6 — Números duros del deep research

Detalle completo en `docs/research/DEEP_RESEARCH_EDGES_CUENTA_2026-08-15.md` (`67131b0`).
Lo que cambia decisiones:

**Siete configs fabrican un Sharpe 1 falso.** Tras 7 configuraciones se espera un backtest
de 2 años con SR anualizado > 1 cuando el verdadero es 0. Ejemplo ADIA 2024: SR 1,0 / 5
años / p=0,02 **si era un trial**; con 10 trials y eligiendo el mejor, la esperanza del
máximo ≈ 0,69, el corte 1,12 y p ≈ 0,88 — no significativo. Harvey: el mejor long-short
por las 3 letras del ticker da t=3,23. **t>3 no basta.**

> El pack de 7 indicadores × contratos × `bar_spec` **es exactamente ese experimento**.

**En futuros el IC tiene que ser feo.** `IR ≈ IC × √Breadth`, con Breadth = apuestas
independientes, no filas:

| Configuración | IC mínimo para IR=1 |
| --- | --- |
| 1 instrumento, 1 forecast/día | ≈ 0,06 |
| 1 evento/sesión | ≈ 0,14 |
| 4 instrumentos poco correlacionados | ≈ 0,03 |

Eso **es** F4: Spearman(estado, retorno) antes de SL/TP. Si IC≈0, no hay G2. Y `n=424`
de H1 **no es breadth 424**.

**Costos reales** (exchange+NFA, no-miembro, por lado — IBKR/TradeStation):

| Instrumento | Tick $ | RT exch+NFA | En ticks |
| --- | --- | --- | --- |
| ES | 12,50 | $2,78 | ≈ 0,22 t |
| NQ / YM | 5,00 | $2,78 | ≈ 0,56 t |
| 6E | 6,25 | $3,22 | ≈ 0,52 t |
| MNQ | 0,50 | — | 0,70 t/lado — **el micro es más caro en ticks** |

H1 usó 2,768 t de 6E ≈ $17,30 RT. En ES eso serían $34,60 contra $2,78 de exchange. El
escenario base (1 tick de slip por pata) en ES ya son ~$28 RT. **Un bruto de 0,3 ticks
muere en cualquier índice.**

**Triple barrera + meta-label, no T=34.** TP y SL en volatilidad, expiración por barras de
actividad, etiqueta = qué toca primero. H1 fue close-through o fin de sesión, sin TP/SL;
con 96% de ruptura, el −2,47 era previsible. Meta-label: (1) hay setup, alto recall;
(2) ¿este se toma? **F4 → filtro, no F4 → grilla de stops.**

**Un walk-forward no alcanza**: WF / CPCV / Monte Carlo con proceso generador. Y antes de
cualquier backtest, **grafo causal**: si no se dibuja por qué el mercado pagaría, no se
corre. Finanzas prefiere FWER (ni un falso) a FDR.

**Paper → 1 contrato. Si live ≠ research, se mata.** No se tunea el stop. Un bruto
SR 0,31 puede ser −0,46 neto: el enemigo es el turnover.

**Qué NO copiar**: 4 millones de alphas, costos AQR de equity institucional, FracDiff/ML
como capítulo 1, `t>3` como sello.

---

## Parte 7 — Reparto de trabajo

**De Nico (nadie más):**
- **A1** y **A3**: las dos decisiones de semántica de gates.
- Estado de cuenta del broker para W7.
- OK del manifiesto F4 (sin eso F4 no arranca).
- Borrar la V1 de Kaggle.

**De Claude (máquina local):**
- Esquema real de un parquet: **¿existen bid/ask?** Decide si el spread se **mide** o se
  asume, y sin eso el spec del simulador no cierra.
- `propagate_coverage(root, dry_run=True)` contra el store real, para ver los estados de
  paridad **verdaderos** en vez de discutirlos entre documentos.
- Spread empírico, sólo si hay bid/ask, pre-holdout.
- El commit que iguala board, `EDGES_DISCOVERED.md` y el acta.

**Del auditor:** reconciliación de B (`BigTrap2.md`, `aVolCellPOI2.md`, medición del
01-ago, §6-§8 del contrato).

---

## Parte 8 — T1 y spread empírico: HECHO (2026-08-15)

**T1 resuelto: los parquets SÍ traen `bid_ticks` y `ask_ticks`.** Esquema de 13 columnas
verificado. Consecuencia: **el spread se mide, no se asume**, y el spec del simulador
puede cerrar con dato propio.

Medición inmediata sobre `research-v2` (target-free, sin holdout, sin outcomes):

| Instrumento | n (quotes) | media | mediana | p90 | 1t | 2t | 3t |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6E 06-26 | 5.554.201 | **1,141 t** | 1 t | 2 t | 89,0 % | 9,3 % | 1,1 % |
| ES 06-26 | 73.268.494 | **1,153 t** | 1 t | 1 t | 90,8 % | 6,8 % | 1,3 % |
| NQ 06-26 | 34.203.535 | **3,817 t** | 3 t | 7 t | 11,7 % | 26,3 % | 25,6 % |
| YM 03-26 | 6.460.091 | **1,899 t** | 2 t | 3 t | 41,4 % | 42,4 % | 11,0 % |

**El hallazgo que cambia el escenario base**: la sospecha registrada era que «1 tick de
slippage por pata es optimista **en 6E**». La medición lo **refuta para 6E** (1,141 t,
89 % de las veces exactamente 1 tick) y descubre el problema donde nadie lo estaba
buscando: **NQ tiene spread medio de 3,817 ticks**, más de 3× el de ES, con p90 = 7 t y
sólo 11,7 % de quotes a 1 tick.

Cruzado con la tabla de costos de exchange (NQ: $2,78 RT ≈ 0,56 t), **la fricción de NQ
está dominada por el spread, no por la comisión**: cruzar el spread una vez ya cuesta
~3,8 t contra 0,56 t de exchange. Un escenario base uniforme de «1 tick por pata» para
todos los instrumentos **subestima NQ en un factor ~4**.

Esto refuerza, con dato propio, la regla que ya estaba escrita: **no transportar costos
de ejecución entre instrumentos**. Y agrega una consecuencia nueva: tampoco transportar
el **escenario de slippage**.

**Lo que falta para cerrar W7** (no es medición, es de Nico): el resumen de comisiones
del broker. La parte de exchange ya está tabulada; la de spread, ahora también.

---

## Éxito de este ciclo

**Un objeto en G0→G1, o una muerte F4/G1 registrada.** Dejar de medir progreso en P-NN
de infraestructura.
