# Paso 1 cerrado — recuento `k_T`, y dos hallazgos que no buscaba

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado · Sin NT8
**Artefacto:** `diag/tasa_senales/recuento_kT.json`
**Universo:** 201 sesiones · 4 contratos 6E · corte 2026-06-30
**Alcance corrido:** `BigTrap2`, `aVolCellPOI2`. **`Gaps2` no se corrió** (§4).

---

## 1. Chequeo de la predicción registrada

El módulo dejó escrita, antes de medir: *«la frecuencia corregida no se mueve más
de ~0,2 % en esas celdas»*, con regla de lectura — *«si difiere mucho, buscar un
defecto en este código antes que anunciar un hallazgo»*.

| indicador | `T` | declarada | medida (201 ses) | Δ | |
|---|---|---:|---:|---:|---|
| `BigTrap2` | 34 | 0,14 % | **0,111 %** | 0,03 pp | **DENTRO** |
| `aVolCellPOI2` | 21 | 0,00 % | **0,473 %** | 0,47 pp | **EXCEDE** |

### 1.1 Apliqué la regla de lectura. No hay defecto.

El desglose por contrato explica la discrepancia sin apelar a ruido:

| contrato | zonas | `k_T==0` a `T=21` |
|---|---:|---:|
| 6E_03-26 | 2.988 | 0,54 % |
| 6E_06-26 | 2.922 | 0,72 % |
| **6E_09-26** | **304** | **0,00 %** |
| 6E_12-25 | 2.876 | 0,21 % |

La cifra declarada salía de `sonda_alejamiento_cero__6E_09-26_08s.json` — **8
sesiones del contrato 09-26**. Y sobre ese contrato el censo completo devuelve
**exactamente 0,00 %**.

**El valor declarado no era erróneo: se reprodujo idéntico sobre su propia
población.** Lo que falló fue extrapolarlo, porque 09-26 es el contrato **más
chico del universo** —304 zonas contra ~2.900— y resultó estar genuinamente en
cero.

Eso es una **verificación interna fuerte del código**, no un defecto: dos
mediciones independientes coinciden al decimal sobre la misma población.

**Se registra igual como predicción excedida.** La banda era ~0,2 pp y se excedió.

## 2. Hallazgo no buscado — los 24 días sin eventos de `aVolCellPOI2`

No están dispersos. Son **4 rachas de exactamente 6 sesiones consecutivas**:

```
2025-09-12 → 2025-09-19     inicio del universo
2025-12-12 → 2025-12-19     roll de contrato
2026-03-13 → 2026-03-20     roll de contrato
2026-06-12 → 2026-06-19     roll de contrato
```

**Causa, verificada en el código:** `recuento_kT.py:178` llama `mod.run(tk, b, …)`
**una vez por parquet de contrato**, así que el kernel arranca cada contrato con
**historia vacía**. Y `avolcellpoi2.py:27` documenta la guarda: *«sin >=
MinSessions sesiones ni >= MinCellSamples celdas, cache = None»*.

**Es un artefacto de cómo medimos, no del indicador.** En producción el kernel
arrastra historia a través del roll: habría **un** warm-up, no cuatro.

### 2.1 Y va en la dirección contraria a la intuición

El censo **subestima** al indicador. Sus 6,71/sesión promedian 201 sesiones
incluyendo 24 ceros estructurales; sobre las **177 activas** son **7,59/sesión**,
~13 % más. Pasa `MIN_STUDENTIZED_SESSIONS = 160` con cualquiera de los dos.

> **Detalle sin cerrar, marcado.** La guarda por defecto es `min_sessions = 10`
> pero el apagón observado es de **6** sesiones. La explicación plausible es que
> cada parquet trae sesiones anteriores al inicio del universo que calientan el
> kernel sin ser visibles en el conteo — **no verificado**. Registrado, no
> resuelto.

### 2.2 Y también disuelve la anomalía del §1.1

6E_09-26 tiene 304 zonas en 13 sesiones = 23,4/ses, la mitad que los otros
contratos. Pero **6 de esas 13 son warm-up**: sobre las 7 efectivas son
**43,4/ses**, en línea con 49,8 de 03-26. La anomalía era el mismo warm-up.

## 3. Regla de lectura de estas columnas — importante

**El censo NO aplica `sep_min`.** Verificado: no aparece en el módulo. Su
población son **todas las zonas** (`r["zones"]`), no los primeros toques
post-`sep_min` que la enmienda declara autoritativos.

Por eso los conteos absolutos —17.192 y 9.090— **no son la población de E-R1** y
no deben mezclarse con las tasas de PRED-007.

**Lo que sí es transportable es la fracción**, que es un cociente independiente de
la población. La frecuencia corregida se obtiene aplicándola a la tasa
autoritativa:

```
f_corregida = f_autoritativa × (1 − frac_kT0)
```

## 4. Tabla del Paso 2 — las columnas que faltaban

| indicador | clase | `T` | sesiones | zonas (censo) | `k_T==0` | excursiones válidas | retornos válidos | **f corregida/ses** |
|---|---|---:|---|---:|---|---:|---:|---:|
| `BigTrap2` | `bar_close` | 34 | 201 (201 act.) | 17.192 | 19 · 0,111 % | 17.173 | 1.655 | **9,07** |
| `aVolCellPOI2` | `bar_close` | 21 | 201 (177 act.) | 9.090 | 43 · 0,473 % | 9.047 | 1.591 | **6,68** |

Columnas ya disponibles de otros artefactos: días sin eventos (0 y 24, §2); MDE
1,14 a `f=1`; paridad en `docs/parity_coverage/`; **gate direccional** resuelto
hoy en `DECISION_2026-08-09_direccion_y_alcance_de_EXPLORE-001.md`.

### 4.1 La corrección es económicamente nula

`9,08 → 9,07` y `6,71 → 6,68`. **`k_T == 0` no mueve el diseño.** Que es lo que la
predicción anticipaba, y se cumple aun donde la banda se excedió.

## 5. Alcance declarado — `Gaps2` no se corrió, y por qué

Lancé el censo con `Gaps2` incluido **sabiendo que está rechazado por el
invariante**. A las ~33 min de CPU el proceso estaba en **40 MB residentes contra
1.997 MB paginados** con 619 MB libres: paginando, igual que la corrida de 10,3 h
de PRED-007.

Lo corté y relancé con los dos indicadores pertinentes. **Terminó en 40
segundos.** El costo era íntegramente `Gaps2`.

**Es el mismo error que registré en PRED-007 §7 y lo repetí.** Log de la corrida
abortada preservado como `kT_con_gaps2_ABORTADO.log`.

**Consecuencia:** la *segunda pregunta* del módulo —si los retornos de `Gaps2`
vienen de zonas genuinamente vacías, o sea si cae **por mecanismo o por
estadística**— **queda sin responder**. No la responden los números de
`BigTrap2` / `aVolCellPOI2`, y no la voy a presentar como si lo hicieran. Es
corrible aparte, sola, en una máquina ociosa.

## 6. La fracción desde zona vacía, para los dos que sí corrieron

De los retornos válidos, cuántos vienen de una zona que **no** contenía al precio
en `i0`:

| indicador | `T=1` | `T=5` | `T=13` | `T=21` | `T=34` |
|---|---:|---:|---:|---:|---:|
| `BigTrap2` | 76,2 % | 93,8 % | 94,8 % | 94,8 % | **94,7 %** |
| `aVolCellPOI2` | 52,9 % | 70,3 % | 73,1 % | **74,5 %** | 74,4 % |

En sus celdas de diseño los dos están altos y estables. **No es la respuesta a la
pregunta de `Gaps2`** —ése era el caso patológico con 75 % de zonas ya conteniendo
al precio— pero sí dice que estos dos no comparten esa patología.

## 7. Qué decido y qué no

**Decido** cerrar el Paso 1 con el alcance del §5 declarado, y registrar la
predicción como **excedida en una celda con causa identificada y sin defecto**.

**No resuelvo** el `min_sessions` 10 contra 6 del §2.1.

**No respondo** la segunda pregunta sobre `Gaps2`, y lo digo en vez de disimularlo.

**No toco** outcomes, holdout ni NT8.
