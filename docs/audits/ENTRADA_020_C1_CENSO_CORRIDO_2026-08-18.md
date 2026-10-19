# Entrada 020 · Opus 5 → Auditor · C1 corrido: el censo existe (2026-08-18)

**Artefacto:** `docs/research/censo_hz2a_superficie_2026-08-18.json`
**Runner:** `diag/tasa_senales/censo_hz2a_superficie.py`
**Firewall:** `holdout_included: false` **computado** · `outcomes_accessed: false` · `pnl_accessed: false`
**Procedencia:** `medicion_comprometida: false` · los 4 parquets con **sha256 canónico verificado**

C1 está corrido. Esto **no es un edge ni una interpretación**: es la tabla de
población que la orden 019 pidió, y la muerte de 52 variantes por N.

---

## 1. Universo

| | |
| --- | --- |
| Serie | 4 contratos 6E encadenados y ordenados (la misma del portador) |
| Ticks | 17.915.971 brutos → **16.215.330** tras firewall por trade date |
| Sesiones | **228** |
| Barras | 281.703 |
| Zonas del portador | **575** |

## 2. Resultado principal: **8 de 60 celdas viven por N (≥ 403)**

Near-miss acumulado, predicado primario (`trade` = ningún trade en `[L,U]`).
`*` = vive por N.

```
R_min=5      d=1    d=2    d=3    d=5    d=8
D_far=10     268    579*   977*  1505*  1505*
D_far=20      76    157    269    482*   866*
D_far=40      48     86    136    229    371
D_far=80      93    165    221    296    414*

R_min=10     d=1    d=2    d=3    d=5    d=8
D_far=10       0      0      0      0      0
D_far=20      39     92    168    314    593*
D_far=40      12     23     38     64    111
D_far=80      62    116    145    177    223

R_min=20     d=1    d=2    d=3    d=5    d=8
D_far=10       0      0      0      0      0
D_far=20       0      0      0      0      0
D_far=40       8     16     27     46     84
D_far=80      58    109    135    161    203
```

**52 de 60 celdas mueren por N.** Eso es un resultado, no una falla del censo.

## 3. Las 8 vivas, con anillo marginal y sesiones

| celda | n_A1 | near-miss | **marginal** | n_A2 | sesiones |
| --- | --- | --- | --- | --- | --- |
| D=10 δ=2 R=5 | 142.023 | 579 | 311 | 57 | 114 |
| D=10 δ=3 R=5 | 142.023 | 977 | 398 | 136 | 135 |
| D=10 δ=5 R=5 | 142.023 | 1.505 | 528 | 433 | 139 |
| D=10 δ=8 R=5 | 142.023 | 1.505 | **0** | 1.231 | 139 |
| D=20 δ=5 R=5 | 210.985 | 482 | 213 | 167 | 101 |
| D=20 δ=8 R=5 | 210.985 | 866 | 384 | 465 | 126 |
| D=20 δ=8 R=10 | 210.985 | 593 | 279 | 91 | 119 |
| D=80 δ=8 R=5 | 340.135 | 414 | 118 | 288 | 21 |

**Por qué el anillo marginal era obligatorio** (condición 2 de la 014): la celda
`D=10 δ=8 R=5` tiene marginal **0**. Su acumulado de 1.505 es **idéntico** al de
`δ=5`: no aporta ni un near-miss nuevo. Leída sólo por acumulado parecería una celda
poblada; el marginal muestra que está vacía. Publicar sólo acumulados habría
sobre-contado la superficie exactamente como la 014 advirtió.

**`D=80 δ=8 R=5` vive por eventos y no por cobertura**: 414 near-miss en **21
sesiones**. `n` de sesiones no es `n` de eventos — condición 3 de la 014.

## 4. Brecha entre predicados

Se publica, no se mezcla.

| celda | trade | quote | quote/trade |
| --- | --- | --- | --- |
| D=10 δ=2 R=5 | 579 | 441 | 0,762 |
| D=10 δ=3 R=5 | 977 | 839 | 0,859 |
| D=10 δ=5 R=5 | 1.505 | 1.367 | 0,908 |
| D=20 δ=5 R=5 | 482 | 436 | 0,905 |
| D=20 δ=8 R=5 | 866 | 817 | 0,943 |
| D=20 δ=8 R=10 | 593 | 569 | 0,960 |
| D=80 δ=8 R=5 | 414 | 350 | 0,845 |

El predicado por quote es **siempre más chico**, como anticipaba la 014, y la brecha
**se cierra al crecer δ** (0,762 en δ=2 → 0,960 en δ=8). Se reporta; no se interpreta.

## 5. δ en unidades de spread (condición 1 de la 014)

Spread medio de 6E: **1,141 ticks** (medido sobre 5.554.201 quotes).

| δ_nm | en spreads |
| --- | --- |
| 1 | **0,88** |
| 2 | 1,75 |
| 3 | 2,63 |
| 5 | 4,38 |
| 8 | 7,01 |

**La columna `δ=1` está por debajo de un spread.** Ninguna de sus 12 celdas vive por N
—la mayor es 268— y eso es consistente con estar midiendo por dentro del spread, no
cerca de la zona. Queda dicho, no concluido.

## 6. Un defecto propio, que vale más que la tabla

El primer intento dio **0 zonas sobre 4.412 bloques**. No era warmup ni datos:
`SessionProfile` acumula en `pending` y `history_scores()` lee de `history`, y yo
**nunca llamaba `commit()`** al cerrar sesión. El perfil quedaba vacío para siempre,
`detect_block` abstenía por `"warmup"` en todos los bloques, y el censo devolvía cero
**sin error**.

Fallaba en silencio y con una salida perfectamente plausible: un censo vacío se lee
como «no hay fenómeno». El portador lo hace bien en
`avolcluster_tick_formal.py` l. 504; lo omití al reproducir la producción de zonas.

Queda como comentario en el runner del censo, no sólo acá.

## 7. Lo que este artefacto NO contiene

Ni acceso, ni penetración, ni MFE/MAE, ni P&L, ni tasa de nada. `outcomes_accessed`
y `pnl_accessed` son `false` y `holdout_included` está **computado**, no escrito.

El censo dice **cuántas oportunidades hay por celda**. No dice si sirven.

## 8. Lo que sigue

El manifiesto numérico lo redacta el auditor **con el N de esta tabla**. Después el
STOP de Nico. F4 no arranca sin eso.

Dato para el manifiesto: si el presupuesto de multiplicidad se cobra sobre las celdas
**testeables**, son **8**, no 60.
