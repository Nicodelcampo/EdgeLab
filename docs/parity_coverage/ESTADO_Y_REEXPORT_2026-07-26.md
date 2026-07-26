# Estado de paridad de los seis kernels + lista consolidada de re-export

**Fecha**: 2026-07-26 · **Referente**: `docs/NORTH_STAR.md` sha256
`21bb3b01a33e2b37…` · **Precondición cumplida**: el barrido ULP corrió **antes**
de esta lista, según la directiva de orden de Nico. Resultados en
`docs/audits/AUDIT-003_barrido_ulp.md`.

---

## 1. Estado de paridad — los seis

| kernel | `.cs` | estado | qué falta |
|---|---|---|---|
| **Gaps2** | *(anclado)* | ✅ **PASS** — 1316/1316 | nada. **No se toca** |
| **BigTrap2** `time:1` | v2.1 | ✅ **PASS** — 0 diffs, tolerancias intactas | nada en `time:1`. `tick:25` sigue bloqueado por TICKBAR-001 |
| **VolTicksPOC2** | v2.1 | ✅ **PASS** bajo la regla de ventana llena — 37 pares, 0 discrepancias | nada. Detalle abajo |
| **HFTZones2** | **v2.3** *(nuevo)* | ⏳ **pendiente de oráculo** | re-export obligatorio: el `.cs` cambió |
| **AACloseOpenDiffs** | **v1.1** *(nuevo)* | ⏳ **pendiente de oráculo** | re-export obligatorio: el `.cs` cambió |
| **aVolCellPOI2** | v2.0 | ⏳ **pendiente de oráculo más denso** | el actual tiene 82 filas y arranca en la sesión 22. Ver §3 |

Y una decisión abierta que no bloquea ningún oráculo:

| # | qué | por qué frena |
|---|---|---|
| **D-1** | semántica del umbral de mecha de BigTrap2 (`hi − range × 30 %`) | expuesto **0,0241 % medido**. Pasarlo a enteros exige elegir un redondeo, o sea **cambiar la definición del indicador**. Es diseño → **decide Nico** |
| **D-2** | qué hacer con el histórico de `AACloseOpenDiffs` anterior al 2026-07-26 | tiene ~47 % de los gaps de 1 tick faltantes, con **sesgo sistemático** hacia gaps grandes → **decide Nico** |

---

## 2. VolTicksPOC2 — residual resuelto, gate reevaluado

Corrección a lo que había reportado antes: no era "44/44 con 1 residual" sino
**44 apareadas y 7 zonas Python sin contraparte en NT8** (51 vs 44).

Aplicando la **regla de ventana llena** aprobada por Nico (`ratio_window_bars`
= 2000 en los dos lados):

| | |
|---|---|
| pares apareados en región de ventana llena | **37** |
| discrepancias en región de ventana llena | **0** |
| excluidas por ventana incompleta (py / nt8) | 14 / 7 |
| **gate** | **PASS** — tolerancias intactas |

**Las 7 discrepancias caen todas en la región de ventana incompleta, y no hay
ninguna fuera de ella.** `window_count` de las 7: 549, 571, 812, 855, 857, 1206,
1635 — todas por debajo de 2000. La regla se pre-registró *antes* de mirar qué
excluía, así que esto es una predicción cumplida, no un ajuste post-hoc: si una
sola discrepancia hubiera tenido `window_count ≥ 2000`, la regla no la salvaba.

**Mecanismo.** El percentil de la barra *b* depende de las 2000 barras previas.
NT8 arranca esa ventana en la primera barra que cargó el chart y Python en el
inicio de la región de corrida; con orígenes distintos las dos ventanas parciales
contienen ratios distintos y una barra cerca del umbral cae de lados opuestos sin
que haya discrepancia de kernel. Se ve directo en los contadores: para la misma
zona, `window_count` Python = 808 y NT8 = 1569.

**Lo que cuesta, dicho sin maquillar.** La región comparada se achica: 37 pares
en vez de 44, 14 zonas Python excluidas de 51. El test es **más débil** que si
los dos lados arrancaran la ventana en el mismo bar. La forma de recuperar
potencia sin tocar tolerancias es exportar un oráculo cuyo warmup cubra las 2000
barras **antes** del inicio de la ventana de comparación — queda anotado para el
próximo export de este kernel, no es urgente porque el gate ya da PASS.

---

## 3. Calendario de sesiones — corrijo mi diagnóstico anterior

Había reportado el FAIL de `aVolCellPOI2` como *deriva de calendario de sesiones*.
**Es incorrecto.** Medido contra los oráculos reales:

| kernel | fronteras NT8 vs Python |
|---|---|
| HFTZones2 | **7 / 7 coinciden** |
| aVolCellPOI2 | **4 / 4 coinciden** |

`sessions.py` ya está alineado a NT8: 17:00 CT, DST-aware. Y el rango
2026-06-08 → 2026-07-21 **no tiene ningún feriado con cierre completo** —
Juneteenth y el 3 de julio operaron con **cierre temprano a las 15:00 CT**,
verificado sobre los ticks del parquet, no supuesto.

Lo que sí difiere es el **origen del contador**: NT8 numera desde la primera barra
que cargó el chart, Python desde el inicio del parquet. En 6E 09-26 da un offset
constante de **4** (NT8 arranca en 2026-06-12, el parquet en 2026-06-08). Se
verificó exacto: `session_index` 22 de NT8 ↔ índice 26 de Python para 2026-07-14.

> **Regla derivada, ya en el contrato**: un `session_index` de NT8 **no es** un
> índice de Python. Se traduce por **trade-date**, nunca por ordinal.

De paso quedó confirmada la timezone del chart: `America/Argentina/Buenos_Aires`
(19:00 local = 17:00 CT = 22:00 UTC), verificada contra los 7 eventos.

El **preflight** está implementado y conectado al runner: corre antes de comparar
zonas y aborta con diagnóstico (qué sesión, qué fecha). Distingue un hueco
interior real de un rango de carga distinto — si abortara por rangos distintos,
abortaría siempre y nadie lo miraría.

**Por qué `aVolCellPOI2` sigue pendiente**: su oráculo tiene 82 filas y arranca en
la sesión 22 con `session_count=18` contra `lookback_sessions=20` — la ventana de
sesiones **nunca se llena** en todo el export. Por la regla de ventana llena, la
región comparable es **vacía**. No es un FAIL de kernel: es un oráculo que no
alcanza para afirmar ni negar paridad.

---

## 4. Lista consolidada de re-export — UNA sola sesión de NT8

Tres exports. **Gaps2 no está en la lista: está anclado y no se toca.**

Antes de arrancar, instalar los dos `.cs` corregidos (reemplazo *in place*, nunca
copias dentro de `bin\Custom` — incidente del 2026-07-25):

| archivo | versión | sha256 canónico |
|---|---|---|
| `nt8/HFTZones2.cs` | **v2.3** | `9bdbcc8108d8dc3248bf0b23b18e2bbf53765a8a7fdfbb86ebf9f0e35f04fd32` |
| `nt8/AACloseOpenDiffs.cs` | **v1.1** | `5a898da43812fd52bbcf26943a27cf20da0a1572dd318be96b9c42523ac5e9b6` |

Verificación antes de entregarlos a NT8:

```bash
.venv/Scripts/python tools/check_nt8_cs.py --ulp nt8/HFTZones2.cs nt8/AACloseOpenDiffs.cs
```

Debe dar `[OK]` en los dos y `SIN TRIAJE: 0`.

### Export 1 — HFTZones2 v2.3

| campo | valor |
|---|---|
| indicador | **HFTZones2**, v2.3 |
| instrumento | **6E 09-26** |
| resolución | **1 Minute** |
| rango | **2026-07-06 → 2026-07-17** |
| params | **defaults** (`AdaptiveMode=true`, `PenetrationTicks=1`) |
| archivo nuevo | `E:\EdgeLab\oracles\HFTZones2_adaptive_6E_0926_v23.csv` |

**Por qué**: el `.cs` estaba en v2.2 con `inside` comparando `double` mientras el
kernel Python ya era v2.3 en enteros. Los dos lados estaban desalineados por
construcción. El oráculo `_v22` **no sirve** para validar v2.3.

### Export 2 — AACloseOpenDiffs v1.1

| campo | valor |
|---|---|
| indicador | **AACloseOpenDiffs**, v1.1 |
| instrumento | **6E 09-26** |
| resolución | **25 Tick** *(cualquiera sirve — que pruebe de paso la independencia del `bar_spec`)* |
| rango | **2026-07-09 → 2026-07-17** |
| params | `MinDiffTicks=1`, `ExtendBars=50`, **`FiltrarPorPercentil=false`** |
| archivo nuevo | `E:\EdgeLab\oracles\AACloseOpenDiffs_6E_0926_v11.csv` |

**Por qué**: v1.0 descartaba el 47,5 % de los gaps de 1 tick. Se espera que el
nuevo oráculo traiga **notablemente más zonas** que el actual (1595 apareadas);
si trae la misma cantidad, el `.cs` instalado no es el v1.1 — vale la pena
mirarlo antes de seguir.

### Export 3 — aVolCellPOI2, más denso

| campo | valor |
|---|---|
| indicador | **aVolCellPOI2**, v2.0 *(sin cambios)* |
| instrumento | **6E 09-26** |
| resolución | **1 Minute** |
| rango | **2026-06-12 → 2026-07-17** ⟵ **el cambio importante** |
| params | defaults (`lookback_sessions=20`, `percentile=99.5`, `export_floor=95`) |
| archivo nuevo | `E:\EdgeLab\oracles\aVolCellPOI2_6E_0926_denso.csv` |

**Por qué el rango largo**: con `lookback_sessions=20`, el export actual llega a
`session_count=18` y **nunca llena la ventana**. Cargando desde 2026-06-12 el
chart acumula ~20 sesiones antes de 2026-07-13, así que la ventana está llena en
toda la región de comparación y el gate pasa a ser informativo.

> Cargar ~25 días de M1 en el chart. Si NT8 tarda mucho o recorta, avisá y
> ajustamos el rango — pero con menos de 20 sesiones de warmup este export no
> aporta nada que el actual no aporte ya.

### Qué NO hace falta re-exportar

| kernel | por qué |
|---|---|
| **Gaps2** | **anclado**. Paridad 1316/1316 sobre un `.cs` que no se tocó |
| **BigTrap2** `time:1` | PASS con el oráculo `_v2` vigente. El `.cs` no cambió en este barrido |
| **VolTicksPOC2** | PASS bajo la regla de ventana llena con el oráculo vigente |

---

## 5. Aporte al referente

Ninguno de estos pasos es un edge. Lo que hacen es que el próximo resultado
**signifique algo**: tres de los seis kernels ya tienen paridad afirmada sin
tocar una sola tolerancia, y los tres pendientes tienen una causa identificada y
un oráculo pre-registrado en vez de un FAIL sin explicar. La distancia al edge se
redujo porque bajó el costo de descartar una hipótesis falsa: antes cada bug de
la familia ULP costaba un export de NT8, ahora cuesta un comando.
