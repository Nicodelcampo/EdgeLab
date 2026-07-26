# CAMP-002 — ¿Filtrar zonas por régimen de volatilidad previsto aporta algo?

**Estado: PRE-REGISTRADA, NO CORRIDA.** Requiere OK explícito de Nico.
**Fecha**: 2026-07-26 · **Referente**: `docs/NORTH_STAR.md` sha256
`21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`

> **STOP activo.** Esta campaña evalúa lift sobre P&L/retornos. La regla
> permanente del `CLAUDE.md` exige presentar manifiesto + número efectivo de
> hipótesis + riesgos + datos faltantes y **esperar aprobación**. Este documento
> es esa presentación. No se corre nada hasta el OK.

---

## 1. Justificación económica

*(campo obligatorio de toda plantilla generadora)*

CAMP-001 cerró **negativo**: 0/48 configuraciones de Gaps2 con expectativa neta
positiva, E[bruto] agregado −0,1479 ticks/trade. La refutación fue estructural,
no marginal — la señal no pagaba los costos por un margen amplio.

Una lectura posible de ese resultado es que las zonas **no** tienen edge. Otra es
que lo tienen **condicionado a régimen**, y que promediar sobre todos los
regímenes lo diluye hasta cero. CAMP-002 discrimina entre esas dos lecturas.

Si la segunda es cierta, el filtro debería aparecer como un aumento de la
expectativa neta en el subconjunto filtrado, **con menos trades**. Si es falsa,
`sigma_pred` no aporta nada y Kronos se descarta barato — que es exactamente para
lo que sirve tener una capa de validación.

**El valor de esta campaña es simétrico**: un resultado negativo cierra una línea
de investigación por poco dinero, y eso también reduce distancia al referente.

---

## 2. Cómo podría refutarse

*(campo obligatorio)*

Criterio **pre-registrado, antes de mirar ningún resultado**:

> La hipótesis queda **REFUTADA** si el lift incremental de expectativa neta del
> filtro de régimen, sobre la estrategia base y a igualdad de todo lo demás, no
> supera **0 ticks/trade** con `p < 0,05` bajo MCPT de bloques de sesión, en el
> **walk-forward** (no en la muestra completa).

Refutaciones adicionales, cualquiera de ellas suficiente:

| # | condición | por qué refuta |
|---|---|---|
| R1 | el lift existe pero desaparece al aplicar costos de MNQ/6E | no es operable |
| R2 | PBO > 0,50 en CSCV | el filtro es sobreajuste |
| R3 | el lift proviene de < 3 sesiones | es un evento, no un régimen |
| R4 | el filtro reduce trades > 80 % | no queda muestra para afirmar nada |
| R5 | `sigma_pred` correlaciona > 0,95 con una vol realizada rezagada trivial | Kronos no aporta sobre `std(returns)`; usar el trivial |

**R5 es la que más importa** y es la más barata: si la predicción de Kronos es
casi idéntica a una vol realizada de 20 barras, no hace falta un transformer de
102M de parámetros ni 2,5 GB de dependencias. **Se evalúa primero**, y es
target-free — no toca P&L, así que **no está bajo STOP** y se puede correr con
sólo instalar el modelo.

---

## 3. Número efectivo de hipótesis

Lo que multiplica el data snooping, declarado antes:

| eje | valores | n |
|---|---|---|
| feature de filtro | `sigma_pred`, `spread_q90_q10`, `p_up` | 3 |
| umbral | percentil {50, 70, 90} del propio feature | 3 |
| sentido | filtrar arriba / abajo del umbral | 2 |
| kernel de zonas | Gaps2 *(el único con paridad anclada)* | 1 |

**Hipótesis nominales: 3 × 3 × 2 = 18.** No son independientes: los tres features
salen de la misma distribución de caminos y los umbrales están anidados. Estimo
un **número efectivo ≈ 8–10**.

Corrección declarada: **Deflated Sharpe Ratio con N = 18** (el nominal, no el
efectivo — conservador a propósito) más el PBO por CSCV que ya implementa
`edgelab/research/g2.py`.

**Presupuesto de investigación: una sola pasada.** Si sale negativo, se cierra —
no se reabre con otro umbral, otro horizonte ni otro `bar_spec`. Reabrir sería
exactamente el data snooping que la corrección pretende controlar.

---

## 4. Diseño

**Zonas**: Gaps2, config de CAMP-001 (`config_id a6c32c0e9dbeb79a`,
`kernel_id 771429ccc049bb8e`). Se reutiliza para que la comparación sea contra
una base ya medida y refutada, no contra una base nueva.

**Feature**: `sigma_pred` de Kronos-small, muestreo **por evento** — una llamada
por nacimiento de zona, no por barra. Es 466× más barato (0,8 h vs 388,9 h) y es
la política correcta conceptualmente: la pregunta es sobre el régimen **cuando
nace la zona**.

**Alineación**: `PITFeatureStore`, servido as-of por `available_at_ns`, con
`max_staleness` = la cadencia. Gate X1 (causalidad) verde **antes** de cualquier
evaluación.

**Comparación**: misma estrategia, mismo simulador, mismos costos, con y sin
filtro. Walk-forward con los `FOLDS` de `camp001.py`.

**Holdout**: **sellado**. 2026-07-01 → 2026-12-31 no se toca. Ni para elegir
umbral, ni para elegir feature, ni para mirar.

---

## 5. Datos faltantes / precondiciones

*(campo obligatorio — lo que hoy impide correr esto)*

| # | falta | bloquea |
|---|---|---|
| **P1** | decisión de Nico: `torch` + `transformers` (~2,5 GB) al lock, contra "sin dependencias pesadas nuevas; sin CUDA" | todo |
| **P2** | CPU o GPU. Con CPU, bar-a-bar es inviable (16,2 días) y sólo entra el muestreo por evento | el diseño |
| **P3** | pesos descargados y **hasheados** — `ModelIdentity` exige `weights_sha256` | X0 |
| **P4** | latencia real medida de `predict_at` con 30 caminos. Hoy es un placeholder pesimista de 2 s | X2, y `available_at` |
| **P5** | gate X5 aprobado (esta campaña) | la evaluación de lift |

**P1 es la decisión de fondo**, y no es sólo técnica: instalar el stack de
PyTorch cambia el entorno reproducible del proyecto entero, que hoy es un lock
liviano y auditable.

---

## 6. Orden propuesto — cada paso puede cerrar la línea

| paso | qué | costo | corta si |
|---|---|---|---|
| **0** | *(sin instalar nada)* infraestructura + firewall causal | **hecho** | — |
| **1** | sanity check zero-shot: 6E 5min, Kronos-small, mirar si la proyección es sensata o ruido | 1 tarde | la forma es ruido |
| **2** | **R5 primero**: correlación de `sigma_pred` con vol realizada rezagada. **Target-free, no está bajo STOP** | 1 hora | corr > 0,95 ⇒ usar el trivial y descartar Kronos |
| **3** | precómputo por evento + gates X1–X4 | 1 día | causalidad o reproducibilidad fallan |
| **4** | **X5 — lift.** Requiere el OK de este manifiesto | 1 semana | criterio §2 |
| **5** | fine-tuning | semanas + GPU | sólo si 4 muestra lift |

> El paso **2** es el de mejor relación información/costo de toda la campaña:
> es target-free, cuesta una hora, no consume presupuesto de hipótesis, y puede
> cerrar la línea entera antes de gastar una semana. Si Kronos no aporta sobre
> `std(returns)` rezagado, no hay nada más que discutir.

---

## 7. Lo que esta campaña NO hace

- **No usa Kronos como generador de entradas.** Los propios autores aclaran que
  son señales crudas que necesitan una capa de portfolio/riesgo. Acá es un
  **filtro de régimen** sobre zonas que ya existen y ya tienen paridad.
- **No toca el holdout.**
- **No evalúa `p_up` como señal direccional en el paso 4.** Está en la grilla de
  hipótesis por completitud, pero la hipótesis pre-registrada es la de
  **régimen**. Convertir esto en "a ver qué pega" es precisamente lo que el
  presupuesto de una pasada prohíbe.

---

## 8. Aporte al referente

No aporta un edge: aporta **capacidad de descartar barato**. CAMP-001 cerró
negativo y dejó una ambigüedad —¿no hay edge, o hay edge condicionado?— que sin
una feature de régimen no se puede resolver. Esta campaña la resuelve en un
sentido u otro, y el paso 2 puede resolverla por una hora de cómputo sin tocar
P&L ni instalar nada permanente.
