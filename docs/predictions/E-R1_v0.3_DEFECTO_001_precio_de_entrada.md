# ⛔ DEFECTO 001 sobre E-R1 v0.3 — el precio de entrada no era ejecutable

> ## → REEMPLAZADO por [`E-R1 v0.3.1`](E-R1_v0.3.1_SELLO_2026-08-09.md)
> DEFECTO 001 cerrado ahi. **Este documento es registro historico: NO ejecutar.**

**Fecha:** 2026-08-09, horas después del sello · **CERO OUTCOMES OBSERVADOS.**
Holdout intacto.
**Hallado por:** revisión pedida por Nico — *«revisá todo bien»*.
**Efecto:** el sello queda **suspendido**. `E-R1 v0.3` **sí tenía parámetros
libres**, contra lo que afirmé.

---

## 1. El defecto

`edgelab/bridge/indicators/bigtrap2.py:174`, dentro de `update_zones(b, t_ns)`,
que corre **al cierre de cada barra**:

```python
touched = hi >= z["lo"] and lo <= z["hi"]     # hi/lo = rango de la BARRA
```

El toque se detecta comparando **el rango de la barra ya cerrada** contra la zona,
y `ZONE_TOUCHED` se estampa con `t_ns` = **fin de barra**.

**Consecuencia:** `first_touch_ms` **no es el instante en que el precio tocó la
banda**. Es el cierre de la barra que la tocó en algún momento de su recorrido.

## 2. Por qué invalida lo que sellé

E-R1 §6 declara la entrada como *«el retorno a la banda»*, lo que implica entrar
**al borde de la zona**.

**No es ejecutable.** En el instante en que el toque es conocido, la barra ya
cerró y el precio está en `close`, que puede estar a varios ticks del borde.
Entrar al borde sería usar información que no se tenía: **look-ahead en el precio
de entrada**, de magnitud comparable a la fricción de 2,768 ticks.

Y afirmé literalmente *«sin parámetros libres»*. **Era falso.** Faltaban tres:

| | qué faltaba | consecuencia |
|---|---|---|
| 1 | **precio de entrada** | el estimando se mide desde un precio no especificado |
| 2 | **precio de salida** en `CloseThrough` | ídem, y `CloseThrough` también es evento de cierre de barra |
| 3 | **resolución intra-barra** de la condición de validez | ver §3 |

## 3. El tercero contamina la `f` que medí

Mi condición de validez es `i_toque > k`, con
`i_toque = searchsorted(ts, first_touch_ms)`. Como `first_touch_ms` es **fin de
barra**, ese índice **no es el del toque real**: es posterior.

Si en una misma barra el precio completa la excursión **y** toca la zona, el
`i_toque` de fin de barra supera a `k` y el evento **cuenta como válido aunque el
toque real haya precedido a la excursión**.

> **Mi condición es más permisiva de lo que declaré**, y en la dirección que
> infla `f`. **`f = 2,13/sesión` es una cota superior, no la medida.**

Irónicamente, es una versión más chica del mismo defecto que le objeté a Codex.

## 4. Por qué esto se repara y no mata a H1

El documento de sello dice: *«si algo resulta mal especificado se registra como
defecto y H1 muere; no se ajusta»*. Esa regla protege contra **reparar el diseño
con resultados a la vista**.

**No hay resultados a la vista.** Cero outcomes leídos, holdout intacto, y el
runner del Paso 6 ni siquiera existe. Enmendar ahora es exactamente para lo que
sirve una pre-registración: **se corrige antes de mirar, no después.**

Si el defecto hubiera aparecido después del primer outcome, H1 moriría.

## 5. La enmienda — sigue sin parámetros elegidos por nosotros

```
ENTRADA   close de la barra que produjo el primer toque
          = el unico precio conocible en el instante de la senal

SALIDA    close de la barra en que dispara CloseThrough,
          o ultimo precio de la sesion CT, lo que ocurra primero

VALIDEZ   la barra del primer toque debe ser ESTRICTAMENTE POSTERIOR
          a la barra que contiene la excursion k_T
```

Las tres se derivan de una sola regla: **usar únicamente precios e instantes
conocibles en el momento de decidir.** Ninguna introduce un umbral, una ventana ni
una constante nueva.

La tercera es **más restrictiva** que la que usé. Baja `f` por debajo de 2,13.
**Cuánto, no lo sé todavía: hay que volver a medir.**

## 6. Estado

| | |
|---|---|
| sello de E-R1 v0.3 | **SUSPENDIDO** |
| `f = 2,13/sesión` | **cota superior, no medida** |
| margen 3,49× | **recalcular** con la `f` corregida |
| runner de outcomes | **no construir hasta cerrar esto** |
| outcomes / holdout | **intactos** |

## 7. Lo que hay que hacer, en orden

1. Corregir `f_ambos_filtros.py` con la condición de validez del §5 —comparar
   **barras**, no timestamps de fin de barra— y volver a medir `f`.
2. Recalcular el margen a esa `f`. **Si cae por debajo de ~1, la celda sí es
   ciega** y ahí sí habría que revisar `T` o dejar morir H1.
3. Re-sellar E-R1 con las tres especificaciones del §5 incorporadas.
4. Recién entonces, el runner del Paso 6.

## 8. Advertencia — el patrón se repitió por tercera vez

Los tres errores de hoy tienen **la misma forma**:

| # | lectura plausible | qué la desmintió |
|---|---|---|
| 1 | «dos brazos son dos hipótesis» | la aritmética del estimando |
| 2 | «margen = efecto/MDE» | la tabla del spike-in |
| 3 | «el primer toque es el instante del toque» | el código del kernel |

**En los tres tomé algo por cierto sin contrastarlo contra su fuente**, y en los
tres el error sobrevivió a mi propia revisión hasta que fui a mirar el archivo.

Los tres se detectaron antes de mirar un solo outcome — pero **ninguno lo detecté
por revisar mi razonamiento**: los tres cayeron al ir a leer el código o la tabla
por otro motivo.

**Regla operativa que se sigue de esto:** antes de cada afirmación que sostenga el
diseño, abrir la fuente. Razonar sobre lo que uno recuerda de un documento no es
verificar.
