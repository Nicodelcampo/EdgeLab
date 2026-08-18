# H-Z2A — Manifiesto numérico (v1, 2026-08-18)

- **Estado:** `DRAFT_FOR_STOP` — **no se ejecuta nada con outcomes hasta el STOP explícito de Nico.**
- **Versión:** `hz2a_manifiesto_numerico_v1`
- **Línea que manda:** `docs/research/H_Z2A_V4_DEPURACION_EPISTEMICA_Y_DISENO_FINAL_2026-08-16.md` (v4; blob `44a996032b72004d028a3e92b585a0d72347ccca`)
- **Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
- **Orden vigente:** `docs/audits/ENTRADA_019_ORDEN_CLAUDE_CENSO_HZ2A_2026-08-18.md`
- **Insumo de población, verificado:** `docs/research/censo_hz2a_superficie_2026-08-18.json` (blob `8bd29ed95b1756d6a11dee7c5d6a1b69c5c09144`; verificación del auditor en `docs/audits/ENTRADA_021_VERIFICACION_CENSO_Y_ASIGNACION_2026-08-18.md`: runner ciego por construcción leyendo el código, artefacto consistente al dígito en 120/120 celdas)
- **Firewall:** outcomes no leídos · P&L no leído · holdout sellado (trade date ≤ 20260630; la sesión 20260701 abre `1782856800000000000` ns) · este documento no contiene ningún outcome.

> Este manifiesto existe porque la orden 019 lo puso después del censo: se escribe
> **con los conteos delante**. Nada de lo que sigue eligió mirando un outcome — el
> censo es outcome-free y la verificación de eso está commiteada.

---

## 1. La pregunta (estimand)

Para una zona `Z = [L, U]` fijada ex ante en `available_at_z`, con una primera
aproximación que termina en **near-miss sin acceso** seguida de **rechazo ≥ R_min**
y **reset**, en el primer landmark `t2` en que el precio vuelve a aproximarse con
fuerza:

> **Δ_historia(z, x) = P(ACCESS desde t2 | historia near-miss/reset, Z = z, X_t2 = x) − P(ACCESS desde t2 | sin esa historia, Z = z, X_t2 = x)**

Es un estimand **predictivo incremental** (landmarking), **no** el efecto causal
del near-miss — condicionar en «llegó a A2» puede crear collider bias, y se declara
(v1 §grafo, v4 §3). La cadena de subpreguntas de v4 §4 queda intacta y en orden:
`H-ZVALID → H-NM → H-REVISIT → H-A2ACCESS → H-PEN → H-ECON`; la que este manifiesto
pone en F4 es **H-A2ACCESS** (el incremento histórico), con H-REVISIT ya medida como
población (la tabla A2/nm del censo, §2).

## 2. La población, con los conteos delante

Universo del censo v1 (congelado): 4 contratos de 6E encadenados (sha256 canónicos
verificados, incl. `6E_09-26 = 6ffcdf04…`), **228 sesiones**, **575 zonas** del
portador (`aVolClusterPOI` v0.5, `RESEARCH_DEFAULTS`), 16.215.330 ticks tras el
firewall por trade date.

Las 8 celdas que viven por N (≥ 403, predicado primario `trade` = ningún trade
dentro de `[L,U]` antes del giro):

| celda | n_A1 | near-miss | **marginal** | n_A2 | A2/nm | sesiones |
|---|---|---|---|---|---|---|
| D_far=10 · δ=2 · R=5 | 142.023 | 579 | 311 | 57 | 0,098 | 114 |
| D_far=10 · δ=3 · R=5 | 142.023 | 977 | 398 | 136 | 0,139 | 135 |
| **D_far=10 · δ=5 · R=5** | 142.023 | **1.505** | 528 | 433 | 0,288 | **139** |
| D_far=10 · δ=8 · R=5 | 142.023 | 1.505 | **0** | 1.231 | 0,818 | 139 |
| D_far=20 · δ=5 · R=5 | 210.985 | 482 | 213 | 167 | 0,346 | 101 |
| D_far=20 · δ=8 · R=5 | 210.985 | 866 | 384 | 465 | 0,537 | 126 |
| D_far=20 · δ=8 · R=10 | 210.985 | 593 | 279 | 91 | 0,153 | 119 |
| D_far=80 · δ=8 · R=5 | 340.135 | 414 | 118 | 288 | 0,696 | **21** |

Las otras 52 celdas mueren por N — eso está medido y publicado, no inferido.

**Configuración central (fijada acá, con razón escrita por número):**

`D_far = 10 · δ_nm = 5 · R_min = 5 · predicado = trade`

- `R_min = 5` no es una elección: es el único valor donde `D_far = 10` tiene
  población (con R = 10 y R = 20 la fila es **cero**). Lo fija el censo.
- `δ_nm = 5`: es 4,38 spreads medianos de 6E (spread medio 1,141 ticks, 89 % del
  tiempo a 1 tick) — fuera del ruido de spread. `δ = 1` muere en las 12 celdas
  (sub-spread, 0,88). `δ = 8` en `D_far = 10` tiene **marginal 0**: no aporta ni un
  near-miss nuevo sobre δ = 5; su salto de A2/nm (0,818) es mecánico (la condición
  de A2 es «volver a ≤ δ»; más δ, más fácil), no más fenómeno.
- `D_far = 10`: ancla la aproximación como «desde cerca». `D_far = 80` vive **por
  eventos y no por cobertura** (414 eventos en sólo 21 sesiones) — la unidad que
  acota la potencia es la sesión; queda fuera del primario con la razón escrita.

**Sensibilidad declarada (regla ±1 paso, ya censuada, no se re-corre después de
outcomes):** `D_far ∈ {10, 20}` · `δ_nm ∈ {3, 8}` · `R_min = 5` · y el eje
`quote_near_miss` como sensibilidad de predicado (la brecha quote/trade se cierra
al crecer δ: 0,762 → 0,960; quote tiene **7** vivas, no 8).

## 3. Nulos y controles (heredados, no reinventados)

- **Pseudozonas apareadas de F1.1** (misma sesión/lado/edad/ancho/distancia) —
  **semilla nueva declarada**: `hz2a_f4_2026-08-18`. El generador no se toca.
- Los controles obligatorios de v1/v4, todos dentro de la familia declarada:
  primera aproximación con estado actual equivalente · segunda sin near-miss ·
  near-miss sin reset · reset sin fuerza renovada · historia permutada por bloques
  dentro de régimen · apertura/noticias/roll separados o excluidos ex ante.
- **Eventos de una misma `zone_id` no se dividen entre train y test.** Cluster
  primario `zone_id`; secundario sesión CME; purge/embargo por vida de zona +
  horizonte; bootstrap por bloques; walk-forward por contrato; instrumentos
  separados antes de poolear (P-44b escrito: params fijos no transportan).

## 4. Grafo causal y mecanismo (lo que el addendum 007 §3 exigió)

Variables: `Z` zona ex ante · `C` régimen (hora, volatilidad, sesión, instrumento) ·
`M` metaorden/información latente · `L0/L1` liquidez antes/después · `R1` rechazo ·
`B` reset · `A2` segunda aproximación · `Y` outcome.

```
Z,C,M,L0 → R1
R1,C,M → L1,B
C,M,L1,B → A2
Z,C,M,L1,A2 → Y
```

- **Mecanismo económico propuesto** (hipótesis, no hecho): clustering de órdenes en
  niveles (Osler 2003: take-profit EN el nivel, stops DETRÁS) + absorción del flujo
  en la primera aproximación + resiliencia/reposición del libro en el reset. La
  cadena completa «near-miss → reset → A2 accede» **no está probada en la
  literatura** (v4 §2, búsqueda exacta negativa) — es la contribución potencial.
- **Latentes declaradas**: «se agotó el inventario» / «volvió la metaorden» no son
  observables sin L2/MBO — prohibido escribirlas como dato (v4 §3). «Agotamiento»
  sin L2 se marca como error (regla viva, A5).
- **Evidencia que refutaría el mecanismo**: F1.3 ya apunta contra agotamiento (la
  ruptura **cae** con los toques previos: 30,3 % → 16,7 %); L2 con reposición en
  vez de depleción mata la narrativa aunque el resultado se sostenga (v2 §13).
- **Confusores declarados**: hora/sesión, volatilidad local, distancia y fuerza en
  t2, ancho y edad de la zona, confluencia. Todo eso entra como `X_t2` — la
  pregunta es si la historia agrega **encima** del estado actual.

## 5. Medición: unidades, relojes, empates (P-39 aplicado al manifiesto)

- `d_t` **firmada, en ticks enteros, por `zone_id`** — nunca «la más cercana»
  (cobertura 99,31 % hace vacuo «hay una zona cerca»).
- Cadena por variable: `constructo → observable → **unidad + reloj** → estimador →
  chequeo` (entrada 021 §5.1; es la dimensión que produjo el factor 60.000 de
  F0.3). Ninguna variable entra sin unidad y reloj declarados.
- **Reloj primario por estimand** (v4 §6): directional-change para la geometría
  (A1, near-miss, rechazo); eventos/trades para el hazard desde t2; calendario
  para sesión y riesgo. Sensibilidad entre relojes preregistrada; resultado
  presente en un solo reloj = etiqueta `CLOCK_SENSITIVE`, se investiga antes de
  promover o descartar. Elegir después el reloj «que dio» queda prohibido.
- **Regla de empate intra-timestamp** (P-28: `sequence` no es orden de exchange):
  conservadora — si en el primer timestamp con algún trade dentro de `[L,U]` hay
  tal trade, el episodio es `ACCESS`. El adverso gana, como en el simulador.
- **Riesgos competitivos** (v4 §3): `ACCESS` · `PENETRATION_k` · `REJECT_AGAIN` ·
  `ZONE_INVALIDATED/EXPIRED` · `OTHER_ZONE_INTERFERENCE` · `SESSION_END` /
  `DATA_GAP` · censura por horizonte. Ninguna censura se convierte en «falló» en
  silencio.

## 6. Limitaciones declaradas (del censo, auditado en la 021)

1. **Ciclo de vida de la zona**: el censo v1 aproxima «disponible» como «misma
   sesión» — no modela la invalidación dentro de la sesión. El diagnóstico C-B la
   mide (outcome-free); si una fracción material de los near-miss cae con la zona
   ya invalidada, **este manifiesto se enmienda y el censo se re-corre como v2
   antes de cualquier F4**. El censo v1 queda congelado: ningún cambio de
   definición se edita en silencio — nueva definición = nueva etiqueta.
2. **A1 sin filtro de actividad**: `n_A1` es cota superior (dirección segura para
   factibilidad: no infla near-miss).
3. **P-28 permanente**: sin orden intra-timestamp del exchange; cualquier análisis
   que lo asuma está fuera de soporte.
4. **Quote es sensibilidad, no se mezcla** con el primario.

## 7. Potencia y presupuesto de multiplicidad

Pisos por brazo (dos proporciones, bilateral α = 0,05, potencia 80 %, design
effect 1,14 de H1) — **recomputados por el auditor, cierran al dígito** con v2 §8:
N ≥ **403** (Δ = 10 pp) · N ≥ **1.566** (Δ = 5 pp).

Lectura honesta para la configuración central (`n = 1.505` eventos en **139**
sesiones):

| denominador | n | MDE₈₀ (peor caso p = 0,5) |
|---|---|---|
| eventos, si fueran IID | 1.505 | ≈ 5,1 pp |
| eventos con DE = 1,14 | ≈ 1.320 | ≈ 5,5 pp |
| **sesiones (la unidad que acota)** | **139** | **≈ 16,8 pp** |

Es decir: la celda central limpia el piso de eventos para Δ = 10 pp con holgura,
queda **justo por debajo** del piso de 5 pp a nivel evento (1.505 < 1.566), y la
dependencia por sesión empuja el MDE real hacia arriba. El estimador es bootstrap
por bloques por sesión y se reporta el IC, no un punto. Si se quiere resolución de
5 pp, la respuesta es más sesiones/contratos — se declara, no se hace en silencio.

**Presupuesto de multiplicidad, escrito antes de correr:**

- censo v1: **60 celdas** — gastadas y públicas (outcome-free).
- fase de test: configuración central (**1**) + sensibilidad ya censuada (**≤ 7**)
  + contrastes de la escalera M0→M1→M2 (**2**) + eje quote (**1**) + familia de
  pseudozonas con semilla nueva declarada.
- **N_eff total declarado: 71** (60 + 11). El dato del censo —«si se cobra sobre
  testeables son 8, no 60»— está incorporado: la fase de test cobra 11, no 60.
- Cualquier eje agregado después (otra ventana horaria, otro activo, otra
  definición de cluster) = **campaña nueva que hereda el presupuesto**.

## 8. Economía (W7) — capítulo, no medición

- Registrado (entrada 009): cuenta **LucidFlex 25K**; tabulado 6E $2,40/lado ⇒
  **0,768 ticks RT** · ES $1,75/lado ⇒ 0,28 ticks RT. **El dato real del broker
  sigue siendo de Nico (N1)** — sin eso no hay afirmación neta.
- El escenario base es **específico por instrumento**; la fricción de H1
  (−2,7680 ticks/evento) queda como referencia hostil, no transportable.
- Q-ECONÓMICA muere si el recorrido no paga spread + slippage + comisión en base,
  o si el fill exigible no es admisible bajo G0.4 (~99,9 % de los límites se
  cancelan ⇒ sin limit-fills optimistas).

## 9. Cómo se refuta (variante vs core — la objeción de Nico integrada)

- **Mueren variantes** (barato): por N insuficiente (ya pasó en 52/60), por
  equivalencia con pseudozonas, por inestabilidad de definición entre relojes, por
  ausencia de incremento histórico en H-A2ACCESS, por economía.
- **El core muere** sólo por: la matriz M0/M1/M2 fuera de muestra (M1 no supera
  M0, o M2 no supera M1), equivalencia con pseudozonas, o economía — nunca por un
  N chico en una celda.
- Matriz interpretativa preregistrada: sólo M0 ⇒ primer pasaje genérico, muere ·
  M1 > M0 y M2 ≈ M1 ⇒ la zona aporta, la historia no, muere Q-DINÁMICA · M2 > M1
  también en pseudozonas ⇒ reaproximación genérica, muere · M2 > M1 sólo en
  reales ⇒ primera evidencia a favor.

## 10. Firewall y orden de ejecución

- Nada con outcomes corre hasta el STOP. El runner que lea outcomes **no entra**
  sin el test de ceguera verde (C-A, asignado y chico).
- Orden: **STOP de Nico → instrumentación (Claude; fixture BigTrap2 para
  ingeniería, aVol v0.5 fijo para ciencia, Gaps2 control) → F4** (IC/Spearman por
  estado y horizonte antes que SL/TP; triple barrera sólo si IC ≠ 0).
- En paralelo, sin bloquear: C2 (P-42, umbral por bucket) · C-B (ciclo de vida) ·
  saneamiento G2-A1 (gate de G2, no de la ruta).

## 11. STOP — lo que Nico aprueba o rechaza, en números

1. La configuración central `D_far=10 · δ_nm=5 · R_min=5 · trade` y la
   sensibilidad declarada (§2).
2. El presupuesto **N_eff = 71** escrito (§7) y la regla de herencia por campaña
   nueva.
3. El congelamiento del censo v1 y la regla «nueva definición = nueva etiqueta»
   (§6.1), con C-B corriendo antes de F4.
4. El estimand de §1 como landmark predictivo — no causal — y la matriz de
   refutación de §9.

Si algo de eso se rechaza, se edita acá y se re-publica con otra versión. Si se
aprueba, la línea pasa de `HYPOTHESIS_REFINED_NOT_RUN` a «manifiesto congelado»,
y F4 deja de estar bloqueado por el capítulo 5.
