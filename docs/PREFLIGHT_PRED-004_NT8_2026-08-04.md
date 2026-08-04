# Preflight PRED-004 en NT8 — máquina de escritorio, 2026-08-04

> **NADA EJECUTADO.** No se copió el `.cs`, no se abrió NinjaTrader, no se corrió
> ninguna captura. Este documento es el preflight previo a la confirmación de
> Nico. **Tres bloqueantes requieren decisión antes del paso 1.**

## Estado verificado

| | |
|---|---|
| clon | `E:\ProyectosQuant\EdgeLab-sync-desktop` |
| rama · tip | `fix/capture-probe-v2-contract` · `baa43b9` (contiene `8df2a98`) |
| working tree | limpio |
| `nt8/BigTrap2.cs` del repo | `e5dd810a…684e977` — **coincide** · 47.227 B · CRLF puro (CR=LF=CRLF=1.109) |

---

## 1. Ruta de instalación NT8

```
C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators
```

**No es OneDrive.** El doc de migración §7.2 cita
`C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\...`, que corresponde a la
**otra** máquina. Acá el usuario es `Usuario` y `Documents` es local.

NT8 **no está corriendo** — condición necesaria para reemplazar el `.cs`.

> ⚠️ **Conflicto con la política de disco declarada para esta sesión** ("todo al
> disco E"). NT8 fija su ruta de indicadores y no acepta `E:`. Instalar exige
> escribir en `C:`. Sería **la única escritura a `C:` de toda la tarea**, y está
> pendiente de autorización explícita.

## 2-3. `BigTrap2.cs` instalado — ATRASADO

| | |
|---|---|
| sha256 | `75910484b7d87510…` |
| **versión** | **2.2** |
| tamaño · fecha | 38.454 B · 2026-07-27 10:22 |

Es exactamente el pin viejo que hace fallar `test_el_cs_canonico_es_el_declarado`.
**La trampa §7.1 del doc de migración está activa ahora mismo**: *"capturar con la
versión vieja produce un FAIL sin información"*.

Inventario completo de indicadores instalados:

| indicador | versión instalada | sha256 (16) |
|---|---|---|
| **BigTrap2** | **2.2** | `75910484b7d87510` |
| HFTZones2 | 2.3 | `9643cde1db56f297` |
| aVolCellPOI2 | 2.3 | `59a52d5227e75892` |
| VolTicksPOC2 | 2.1 | `2dae910f9c827c82` |
| Gaps2 | 2.0 | `04a578cdac758764` |
| AACloseOpenDiffs | 2.0 | `e4f5f17b7a2f29fe` |
| TickBarDiag | 1.1 | `e0c2cc8b9e1c45bd` |

## 4. Backup propuesto

```
E:\ProyectosQuant\EdgeLab-sync-desktop\archive\nt8_cs_backup\BigTrap2_v2.2_instalado_20260804.cs
```

A `E:`, dentro de la carpeta ya cubierta por `.gitignore` (commit `baa43b9`), así
que no ensucia el repo. **Copia, no move**: el archivo en NT8 se reemplaza recién
después de verificar que el backup existe y su sha256 coincide con el original.

## 5. SHA del v2.3 del repo

```
e5dd810a56e4883596d6a01cfffebdf9eda28bccb36cf69941589c7ba684e977
```

Coincide exacto con el publicado. `git diff 4a1ba55 HEAD -- nt8/BigTrap2.cs`
vacío: el archivo del tip **es** el de `4a1ba55`.

## 6. Parámetros exactos

Idénticos en las tres corridas — son los `SetDefaults` del propio `.cs`, sin
tocar nada:

| parámetro | valor |
|---|---|
| `TicksPerRow` | 1 |
| `ImbalanceMode` | `Diagonal` |
| `TrapVolumeSource` | `AggressiveSide` |
| `UseWickFilter` · `WickZonePct` | `true` · `30.0` |
| `ImbalanceRatio` | `3.0` |
| `MinDeltaFilter` | `0` |
| `MinTrapVolume` | `30` |
| **`MinExportVolume`** | **`1`** |
| `MaxAgeBars` · `MaxTouches` | `2000` · `0` |
| `Calculate` | `OnBarClose` |
| **Tick Replay** | **DESTILDADO** |

Dos trampas registradas que estos valores respetan:

- **§7.6** — `MinExportVolume=1` es el **piso analítico**; `MinTrapVolume=30` es
  sólo el corte on-chart. Confundirlos cambia qué eventos salen al CSV.
- **§7.3** — Tick Replay va **destildado**: el `.cs` declara que requiere tick
  data histórico descargado, no Tick Replay. La subserie de 1 tick no lo necesita.

**Lo único que cambia entre corridas es el bar spec del chart:**
`time:1` → `25 Tick` → `10 Tick`.

## 7. Rutas de salida — un archivo nuevo por corrida

`EventLogPath` base:

```
E:\ProyectosQuant\EdgeLab-sync-desktop\oracles\BigTrap2_v23_6E_0926.csv
```

**La garantía de P6 es del código, no del procedimiento.** `BigTrap2.cs:853-858`:

```csharp
string baseName = Path.GetFileNameWithoutExtension(EventLogPath) + "__" + bs;
resolvedEventLogPath = Path.Combine(dir, baseName + ext);
for (int k = 2; File.Exists(resolvedEventLogPath) && k < 1000; k++)
    resolvedEventLogPath = Path.Combine(dir, baseName + "_" + k + ext);
eventWriter = new StreamWriter(resolvedEventLogPath, false) { AutoFlush = true };
```

Compone `<base>__<bar_spec><ext>`; si existe, prueba `_2`, `_3`… antes de abrir.
Abre sobre un nombre que **ya verificó libre**. **Nunca append, nunca overwrite.**

Archivos resultantes esperados:

```
oracles\BigTrap2_v23_6E_0926__time1.csv
oracles\BigTrap2_v23_6E_0926__Tick25.csv
oracles\BigTrap2_v23_6E_0926__Tick10.csv
```

## 8. Comandos de análisis posteriores

```bash
cd E:\ProyectosQuant\EdgeLab-sync-desktop

# P5 — time:1 bit-idéntico contra el oráculo previo
.\.venv\Scripts\python tools\run_nt8_bridge.py --indicator BigTrap2 --bars time:1 \
  --chart-tz America/Argentina/Buenos_Aires \
  --oracle "BigTrap2=oracles\BigTrap2_v23_6E_0926__time1.csv" \
  --out runs\pred004\p5_time1

# P1 — K=25   (idem con --bars tick:25 y --out runs\pred004\p1_k25)
# P2 — K=10   (idem con --bars tick:10 y --out runs\pred004\p2_k10)

# estado del pin y de la asimetría 2.3/2.2
.\.venv\Scripts\python -m pytest tests\bridge\test_desviacion_rotura.py -q
```

## 9. Criterio PASS / FAIL / ABSTAIN

Literal de `docs/predictions/PRED-004_tickbar_attribution_v23.json`:

| id | medida | esperado (PASS) | refuta_si (FAIL) |
|---|---|---|---|
| **P5** | `time:1` | bit-idéntico al oráculo previo | cualquier diferencia |
| **P1** | `FOOTPRINT_MISMATCH` K25 | ≤ 1 % fuera de warmup/maturity tail | > 1 % |
| **P2** | `FOOTPRINT_MISMATCH` K10 | ≤ 1 % con el mismo código | > 1 % |
| **P3** | OHLCV del bloque atribuido | 100 % en barras procesadas | cualquier par procesado sin igualdad |
| **P4** | ambigüedad de anclaje | 0 barras procesadas con candidatos ≠ 1 | selección arbitraria |
| **P6** | archivos de EventLog | una corrida por archivo, meta propia, seq inicia una vez | append, overwrite o dos reinicios de seq |

**ABSTAIN** = `ANCLAJE_AMBIGUO`. Del diseño pre-registrado: *"al inicio y en cada
frontera se permite buscar un offset acotado; cero o múltiples candidatos implica
abstención fail-closed"*. Las abstenciones **se reportan como resultado**, no se
resuelven eligiendo un candidato.

`outcomes_accessed: false` en el JSON — sigue así.

---

## BLOQUEANTES — requieren decisión antes del paso 1

### A · La referencia de P5 no está en el clon *(bloqueante duro)*

`tools/correr_gates.py:55` espera `oracles/BigTrap2_time1_6E_0926_v2.csv`.
**No vino en la carpeta de migración**, que trae 6 oráculos y ninguno de `time:1`:

```
BigTrap2_tick25_6E_0926_v22.csv   (INVÁLIDO: tres corridas appendeadas)
tickbar_frontera2_10t__Tick10.csv
tickbar_frontera2_10t__Tick10_2.csv
tickbar_frontera3_10t__Tick10.csv
split/  (3 derivados, NO son oráculos)
README.md
```

**Sí existe en la copia histórica** `E:\EdgeLab\oracles\`, y es válido:

| | |
|---|---|
| sha256 | `7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27` |
| tamaño · líneas | 1.110.200 B · 6.577 |
| `# meta` | **1** → una sola corrida |
| reinicios de `seq` | **1** → sin append |

**Sin este archivo, P5 no se puede evaluar y el orden inalterable
(compilar → time:1 → K25 → K10) se corta en el paso 2.**

Traerlo cruza la regla 4 del pedido de migración (*"`data/`, `oracles/` y
`archive/` vienen exclusivamente de la carpeta de migración"*). **Requiere
autorización explícita.** No se copió.

### B · El oráculo de referencia se capturó con v2.1

Su `# meta` declara `version=2.1`, no 2.2 ni 2.3. P5 exige bit-identidad
corriendo **v2.3** contra una referencia **v2.1**.

El doc de migración §5 afirma que *"el camino de tiempo quedó intacto para
garantizar P5"* — y eso es exactamente lo que P5 pone a prueba, así que la
comparación es legítima. Se registra para que quede asentado que **el salto es
2.1 → 2.3**, no 2.2 → 2.3, y que una diferencia en `time:1` refutaría esa
afirmación del handoff, no sólo el cambio de atribución.

Parámetros con que se capturó la referencia (de su `# meta`): `ticks_per_row=1`,
`imbalance_mode=Diagonal`, `trap_volume=AggressiveSide`, `imbalance_ratio=3`,
`wick_filter=True`, `wick_zone_pct=30`, `min_delta=0`, `max_age_bars=2000` —
**idénticos a los defaults del §6**, así que no hay que reconfigurar nada.

### C · `TickBarDiag.cs` instalado ≠ repo

| | sha256 (32) |
|---|---|
| instalado | `e0c2cc8b9e1c45bd502bac731b24b58a` |
| repo | `da934b9ac5e9a2e2c8fe0014399aa0bb` |

Si K=25/K=10 lo usan para el ledger de atribución, aplica la misma trampa §7.1 y
hay que actualizarlo. **Pendiente de decisión sobre si entra en el alcance.**

Recordatorios asociados (§7.4, §7.5): `TickBarDiag` va con `SkipBars=0` y
`MaxBars=40000` — con los defaults (20/150) la captura cubre 150 barras y ninguna
frontera de sesión. Y su ledger sale en **hora del chart, no UTC**: el
clasificador necesita `--tz-shift-hours 3` con chart en ART.

---

## Abstenciones mantenidas

No se movió el pin del `.cs`. No se resolvió la asimetría 2.3/2.2. No se tocó
`nt8/BigTrap2.cs`. No se inició NT8 ni PRED-004. No se copió ningún oráculo entre
carpetas.

**Aporte al referente:** deja PRED-004 listo para ejecutarse con todos los
parámetros, rutas y criterios fijados **antes** de ver un solo resultado —que es
la condición para que su veredicto valga— y detecta antes de gastar una captura
que el `.cs` instalado está atrasado (v2.2) y que falta la referencia de P5, los
dos defectos que habrían producido un FAIL sin información.
