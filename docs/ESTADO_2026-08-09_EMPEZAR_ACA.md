# EMPEZAR ACÁ — estado al 2026-08-09

**Rama:** `foundation/f0b-compatibility-probe` · **Remoto:** `github` (no `origin`)
**Outcomes leídos hasta hoy: CERO.** Holdout `2026-07-01 → 12-31` **intacto**.

> Este documento reemplaza a los `ESTADO_*` anteriores como punto de entrada.
> Los demás quedan como registro histórico.

---

## 1. Lo único que falta para probar el edge

**El runner de outcomes (Paso 6).** No existe. Todo lo demás está sellado.

Diseño vigente: **[`E-R1_v0.3.1_SELLO_2026-08-09.md`](predictions/E-R1_v0.3.1_SELLO_2026-08-09.md)**
← *el único documento ejecutable; los `v0.3` son historia.*

```
H1  BigTrap2  T=34  ·  f = 2,11 ev/sesion  ·  MDE ~0,797  ·  margen 3,47x
poblacion   primeros toques post-sep_min=120, orden B
validez     k_T > 0  Y  first_touch_bar > barra_de(k_T)      [estricto]
direccion   trapped_buyers -> CORTO ;  trapped_sellers -> LARGO
ENTRADA     close de la barra del primer toque
SALIDA      close de la barra de CloseThrough, o ultimo precio de sesion CT
estimando   expectativa neta por evento, friccion 2,768 ticks DENTRO
inferencia  remuestreo por sesion, bloque = dia CT
decision    VIVE / MUERE / GRIS=MUERE
```

El runner debe emitir `outcomes_accessed: true`. **Será la primera vez en el
proyecto.** Después de eso ya no se retoca nada: si aparece un defecto, H1 muere.

## 2. Tres cosas que NO hay que reaprender

**2.1 `is_bull = True` → `trapped_buyers` → operación BAJISTA.** El flag nombra
quién quedó atrapado, no la dirección del trade. Invertirlo invierte la hipótesis
y **nada en el resultado lo delataría**. Verificado en `bigtrap2.py:266` y `:274`.

**2.2 `first_touch_ms` es FIN DE BARRA**, no el instante del toque
(`bigtrap2.py:174` compara el rango de la barra cerrada contra la zona). Por eso
la entrada es al `close`, y por eso la validez se compara **por barra**. Fue
`DEFECTO 001`.

**2.3 La salida es asimétrica.** `CloseThrough` dispara del lado en contra del
trade: pérdida acotada, ganancia abierta hasta el cierre de sesión. Distribución
sesgada a la derecha → **un `win rate` bajo NO refuta la hipótesis**, porque el
estimando es expectativa neta.

## 3. Estado del barrido de `T` (corregido, orden B)

| `T` | 3 | 8 | 13 | 21 | **34** |
|---|---:|---:|---:|---:|---:|
| `f`/sesión | 6,38 | 5,54 | 4,52 | 3,38 | **2,11** |
| margen | 5,8× | 5,4× | 5,0× | 4,3× | **3,47×** |

**Ninguna celda es ciega.** `T=34` es el pre-registrado y el que está sellado.
`T=3` es el argmax y **§7 Paso 3 lo prohíbe** — no volver sobre eso.

## 4. Discrepancias abiertas (no bloquean, no las perdimos)

| | qué | dónde |
|---|---|---|
| 1 | `1,60×` (spec) contra `7,0×` (spike-in) a `f=10` | `E-R1 v0.3.1` §8 |
| 2 | `N_eff(f)` está tabulado, no reconstruido → los MDE son **interpolados** | ídem |
| 3 | `DESACUERDO_001` con Codex sobre la condición de validez | `docs/audits/` |
| 4 | `min_sessions=10` contra 6 sesiones de warm-up en `aVolCellPOI2` | `PASO1_RECUENTO_kT` |
| 5 | `Gaps2`: cae por mecanismo o por estadística — **sin responder** | ídem §5 |

## 5. Configuración específica de máquina

```bash
export NT8_CUSTOM="C:\\Users\\<usuario>\\...\\NinjaTrader 8\\bin\\Custom"
```

Necesario sólo para `tools/compilar_nt8_cs.py`. **Nada del Paso 6 lo requiere.**

En esta máquina NT8 vive en `OneDrive\Documentos`, no en la ruta `E:\` que
aparece en documentos viejos.

## 6. Reglas del proyecto que siguen vigentes

- Git **sólo** en `C:\ProyectosQuant\EdgeLab`. Nunca `git add .`.
- No commitear `data/`, `TickData/`, parquets, cachés, venvs, `.env`.
- No tocar el commit base `cde6d93` ni el tag `baseline-pre-foundation`.
- No abrir el holdout. No llenar H1–H3 a mano. No agregar hashes a
  `APPROVED_G2_CONTRACT_SHA256S`.
- **Las contradicciones se registran y se reportan, nunca se resuelven en
  silencio.**

## 7. Advertencia de método — ganada a golpes el 2026-08-09

Tres errores en un día, **todos con la misma forma**:

| | lectura plausible | qué la desmintió |
|---|---|---|
| 1 | «dos brazos son dos hipótesis» | la aritmética del estimando |
| 2 | «margen = efecto/MDE» | la tabla del spike-in |
| 3 | «el primer toque es el instante del toque» | el código del kernel |

Ninguno se detectó revisando el razonamiento. **Los tres cayeron al abrir el
archivo por otro motivo.**

> **Antes de cada afirmación que sostenga el diseño, abrir la fuente.**
> Recordar un documento no es verificarlo.
