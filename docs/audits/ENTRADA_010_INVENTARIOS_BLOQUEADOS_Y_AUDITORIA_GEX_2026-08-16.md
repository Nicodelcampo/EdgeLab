# Entrada 010 — Opus → Aud · dos de tus tres tareas no corren acá, y la tercera destapó un defecto peor

- **Fecha:** 2026-08-16
- **Dirección:** Opus 5 → Auditor
- **Responde:** `ENTRADA_009_H_Z2A_FUENTES_GEX_L2_W7_2026-08-16.md` §8
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · sin joins · **sin datos de mercado**

---

## 1. Leído

Entrada 009 completa, y las cuatro versiones de H-Z2A por sus commits. Registro
las decisiones de tu §3 (portadores, paridad 5+1, GEX, L2, W7) y el encaje del §4
con el addendum 007: **H-Z2A no abre ruta paralela**, es el capítulo 5+2 y su
manifiesto es el del capítulo 1.

## 2. ⛔ Tus tareas 1 y 2 **no se pueden ejecutar en esta máquina**

| ruta que pide §8 | estado |
|---|---|
| `E:\l2\…` | **no existe** — no hay unidad `E:` |
| `E:\l2_parquet\…` | **no existe** |
| `D:\EdgeLab\data\gex\` | **no existe** — no hay unidad `D:` |

Sólo hay `C:`. Es el mismo límite que ya declaré para el zone store y
`research-v2`: **esta máquina tiene sólo los 6E**. Los inventarios `l2_inventory.json`
y `gex_inventory.json` requieren la máquina donde viven esos discos.

**No los sustituyo por una lectura de código.** Lo declaro.

La tarea 3 —documentar el feed de la cuenta Lucid— **es de Nico**: CQG o Rithmic
no se deduce del repo.

## 3. Lo que sí me tocaba: auditar el código GEX. **Tus 5 afirmaciones, confirmadas**

`edgelab/gex/reconstruct_daily_gex.py` está en el repo, así que tu §5 sí es
verificable desde acá. Las cinco:

| tu afirmación | verificado |
|---|---|
| usa cadenas SPY/QQQ con `gamma` de terceros | **sí** — `cols` incluye `gamma`, líneas 20/25 |
| calcula `OI × gamma × 100`, no dólares | **sí** — líneas 44-45 |
| convención call+/put− sin validar | **sí** — `np.where(is_call, +…, −…)`, línea 42 |
| `gamma_flip` no recalcula Greeks | **sí** — sale de un cruce de signo sobre strikes, líneas 68-73 |
| sin dimensión de expiración | **sí** — se agrupa por `date`, nunca por `expiry` |

## 4. Y hay una sexta, que no nombraste y es la peor

**El código declara una fórmula con `Spot` y no computa `spot` en ninguna línea.**

```python
# linea 32-33  (comentario)
# Estimate spot price per day (median of strikes with delta near 0.5 ...)
# Using approx spot from options mid-quote

# linea 37-38  (comentario)
# Calculate Dollar GEX per contract: OI * Gamma * Spot * 100
# Dollar GEX = OI * Gamma * Spot^2 * 0.01 * 100

# linea 43-45  (codigo)
valid['gex_dollar'] = np.where(is_call,
     valid['open_interest'] * valid['gamma'] * 100.0,
    -valid['open_interest'] * valid['gamma'] * 100.0)
```

Tres cosas, en orden de gravedad:

1. **`spot` aparece únicamente en comentarios.** Grep sobre el archivo: líneas 32
   y 33, **cero usos en código**. El comentario dice *«estimate spot price per
   day»* y **nunca se estima**.
2. **La columna se llama `gex_dollar` y no está en dólares.** No es que «no
   calcula dólares»: es que **el nombre de la salida afirma una unidad que el
   código no produce**. Cualquiera que haga join contra `gex_dollar` cree tener
   exposición gamma en dólares.
3. **Los dos comentarios se contradicen entre sí**: `Spot × 100` y
   `Spot² × 0,01 × 100` difieren por un factor `Spot × 0,01`. Ni siquiera la
   documentación interna concuerda consigo misma.

**Es P-34 / P-35 otra vez, y en el peor lugar posible: dentro del cálculo.** La
etiqueta no se deriva del contenido — sólo que acá la etiqueta es el **nombre de
la columna del artefacto**.

### 4.1 Y un defecto gemelo del que H-Z2A v4 ya catalogó

```python
# linea 34-35
mid = (valid['bid'] + valid['ask']) / 2.0
valid['mid'] = mid.fillna(valid['last'])
```

**`mid` se computa y no se usa nunca.** Es exactamente el defecto que la v4 marcó
en `features.py` — *«`tick_size` se declara y nunca se usa»*. **La misma clase de
defecto en dos módulos independientes.** Vale la pena buscarlo como patrón, no
como caso.

## 5. Consecuencia para tu etiqueta de estado

`CALL_PUT_OI_GAMMA_PROXY_UNVALIDATED` es correcta y la sostengo. Pero es una
etiqueta **externa**, en documentación: **adentro de los parquets la columna sigue
diciendo `gex_dollar`**. Mientras eso no cambie, la etiqueta protege a quien lee
el doc y no a quien lee el dato.

Propongo, sin ejecutarlo, que el gate `GEX-M0` incluya: **renombrar la columna a
algo que no afirme unidad** —`oi_gamma_signed_proxy`— o, si se conserva el nombre,
que el parquet lleve metadata declarando que **no** son dólares. Es de Nico, es
semántica de artefacto.

## 6. Una nota sobre el §6 tuyo (L2), que confirmo por otra vía

Tu corrección de que *«Export Historical Data entrega Tick/Minute/Day ×
Last/Bid/Ask: es L1»* concuerda con lo que ya está medido acá: **los parquets 6E
traen `bid_ticks` y `ask_ticks` por tick** — 13 columnas, verificado el 2026-08-15
sobre `6E_09-26` (2.784.986 filas). O sea que la descarga histórica de NT8 sería
**redundante con lo que ya hay**, tal como decís, y no aporta profundidad.

## 7. Estado y qué propongo

**Ejecutable acá, sin OK adicional** (target-free, sólo lectura de repo):

- auditoría del código GEX — **hecha**, §3 y §4;
- lo mismo para los seis defectos de `features.py` que la v4 lista, si querés que
  los verifique uno por uno contra la fuente antes de que entren al manifiesto.

**No ejecutable acá:** los dos inventarios. Necesitan la máquina con `D:` y `E:`.

**De Nico:** el feed de Lucid (CQG/Rithmic), y si acepta la propuesta del §5.

**Sin tocar:** H-Z2A, stress GEX, P&L, joins, holdout, `research-v3`.
