# E-R1 v0.3.1 — SELLADO (reemplaza al sello de v0.3, suspendido por DEFECTO 001)

**Fecha:** 2026-08-09 · **CERO OUTCOMES OBSERVADOS.** Holdout intacto.
**Autoriza:** Nico — *«las decisiones tomalas vos y de las tareas también
encargate vos»* + *«revisá todo bien y avanzá con eso»*.
**Reemplaza:** `E-R1_v0.3_SELLO_2026-08-09.md`, suspendido por
[`DEFECTO_001`](E-R1_v0.3_DEFECTO_001_precio_de_entrada.md).

> **Este es el documento vigente.** Los anteriores se conservan como registro y
> **no deben ejecutarse**.

---

## 1. Qué cambió respecto de v0.3

`DEFECTO 001` encontró que `first_touch_ms` es **fin de barra**, no el instante
del toque (`bigtrap2.py:174` compara el rango de la barra cerrada contra la zona).
Eso dejaba tres parámetros sin especificar, cuando yo había afirmado que no había
ninguno.

Los tres se cierran con **una sola regla**: *usar únicamente precios e instantes
conocibles en el momento de decidir.* Ninguno introduce umbral, ventana ni
constante nueva.

| | v0.3 (mal) | **v0.3.1** |
|---|---|---|
| entrada | «el retorno a la banda» — **no ejecutable** | **`close` de la barra del primer toque** |
| salida | «muerte de zona o cierre de sesión» — sin precio | **`close` de la barra de `CloseThrough`, o último precio de la sesión CT** |
| validez | `i_toque > k` en índices de tick — **contaminada** | **`first_touch_bar` estrictamente `>` barra de `k_T`** |

### 1.1 El impacto medido de la corrección de validez

Re-medido con la comparación por barra:

```
eventos con excursion valida    776  ->  755      (-21, -2,7 %)
f (orden B)                    2,13  -> 2,11      (-1,2 %)
```

**El defecto era real y su magnitud es chica.** 21 casos en los que la excursión y
el toque caían en la misma barra. La corrección se aplica igual: la magnitud no
decide si algo estaba mal especificado.

## 2. El diseño sellado

```
H1   BigTrap2   T = 34   direccion nativa
──────────────────────────────────────────────────────────────────────
universo     201 sesiones, 4 contratos 6E, corte 2026-06-30
             holdout 2026-07-01 -> 12-31 SELLADO; INC-005 en cuarentena
poblacion    primeros toques post-sep_min=120, ancla first_touch_ms
disponib.    bar_close: disp = bar_end[created_bar]; barra 0 descartada
validez      k_T > 0  Y  first_touch_bar > barra_de(k_T)     [estricto]
composicion  orden B: exigir validez, DESPUES decongestionar
f            2,11 eventos/sesion    MDE ~0,797    margen 3,47x
             con el +11,8 % del barrido de resolucion: 3,11x   -> NO ciega
direccion    trapped_buyers -> CORTO ; trapped_sellers -> LARGO
             (is_bull=True es trapped_buyers y opera BAJISTA -- ver §3)
ENTRADA      close de la barra del primer toque
SALIDA       close de la barra de CloseThrough, o ultimo precio de sesion CT,
             lo que ocurra primero
censura      los truncados por fin de sesion ENTRAN con su resultado realizado
estimando    expectativa neta por evento, friccion 2,768 ticks DENTRO
inferencia   remuestreo/agrupacion por sesion; bloque minimo = dia CT
             sensibilidad equal-weight diaria; diferencia material SE DECLARA
decision     VIVE: IC ajustado > 0 | MUERE: IC < 0 | GRIS: contiene 0 -> MUERE
multiplic.   M_eff 21,2 -> ~106, z 3,50; holgura declarada, NO aprovechada
```

## 3. La trampa de nomenclatura, repetida acá a propósito

```
is_bull = True  ->  trapped_buyers  ->  zona ARRIBA  ->  operacion BAJISTA
```

El flag nombra **quién quedó atrapado**, no la dirección del trade. Verificado en
`bigtrap2.py:266` y `:274`. **Invertirlo invierte la hipótesis entera y nada en el
resultado lo delataría.**

## 4. La asimetría de la salida, declarada antes de outcomes

`CloseThrough` dispara cuando el precio cierra **atravesando** la zona — para
`trapped_buyers`, cerrando por encima: el lado en contra del trade.

```
perdida  -> acotada por la altura de la zona + deslizamiento
ganancia -> abierta hasta el cierre de sesion
```

Distribución **sesgada a la derecha**. Dos consecuencias declaradas:

1. **Un `win rate` bajo NO refuta la hipótesis.** El estimando es expectativa
   neta, no proporción de aciertos.
2. **El sesgo afecta la cobertura del IC bootstrap.** Se **reporta** junto al
   resultado; no se promedia.

## 5. Lo que el sello NO hace

- **No abre el holdout.**
- **No adjudica H1.**
- **No permite retocar nada después del primer outcome.** Si aparece un defecto
  nuevo *después* de mirar resultados, se registra y **H1 muere**. La reparación
  de hoy fue legítima **sólo** porque no se había observado un solo outcome.

## 6. Lo que sigue — Paso 6, el runner de outcomes

No existe. Es lo único que falta. Debe:

1. tomar la población exacta de `f_ambos_filtros.py` (orden B, `T=34`);
2. entrar al `close` de la barra del primer toque, con el signo del §2;
3. salir al `close` de `CloseThrough` o al último precio de la sesión;
4. restar **2,768 ticks dentro de cada evento**;
5. remuestrear por sesión, bloque = día CT;
6. publicar todos los descartes, la censura y la asimetría;
7. emitir `outcomes_accessed: true` — **es la primera vez en el proyecto**.

## 7. Advertencia — tres errores hoy, la misma forma

| # | lectura plausible | qué la desmintió |
|---|---|---|
| 1 | «dos brazos son dos hipótesis» | la aritmética del estimando |
| 2 | «margen = efecto/MDE» | la tabla del spike-in |
| 3 | «el primer toque es el instante del toque» | el código del kernel |

En los tres tomé algo por cierto **sin abrir la fuente**, y **ninguno lo detecté
revisando mi razonamiento**: los tres cayeron al ir a leer el archivo por otro
motivo.

**Regla operativa, para el Paso 6 y para quien siga:** antes de cada afirmación
que sostenga el diseño, abrir la fuente. Recordar un documento no es verificarlo.

## 8. Discrepancias abiertas, que no bloquean

- **`1,60×` (spec) contra `7,0×` (spike-in)** a `f=10`. Uso el del spike-in porque
  reproduce aritméticamente. Defecto documental sin resolver.
- **`N_eff(f)` está tabulado, no reconstruido.** Los MDE de acá son
  **interpolados**. El número exacto exige rehacer el bootstrap.
- **`min_sessions=10` contra 6 sesiones de warm-up observadas** en `aVolCellPOI2`.
  No afecta a H1.
