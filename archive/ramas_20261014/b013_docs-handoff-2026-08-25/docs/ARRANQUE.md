# ARRANQUE — leé esto primero

Punto de entrada único. Si estás retomando EdgeLab en otra máquina o en otra sesión,
**empezá acá y no leas nada más hasta terminar la sección 2.**

---

## 0. Los tres minutos que evitan todo lo demás

```bash
git clone https://github.com/Nicodelcampo/EdgeLab.git   # si no lo tenés
cd EdgeLab
git fetch --all --prune
git checkout foundation/f0b-compatibility-probe
git log --oneline -1        # deberia decir 7fbab53 o posterior
python -m pytest -q tests/bridge/ 2>&1 | tail -1
```

**Lo que tenés que ver:** unos **27 fallos**. Eso es lo **esperado**, no un problema.
Vienen de antes y están documentados. Si ves 0 fallos, probablemente falten los datos de
`data/` y muchas pruebas se estén salteando.

---

## 1. Qué es esto, en un párrafo

Hay un indicador de trading, **BigTrap2Absorption**, que existe dos veces: en NinjaTrader
(C#) y en Python. Antes de medir si **gana plata**, hay que probar que las dos versiones
calculan lo mismo y entender qué hace cada una de sus 21 perillas. Eso está casi
terminado. **Lo de ganar plata no se midió nunca, a propósito** — es una decisión
pendiente, no una tarea.

---

## 2. Las cuatro reglas que no se rompen

**No mirar rentabilidad.** Todo lo hecho mide estructura. En cuanto se mire si gana plata
se «gasta» la muestra y no hay vuelta atrás. Todos los archivos llevan
`CAMPAIGN_OUTCOMES_OPENED=false`.

**No commitear en la rama desde la que corre un barrido.** El programa compara la versión
al empezar contra la versión al terminar; si cambió, invalida el resultado. Ya pasó una
vez. **Usá otra rama para escribir mientras algo corre.**

**No tocar las 19 sesiones apartadas.** Están en `specs/bt2_absorption_gate1_split_v1.json`,
reservadas para una prueba futura.

**No mergear ni rebasear sin autorización explícita de Nico.**

---

## 3. Configurá tus rutas

Todo lo pesado vive **fuera del repo**. En esta máquina:

```
C:/Users/nicoc/OneDrive/Documentos/DataNT8      cintas de ticks + salidas de barrido
C:/Users/nicoc/OneDrive/Documentos/NinjaTrader 8   base de NT8 (ticks, replay L2)
C:/ProyectosQuant/cryptodata                    descargas de Binance
```

**En la otra máquina, exportá una variable y usala en todos los comandos:**

```bash
export DATA="/ruta/a/DataNT8"          # Linux/Mac/Git-Bash
$env:DATA = "C:\ruta\a\DataNT8"        # PowerShell
```

**Verificá que las cintas estén:**

```bash
ls "$DATA"/*.Last.txt
```

Deberías ver `GC 02-26`, `GC 04-26`, `GC 06-26`, `GC 08-26`, `GC 12-25`, y varias de `6E`,
`ES`, `NQ`, `YM`. **Si faltan, se re-exportan desde NT8** — no hay que transferirlas.

---

## 4. Estado exacto, hoy

| | |
|---|---|
| rama principal | `foundation/f0b-compatibility-probe` @ `7fbab53` |
| local vs remoto | **iguales**, nada pendiente de subir |
| pruebas | 27 fallan, **las mismas de antes** |
| barrido de parámetros | **interrumpido por apagado**, 64 de 99 en un contrato |
| medición de rentabilidad | **no corrida, decisión pendiente** |

### Ramas vivas

| rama | qué es | ¿mergear? |
|---|---|---|
| `foundation/f0b-compatibility-probe` | la principal | — |
| `docs/handoff-2026-08-25` | este documento + análisis | sí, cuando quieras |
| `fix/sweep-finalize-contract-scope` | ya integrada | ya está |
| `work/crypto-context-foundation-20260824` | crypto, PR #14 | **no**, CI 7/10 |
| `research/gate-regime-context` | cimiento roto | **no** |

---

## 5. Retomar el barrido interrumpido

Se cortó con **64 de 99** configuraciones hechas para `GC 02-26`. **No se perdieron.**

### La única condición que importa

Cada resultado parcial guarda **con qué versión del código se calculó**. Si retomás desde
otra versión, el programa se niega a mezclar y **recalcula desde cero**.

Los 64 se calcularon con **`7fbab53`**. Entonces:

```bash
git checkout 7fbab53
```

Si estás en otra versión funciona igual, pero perdés **~13 horas** de cálculo.

### El comando

```bash
python tools/bt2_absorption_param_sweep.py run --stage all --resume \
  --max-hours 8 --contracts "GC 02-26" \
  --data-dir "$DATA" \
  --output "$DATA/sweep_7fbab53_GC02-26"
```

Y lo mismo para `GC 04-26`, `GC 06-26` y `GC 08-26`, **cada uno con su propia carpeta de
salida** (`sweep_7fbab53_GC04-26`, etc.).

### Cuánto tarda de verdad

**Días, no horas.** Medido, no estimado:

```
64 configuraciones          ->  ~13 horas
UNA SOLA de ellas           ->   6,7 horas
las 396 totales             ->  varios dias
```

Las configuraciones que aflojan filtros generan tantas señales que el procesamiento
explota. **Se puede cortar y retomar cuantas veces haga falta.**

### Si algo sale mal

| síntoma | qué es | qué hacer |
|---|---|---|
| `PAUSED_BY_MAX_HOURS` | llegó al límite de horas | **no es error**, volvé a correr con `--resume` |
| `INVALID_PROVENANCE` | commiteaste en esa rama mientras corría | correr desde un worktree en el commit de los parciales |
| `DIAGNOSTIC_REAGGREGATION_MIXED_CODE` | parciales de versiones distintas | idem |
| `faltan N de M parciales` | conjunto incompleto | seguí corriendo con `--resume` |

---

## 6. Qué se sabe hasta ahora

Cuatro cosas, en orden de importancia. Cada una tiene su documento.

### 6.1 Las dos versiones coinciden — pero se probó en un solo punto

Firmado como `FINAL_PUERTA0_SIGNED`. **Se probó sólo con los valores por defecto de las
21 perillas.** Esa limitación mordió: ver 6.2.

→ `docs/research/FIRMA_FINAL_PUERTA0_BT2_ABSORPTION_2026-08-23.md`

### 6.2 Apareció y se arregló un defecto real de paridad

**`MinExportVolume`**: la versión C# la usa para filtrar, la Python **la leía y la tiraba**.
Invisible en seis auditorías porque con el valor por defecto el filtro nunca se activa.

Arreglado. Se agregaron **9 pruebas fuera de los valores por defecto**, de las cuales **3
fallan sobre el código sin arreglar**. Se barrieron las 21 perillas buscando el mismo
patrón: **era la única**.

→ `docs/research/SWEEP_OAT_51_RESULTADO_2026-08-24.md`

### 6.3 Las perillas se dividen en tres grupos

| grupo | qué hace | cuántas |
|---|---|:-:|
| cambian **cuántas** señales | lo esperable | 15 |
| cambian **cuánto vive** cada señal | invisible si sólo contás | 3 |
| no hacen nada | decorativas | 3 |

El grupo del medio fue el hallazgo: parecen decorativas porque el conteo no las ve, pero
una hace que los toques pasen de 9.400 a **223.000**.

### 6.4 ⚠ Los efectos NO se componen

Lo más importante y lo más reciente. Predije combinaciones suponiendo que las perillas son
independientes y comparé contra lo medido: **falla por hasta 1.537×, en las dos
direcciones.**

**Consecuencia: las magnitudes del barrido de a una perilla valen SÓLO en el punto del
headline.** No son propiedades de la perilla.

→ `docs/research/SWEEP_INTERACCIONES_PARCIAL_2026-08-25.md`

---

## 7. Lo que está bloqueado, y en quién

| qué | quién |
|---|---|
| **Decidir si se corre la medición de rentabilidad** | **Nico** |
| Terminar el barrido (99 × 4) | tiempo de máquina |
| Abrir el PR borrador de `fix/...` | falta `gh` o token de GitHub |
| Actualizar descripción del PR #14 | idem |
| Cuántas sesiones de Market Replay hay para Bitcoin | Nico, en NT8 |

---

## 8. Si vas a tocar crypto

Tres cosas medidas que **no conviene volver a descubrir**:

**Binance dejó de publicar el mejor precio de compra/venta después del 2024-03-30.** Las
operaciones sí están al día. **No existe archivo gratuito de libro de órdenes descargable
en bloque** — se probaron cuatro fuentes y las cuatro fallaron al intentarlas de verdad.

**Eso resultó no importar.** Las operaciones ya traen **quién fue el agresor** como dato
del exchange, y el indicador sólo usaba el libro para adivinar eso. La cobertura pasó de
320 días a **2.542**.

**El tamaño mínimo de precio cambia con el tiempo.** SOL pasó de `0.001` a `0.01` el
2024-10-14; usar el valor actual sobre datos viejos daba **85 % de precios «inválidos»**
que no lo eran.

> ⚠ **Todo lo de crypto vive en otra rama y NO está mergeado.** Para verlo:
>
> ```bash
> git checkout work/crypto-context-foundation-20260824
> ```
>
> Ahí están `docs/research/CRYPTO_FUENTES_DISPONIBILIDAD_2026-08-24.md`,
> `docs/research/CRYPTO_DATA_INTAKE_2026-08-24.md` y
> `specs/binance_tick_size_history.json`. **En `foundation` no existen.**

---

## 9. Coordinación

Hay una página de Notion llamada **`canal`** con el registro compartido con el auditor.
**Leerla antes de escribir**, y agregar al final sin tocar entradas previas. El formato
está en la propia página.

---

## 10. Mapa de documentos

Sólo si necesitás profundidad. **No hace falta leerlos para arrancar.**

```
docs/ARRANQUE.md                                     <- este archivo
docs/HANDOFF_2026-08-25.md                           version narrativa del traspaso
docs/research/SWEEP_OAT_51_RESULTADO_2026-08-24.md   barrido de a una perilla
docs/research/SWEEP_INTERACCIONES_PARCIAL_...        por que no se componen
docs/research/FIRMA_FINAL_PUERTA0_...                la firma de equivalencia
docs/research/CRYPTO_FUENTES_DISPONIBILIDAD_...      qué hay gratis de crypto  (rama crypto)
docs/nt8_indicator_parity_contract.md                reglas de comparación
specs/bt2_absorption_gate1_v1.json                   la prueba pendiente, congelada
manifests/sweep/GC02-26_7fbab53_extract.json         conteos del barrido, 66 KB
```

---

## 11. Cuatro trampas en las que ya caí

Están acá porque el próximo va a tener las mismas tentaciones.

**El número más visible no es todo el asunto.** Conté doce perillas «decorativas» mirando
cuántas señales producían. Eran tres; las otras nueve cambiaban **cuánto vivía** cada señal.

**Comparar cosas que no son comparables.** Medí pruebas en dos carpetas con distintos
archivos de datos y reporté una regresión que no existía. **Misma carpeta, mismos datos, o
no compares.**

**Estimar tiempos sin medir.** Erré por factores de 3× y 5×, siempre extrapolando desde el
caso rápido. La dispersión real entre configuraciones es de **13×**.

**Aislar el árbol de archivos no aísla el HEAD de git.** Trabajé en un worktree separado
creyendo que estaba aislado y le commiteé a la rama desde la que corría un barrido. El
programa lo detectó y anuló el resultado.

---

## Si sólo leés una línea

**El indicador está casi listo para ser medido, y nunca se midió. Todo lo demás es
preparación.**
