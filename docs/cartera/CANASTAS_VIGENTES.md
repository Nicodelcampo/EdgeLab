# Canastas vigentes — qué se opera, con qué evidencia y cómo auditarlo

Estado: VIGENTE (GENERADO por `python tools/canastas_vigentes.py --write` de los archivos que usa la operación; no editar a mano). 0 edges promovidos: todas en papel/forward; operar con dinero real lo decide Nico. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Cómo auditar

- Cada número sale de un archivo committeado (columna «Operaciones»); el historial de git dice quién y cuándo lo cambió.
- Pre-registros (escritos antes de mirar): `docs/research/cartera_20261116/PREREGISTRO.md`, `PREREGISTRO_TANDA4.md`, `PREREGISTRO_FORWARD_V2.md`, `docs/research/fundedsyncstack_20261115/PREREGISTRO_CARTERA_B.md`; aperturas del holdout en `docs/research/HOLDOUT_VENTANAS.jsonl`; pruebas contadas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`.
- Recalcular: `python tools/cartera_nov_analisis.py seleccion|noviembre|prop`, `python tools/fundedsync_cadena.py cartera_b <AAAAMMDD>`, `python tools/lucid_canastas.py`, `python tools/seguimiento_forward.py <AAAAMMDD>` (forward bajo demanda).
- Costos: sólo `config/costos/costos_canonicos.json` (`edgelab/costos.py`).

## Cartera v2 (2026-11-16) — 8 reglas, base de `SELECCION.json (8 reglas congeladas)`

Mejoras aplicadas: A1 comisión mínima (firma más barata que admite algoritmos); A2 PREAPERTURA-NQ a la mitad; M1 no operar si fricción > 0,08 R (stop menor que el piso); M3 micros fijos por regla (riesgo mediano de desarrollo ≈ 200 USD).

| Regla | Señal → ejecuta | Micros | Riesgo mediano | No operar si stop < | R/op DESC (t) | R/op REP (t) | R/op oct | Fricción R | Meses + | Ops/mes | Operaciones (auditar) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CVGAP-ES-C | ES → MES | 2 | 192 USD | 11.1 pts | +0.40 (+2.9) | +0.27 (+1.5) | +0.06 | +0.059 | 86% | 8.5 | `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-ES-C__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-ES-C__rep.json`, `docs/research/cartera_20261116/ops/CVGAP-ES-C__hold.json` |
| U1-RACIMOS-GRILLA-NQ | NQ → MNQ | 1 | 200 USD | 19.31 pts | +0.17 (+2.4) | +0.14 (+0.8) | +0.44 | +0.017 | 82% | 4.9 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-RACIMOS-GRILLA-NQ__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-RACIMOS-GRILLA-NQ__rep.json`, `docs/research/cartera_20261116/ops/U1-RACIMOS-GRILLA-NQ__hold.json` |
| CONF-CVR-CFD-NQ-R | DK:USATECHIDXUSD → MNQ | 2 | 210 USD | 19.31 pts | +0.14 (+3.0) | +0.12 (+1.9) | +0.19 | +0.034 | 86% | 5.1 | `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__desc.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__hold.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__hold_oct.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__rep.json` |
| U1-ZONAS-BT2-ES | ES → MES | 2 | 233 USD | 11.1 pts | +0.11 (+4.3) | +0.08 (+1.8) | +0.13 | +0.047 | 86% | 4.6 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-BT2-ES__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-BT2-ES__rep.json`, `docs/research/cartera_20261116/ops/U1-ZONAS-BT2-ES__hold.json` |
| PREAPERTURA-NQ | NQ → MNQ | 1 ×0.5 | 99 USD | 19.31 pts | +0.35 (+1.3) | +0.41 (+1.1) | +0.07 | +0.036 | 71% | 10.3 | `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__desc.json`, `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__hold.json`, `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__rep.json` |
| U1-ORO-GRILLA | DK:XAUUSD → MGC | 1 | 177 USD | 7.56 pts | +0.20 (+1.7) | +0.02 (+0.1) | +0.57 | +0.051 | 58% | 5.2 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ORO-GRILLA__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ORO-GRILLA__rep.json`, `docs/research/cartera_20261116/ops/U1-ORO-GRILLA__hold.json`, `docs/research/cartera_20261116/ops/U1-ORO-GRILLA__hold_oct.json` |
| U1-ZONAS-BT2-NQ | NQ → MNQ | 2 | 200 USD | 19.31 pts | +0.08 (+0.9) | +0.10 (+0.9) | +0.11 | +0.032 | 69% | 8.3 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-BT2-NQ__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-BT2-NQ__rep.json`, `docs/research/cartera_20261116/ops/U1-ZONAS-BT2-NQ__hold.json` |
| CVGAP-CFD-ES-C | DK:USA500IDXUSD → MES | 2 | 256 USD | 11.1 pts | +0.02 (+0.2) | +0.11 (+1.5) | +0.35 | +0.040 | 64% | 5.4 | `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-CFD-ES-C__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-CFD-ES-C__rep.json`, `docs/research/cartera_20261116/ops/CVGAP-CFD-ES-C__hold.json`, `docs/research/cartera_20261116/ops/CVGAP-CFD-ES-C__hold_oct.json` |

Fricción R = fricción mediana antes del filtro M1 (con M1 no se opera cuando supera 0,08 R).

## Cartera v3 (2026-11-16) — 8 reglas (forward en paralelo con la v2), base de `v3/SELECCION.json (selección §5 con M1 antes de elegir; PREREGISTRO_TANDA4 C1)`

| Regla | Señal → ejecuta | Micros | Riesgo mediano | No operar si stop < | R/op DESC (t) | R/op REP (t) | R/op oct | Fricción R | Meses + | Ops/mes | Operaciones (auditar) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CVGAP-ES-C | ES → MES | 2 | 192 USD | 11.1 pts | +0.40 (+2.9) | +0.27 (+1.5) | +0.06 | +0.059 | 86% | 8.5 | `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-ES-C__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-ES-C__rep.json`, `docs/research/cartera_20261116/ops/CVGAP-ES-C__hold.json` |
| DRC-NQ-R | NQ → MNQ | 7 | 200 USD | 19.32 pts | +0.17 (+1.0) | +0.16 (+0.6) | +0.58 | +0.151 | 43% | 11.6 | `docs/research/cartera_20261116/ops/DRC-NQ-R__desc.json`, `docs/research/cartera_20261116/ops/DRC-NQ-R__hold.json`, `docs/research/cartera_20261116/ops/DRC-NQ-R__rep.json` |
| U1-ZONAS-AVCL-ES-C | ES → MES | 3 | 190 USD | 11.1 pts | +0.12 (+1.1) | +0.12 (+0.7) | +0.07 | +0.090 | 57% | 6.9 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-AVCL-ES-C__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-AVCL-ES-C__rep.json`, `docs/research/cartera_20261116/ops/U1-ZONAS-AVCL-ES-C__hold.json` |
| U1-RACIMOS-GRILLA-NQ | NQ → MNQ | 1 | 200 USD | 19.32 pts | +0.17 (+2.4) | +0.14 (+0.8) | +0.44 | +0.017 | 82% | 4.9 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-RACIMOS-GRILLA-NQ__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-RACIMOS-GRILLA-NQ__rep.json`, `docs/research/cartera_20261116/ops/U1-RACIMOS-GRILLA-NQ__hold.json` |
| PREAPERTURA-NQ | NQ → MNQ | 1 ×0.5 | 99 USD | 19.32 pts | +0.35 (+1.3) | +0.41 (+1.1) | +0.07 | +0.036 | 71% | 10.3 | `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__desc.json`, `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__hold.json`, `docs/research/cartera_20261116/ops/PREAPERTURA-NQ__rep.json` |
| U1-ZONAS-AVCL-NQ | NQ → MNQ | 3 | 200 USD | 19.32 pts | +0.04 (+0.4) | +0.04 (+0.7) | +0.09 | +0.093 | 50% | 8.1 | `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-AVCL-NQ__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/U1-ZONAS-AVCL-NQ__rep.json`, `docs/research/cartera_20261116/ops/U1-ZONAS-AVCL-NQ__hold.json` |
| CONF-CVR-CFD-NQ-R | DK:USATECHIDXUSD → MNQ | 2 | 210 USD | 19.32 pts | +0.14 (+3.0) | +0.12 (+1.9) | +0.19 | +0.034 | 86% | 5.1 | `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__desc.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__hold.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__hold_oct.json`, `docs/research/cartera_20261116/ops/CONF-CVR-CFD-NQ-R__rep.json` |
| CVGAP-CFD-ES-C | DK:USA500IDXUSD → MES | 2 | 256 USD | 11.1 pts | +0.02 (+0.2) | +0.11 (+1.5) | +0.35 | +0.040 | 64% | 5.4 | `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-CFD-ES-C__desc.json`, `docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-CFD-ES-C__rep.json`, `docs/research/cartera_20261116/ops/CVGAP-CFD-ES-C__hold.json`, `docs/research/cartera_20261116/ops/CVGAP-CFD-ES-C__hold_oct.json` |

## Cartera B (2026-11-16) — T + Z + R de FundedSync en MNQ (canasta aparte, otra lógica de riesgo)

Pre-registro: `docs/research/fundedsyncstack_20261115/PREREGISTRO_CARTERA_B.md`. Variante paralela: T filtrado por el sesgo Franklin (sólo T a favor del sesgo NY vs Londres y VWAP). Cuenta de referencia: {'tipo': 'drawdown fijo', 'dd': 3500, 'objetivo': 3500, 'dias': 120, 'nota': 'hasta que Nico fije la cuenta real'}. Puntos netos de fricción canónica por operación (desarrollo sin el stop de catástrofe de Z y R).

| Regla | Módulo | Micros MNQ | Stop | Pts/op 2020–23 (t) | Pts/op 2024–26 (t) | Ops/mes |
|---|---|---|---|---|---|---|
| T | FtmEngine | 1 | propio del módulo | +13.2 (4.4) | +19.4 (4.5) | 19.0 |
| Z | ZetaTrendDay | 1 | catástrofe 0,5 × ATR20 (vía MAE) | +26.6 (3.2) | +40.2 (2.7) | 2.2 |
| R | AtrPhase | 1 | catástrofe 0,5 × ATR20 (vía MAE) | +28.1 (2.5) | +75.9 (5.1) | 3.1 |

## En una cuenta LucidFlex 25K (simulación, descriptiva)

Valor esperado por cuenta comprada (USD), LucidFlex 25K con **DLL $600 + 50 % ($55,30)**, retirando $1.000; media de desarrollo / **contraída** (James-Stein ≈ mitad; el paso 2 de `urgencia_vs_evidencia_20261117` mostró que es OPTIMISTA: lo elegido no conservó nada en réplica, así que la expectativa honesta hoy está entre «cero» y «contraída» hasta que decida el forward) / cero (sin edge). Detalle de las 4 configuraciones y las dos políticas en `docs/research/propfirm_lucidflex_20261117/CANASTAS_LUCID.json`.

| Canasta | USD/sesión (t) | Pasa (contraída) | Cobra (contraída) | EV dev | **EV contraída** | EV cero | Días por cuenta | EV contraída por mes y cuenta |
|---|---|---|---|---|---|---|---|---|
| v2|usd100 | +49 (4.1) | 73% | 52% | +3299 | **+1912** | +55 | 114 | +352 |
| v2|usd200 | +98 (4.3) | 56% | 33% | +2305 | **+1127** | +36 | 51 | +464 |
| v2|usd300 | +150 (4.3) | 48% | 24% | +1774 | **+832** | +34 | 34 | +507 |
| v3|usd100 | +54 (3.7) | 60% | 33% | +2266 | **+1043** | +49 | 64 | +344 |
| v3|usd200 | +110 (3.9) | 46% | 22% | +1466 | **+679** | +70 | 30 | +476 |
| v3|usd300 | +167 (3.9) | 43% | 20% | +1280 | **+676** | +100 | 25 | +579 |
| B|1MNQ | +47 (8.2) | 52% | 24% | +2104 | **+654** | +69 | 58 | +239 |
| B|2MNQ | +94 (8.2) | 41% | 17% | +1276 | **+442** | +72 | 25 | +368 |
| B[T]|1MNQ | +27 (6.2) | 52% | 22% | +1642 | **+516** | +65 | 74 | +147 |
| B[Z]|1MNQ | +6 (3.9) | 37% | 6% | +210 | **+5** | -47 | 279 | +0 |
| B[R]|1MNQ | +13 (4.9) | 56% | 27% | +1225 | **+365** | +6 | 219 | +35 |
| B[T+Z]|1MNQ | +34 (7.4) | 55% | 25% | +2067 | **+638** | +69 | 74 | +182 |
| B[T+R]|1MNQ | +41 (7.2) | 51% | 22% | +1825 | **+566** | +63 | 58 | +204 |
| B[Z+R]|1MNQ | +20 (6.4) | 61% | 34% | +2195 | **+680** | +41 | 189 | +76 |
| B|1MNQ|desde-2025-08 | +77 (4.6) | 52% | 26% | +2537 | **+746** | +86 | 43 | +363 |
| v2+B | +175 (5.7) | 46% | 22% | +2401 | **+708** | +53 | 29 | +519 |

## Lo que NO está demostrado (leer antes de operar)

- Ninguna canasta tiene confirmación fuera de muestra con potencia: el holdout de oct–nov es corto y a favor; decide el forward.
- La media de desarrollo viene de reglas elegidas entre muchas: usar la columna **contraída**, no la de desarrollo.
- La vida de una ventaja en este dominio (NQ/ES intradía) todavía no está medida (paso 1b de `docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md`).
