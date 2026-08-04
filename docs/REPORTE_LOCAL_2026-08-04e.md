# Reporte local (4) — 2026-08-04 · censo ejecutado y BLOQUEO: los datos locales son los viejos

> Ejecutado en la computadora operativa, siguiendo el handoff de
> `REPORTE_INVESTIGACION_2026-08-04d.md` §3.
>
> **Resultado: el censo de tasa de señales NO se ejecutó.** No por falta de
> manifiesto —se produjo— sino porque el censo de integridad demostró que los
> parquets de esta máquina son los **viejos, con la duplicación de bloque ya
> documentada**. Correr el censo sobre ellos habría producido un resultado
> inválido con apariencia de válido.

## 1 · Handoff — pasos ejecutados

| paso | resultado |
|---|---|
| 1 · fetch + descendiente limpio de `17ab97a` | HEAD `f226aa9`, working tree limpio |
| 2 · `pytest tests/research/test_signal_rate_census.py` | **7 passed** |
| 3 · ¿existe `runs/censo/manifiesto_universo.json`? | **NO** en ninguna ruta de la máquina |
| 4 · correr `post_sepmin.py` | **NO EJECUTADO** — ver §3 |
| 5 · `audit_post_sepmin.py` | no aplica |
| 6 · reportar bloqueo + productor canónico | este documento |
| 7 · no llenar H1–H3 | respetado |

Se respetó también la instrucción de no tocar todavía la taxonomía del auditor
de captura.

Sobre el paso 6: se identificó el productor canónico (`tools/censo_integridad.py`)
y, con autorización explícita de Nico, se lo ejecutó — **no** se improvisó un
manifiesto. Para que el worktree viera los parquets (que viven en el repo
original y están gitignored) se creó un *junction* de directorio
`EdgeLab-sync/data → EdgeLab/data`: no duplica los 323 MB, no modifica el
original y git no lo detecta.

## 2 · Censo de integridad — ejecutado

```
python tools/censo_integridad.py --out runs/censo
```

```
6E_03-26   87 dias  APTO=70  DEF=17  dup_bloque=0
6E_06-26   86 dias  APTO=76  DEF=10  dup_bloque=36
6E_09-25   47 dias  APTO=0   DEF=47  dup_bloque=0
6E_09-26   39 dias  APTO=23  DEF=16  dup_bloque=40
6E_12-25   90 dias  APTO=67  DEF=23  dup_bloque=0

universo: 236 dias aptos   config_hash=b92831e4cb3d59d3   113s
```

Artefactos: `runs/censo/manifiesto_universo.json`, `runs/censo/censo.json`.

Nota lateral que **despeja una preocupación anterior**: 236 días aptos supera los
200 que declara la ESPEC. El margen que en `REPORTE_LOCAL_2026-08-04.md` §2.1
consideré estrecho no lo es tanto — pero ver §3, porque este número está medido
sobre datos sucios.

## 3 · BLOQUEO — la duplicación de bloque +3h está presente

**76 duplicaciones de bloque, todas con desfase de exactamente +3,0 horas.**

```
desfase (horas) -> bloques:  {3.0: 76}

dias afectados:
  2026-05-27: 10        2026-06-19: 39
  2026-05-28: 13        2026-06-22:  1
  2026-06-01: 13
```

Ejemplo textual de la salida:

```json
{"origen_ts": "2026-06-19 09:00:16.008-05:00",
 "copia_ts":  "2026-06-19 12:00:16.008-05:00",
 "n_ticks": 256, "n_ticks_reales": 9870}
```

### 3.1 Es el defecto ya documentado, reproducido independientemente

`5c8dab7` ("parquets reconstruidos desde los exports limpios: 0 duplicaciones,
252 dias", 2026-07-27) dice:

> *"El defecto de duplicación de bloque NO era del parquet ni de su
> construcción… venía de la base histórica de NT8. Huella: +3 horas con la MISMA
> fracción de segundo… Los exports del 27-jul están limpios: 6E 09-26 del
> 2026-06-19 pasó de 50.906 a 41.036 ticks, y los **9.870** que se fueron son
> EXACTAMENTE la separación del bloque duplicado."*

Esta corrida, hecha sin conocer ese número de antemano, reporta para ese mismo
día y contrato **`n_ticks_reales = 9870`**. Coincide exactamente.

### 3.2 Y el mismo commit identifica el archivo local por su tamaño

> *"VALIDADO: alimentado con el archivo VIEJO reproduce el parquet VIEJO exacto
> — **2.085.208 filas**, 0 diferencias en las 12 columnas."*

`data/nt8/6E/6E_09-26_ticks.parquet` de esta máquina tiene **2.085.208 filas**.

**Conclusión: los `.Last.txt` de `TickData/` en esta máquina son los exports
ANTERIORES a la re-exportación del 27-jul.** El parquet que yo construí en F2
(`5a4da89`, 2026-08-03) es fiel a su fuente — el problema no es el conversor,
es la fuente.

### 3.3 Por qué no se corrió el censo de señales

Sobre datos con 9.870 ticks duplicados en un solo día, la tasa de señales de ese
día está inflada por construcción. Un censo así no falla ruidosamente: **produce
números plausibles**. Y como su salida alimenta la selección de H1–H3, el
resultado sería elegir hipótesis sobre un artefacto — exactamente el modo de
falla contra el que existe el guard de `f4367a2`.

Los 236 días aptos tampoco son comparables con los 252 del 27-jul: distinta
fuente.

## 4 · RETRACTACIÓN — mi hallazgo de los feriados está contaminado

En `REPORTE_LOCAL_2026-08-04b.md` §2 reporté dos cierres anticipados medidos
sobre `6E 09-26`, uno de ellos el **2026-06-19**.

Ese día es justamente el que concentra **39 de las 76 duplicaciones** (9.870
ticks duplicados). La medición se hizo sobre datos corruptos y **no se sostiene**.

Qué queda en pie y qué no:

- **2026-07-03** — no aparece en la lista de días con duplicación. La medición
  (último tick 14:59 CT, nada después) sigue siendo válida hasta donde alcanza,
  y coincide con un feriado CME conocido.
- **2026-06-19** — **retirado**. Hay que volver a medirlo sobre datos limpios.
- **El "+2 sesiones" ya no tiene mi explicación de "dos feriados"**: si uno de
  los dos cae, el número deja de cuadrar. La cadena causal del auditor sigue
  medida y en pie; lo que se retira es mi atribución del conteo.
- **El outlier del 2026-06-26** (último tick 18:59 CT) sigue sin explicar, y
  ahora con más razón para sospechar de la fuente: no figura entre los días con
  duplicación detectada, pero el detector busca una firma específica (+3h,
  bloques de 256 ticks) y no agota las formas de corrupción posibles.

El caveat que agregué en §2.0-bis de aquel reporte —*"quien construya el
calendario debe partir del calendario CME publicado y usar los ticks sólo para
verificar"*— resulta ser más necesario de lo que suponía al escribirlo.

## 5 · Qué hace falta para destrabar

**Traer a esta máquina los `.Last.txt` re-exportados del 27-jul** (los limpios),
regenerar los parquets con `databuild/build_nt8_ticks.py` y volver a correr el
censo de integridad. El criterio de aceptación es binario y ya está definido:
`dup_bloque = 0` en los cinco contratos, y ~252 días aptos en vez de 236.

Alternativa: correr el censo de señales en la máquina que ya tiene los datos
limpios.

### 5.1 Hallazgo secundario — `6E 09-25` aporta 0 días

```
CONTRATO_SIN_FRONT_MONTH_DECLARADO: 47 dias
```

Los 47 días de ese contrato se rechazan porque no tiene ventana de front-month
declarada. No es corrupción: es una declaración faltante en la configuración.
Con 47 días recuperables sobre un universo de 236, vale revisarlo — pero es
decisión de investigación, no de esta máquina.

## 6 · Lo que este reporte NO hace

- No corrió `post_sepmin.py` ni su auditor.
- No seleccionó H1–H3.
- No modificó el conversor F2 ni los parquets: el conversor es fiel a su fuente.
- No tocó la puerta única del holdout ni abrió el holdout.
- No modificó la taxonomía del auditor de captura.
- No borró ni reemplazó los datos viejos: quedan como están, para que la
  comparación contra los limpios sea posible.

**Aporte al referente:** se evitó producir un censo de tasas —y con él una
selección de hipótesis— sobre datos con duplicación conocida, y se retracta un
hallazgo propio cuya evidencia resultó contaminada. El costo de haberlo corrido
no habría sido un error visible sino uno plausible.
