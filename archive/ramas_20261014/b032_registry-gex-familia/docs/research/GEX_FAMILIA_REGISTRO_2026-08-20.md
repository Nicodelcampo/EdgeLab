# Registro de familia — GEX-NIVELES (niveles de gamma exposure)

- **Fecha de apertura:** 2026-08-20
- **Abierta por:** pedido explícito de Nico ("quiero que armes un indicador para NT8
  para ver esos niveles y cómo se comportó el precio respecto de ellos")
- **Redacta:** Auditor. **Rama propia** (`registry/gex-familia`), mergea Opus.
- **Estado:** OBSERVACIONAL. No es una campaña, no mide outcomes, no es señal de
  entrada. Es un overlay de niveles exógenos sobre el chart, para mirar.

---

## 1. Objeto

Niveles **diarios** derivados del open interest de opciones:

| nivel | definición | lectura |
|---|---|---|
| **Call Wall** | strike con máximo GEX de calls | resistencia |
| **Put Wall** | strike con máximo GEX de puts | soporte |
| **Gamma Flip** | precio donde el GEX neto acumulado cruza cero (interpolado) | corte de régimen: arriba amortigua, abajo amplifica |
| GEX neto + régimen | suma total, signo | contexto |

## 2. Fuentes (las dos, con su esquema)

1. **Historia:** parquet local `E:\options_data\SPY_options.parquet`.
   Verificado por Opus contra el artefacto (`7e9e019`): **4.514 días,
   2008-01-02 → 2025-12-12, cero filas ≥ 2026-07-01** — íntegramente pre-holdout
   *por construcción del dato*, no por filtro. Columnas reales (verificadas):
   `ask, ask_size, bid, bid_size, contract_id, date, delta, expiration, gamma,
   implied_volatility, in_the_money, last, mark, open_interest, rho, strike,
   symbol, theta, type, vega, volume`.
   **No tiene `spot` ni `underlying`** — el spot se estima por put-call parity
   dentro del vencimiento más cercano (corrección `7e9e019`; la v1 cruzaba
   vencimientos, producto cartesiano sin sentido).
2. **Día actual:** CBOE delayed CDN (`--today`). Gratis, sin API key, delay 15 min.
   No trae gamma: se calcula con Black-Scholes desde la IV de la cadena.
   **Cae dentro del período de holdout por fecha** — ver §6.

## 3. Parámetros congelados (no se tunean mirando el chart)

- Multiplicador SPY→índice: **×10**.
- `RISK_FREE = 0,043`; `DIV_YIELD[SPY] = 0,012` (solo para el gamma BS de `--today`).
- Piso de tiempo al vencimiento: **0,25 días** (los 0DTE entran; en la v1 el filtro
  `g > 0` con `t = 0` los excluía — el vencimiento con más gamma era el excluido).
- Agregación sobre **todas las expirations**.
- Convención de signo: **calls +, puts −** — estándar de la industria, **no
  validada** (gate GEX-M0 sigue abierto). Los niveles (walls, flip) son robustos a
  esto; la narrativa "los dealers están largos/cortos" es el supuesto, no el dato.
- Gamma flip: cruce interpolado del GEX acumulado por strike. **Aproximado, declarado.**

## 4. Unidad estadística y advertencias

- La unidad es el **día de opciones** (calendario NYSE), no la sesión CME. Si algún
  día se cruza con futuros, el mapeo día→trade date se define por escrito antes.
- El OI es un snapshot de la noche anterior; **no hay GEX intradía real** en ninguna
  de las dos fuentes.
- Para chart de ES, el basis ES−SPX entra por el parámetro `PriceOffset` del
  indicador (manual, por día). Nunca se ajusta para que una línea "pegue" mejor.

## 5. Qué está permitido y qué no

**Permitido ahora:** compilar, dibujar, mirar días **anteriores a julio 2026**.

**Prohibido sin protocolo nuevo:**
- Formarse una idea de estrategia mirando cómo reaccionó el precio a los niveles en
  **julio–diciembre 2026** (holdout). Dibujar los niveles no lo rompe; diseñar desde
  esas reacciones, sí. (Punto planteado por Opus, aceptado.)
- Cualquier medición de outcome (rechazo, ruptura, excursiones, P&L) contra estos
  niveles: cruza el STOP → protocolo propio + presupuesto de multiplicidad + OK
  explícito de Nico.
- Promover un nivel a "soporte/resistencia operable" en la libreta propia: eso ya es
  una hipótesis, y necesita su censo con controles (espejo/placebo), no el chart.

## 6. Gobernanza de esta apertura

- **F9 estaba pausada** por decisión sellada (no agregar indicadores sin evidencia de
  que haga falta). Esta familia entra por **pedido directo de Nico**, que es la
  autoridad — pero el registro escrito existía que hacerse igual, y es este
  documento. Lección registrada: la familia se abre **antes** del código, no después.
- El commit inicial (`301c29e`, del auditor) fue directo a `foundation`, contra la
  regla de fast-forward de CLAUDE.md. Opus verificó que la práctica ya divergía de la
  regla (17 de los últimos 18 commits suyos también directos). **Pendiente de Nico:**
  declarar cuál es la rama de trabajo hoy, o ratificar la regla.
- Dos bugs de la v1 encontrados por Opus y corregidos en `7e9e019` / `ce4a06e`
  (parity cross-expiry, columnas corridas en el `.cs` que dibujaban el "Call Wall"
  sobre el propio precio). La v1 nunca se usó para sacar conclusiones.

## 7. Ledger de la familia

*(vacío — ninguna medición todavía)*

| fecha | entrada | resultado |
|---|---|---|
| 2026-08-20 | registro + indicador observacional | — |
