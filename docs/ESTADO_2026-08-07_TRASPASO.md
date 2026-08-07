# Estado al 2026-08-07 — traspaso entre máquinas

**Motivo:** bajón de tensión cortó los procesos en `E:\EdgeLab`. Se sigue desde
la otra máquina.
**Rama:** `foundation/f0b-compatibility-probe` — la única, como manda `CLAUDE.md`.
**Tip al cerrar:** `6dbe77e`

> **Lo que salió mal la vez anterior** (`docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`):
> 70 commits vivían en una rama que `CLAUDE.md` no mencionaba, y cada máquina
> leyó la suya. Las dos lecturas eran internamente coherentes. Este documento
> existe para que eso no se repita en otra forma.

## 0. Lo primero, siempre

```
.venv\Scripts\python tools\estado.py
.venv\Scripts\python tools\manifiesto_datos.py
```

El primero sale 1 si algo requiere atención. El segundo verifica que **esta
máquina tenga los MISMOS datos**, no sólo datos.

> **`data/` no viaja con el repo.** Está gitignoreado por política: son **31
> parquets, 16,9 GB**. Hay que copiarlos por fuera de git. El manifiesto no los
> transporta — da la certeza de estar copiando los mismos.
>
> Sin eso, dos máquinas pueden tener archivos distintos con el mismo nombre y
> nadie se entera. Es exactamente la falla que produjo **dos veredictos
> opuestos** con `manifiesto_universo.json` el 2026-08-05.
>
> La sonda ya publica `input_parquet_sha256`, así que una discrepancia se
> detecta igual — pero **después** de gastar el cómputo. Esto la detecta antes.

**Correlos antes de medir cualquier cosa.**

## 1. Qué quedó a medias, y por qué importa

**Una corrida de 40 sesiones de la sonda se cortó a mitad.** No dejó basura —la
promoción atómica funcionó: no hay temporales huérfanos y el artefacto anterior
quedó intacto— pero dejó una asimetría que **sí** puede engañar:

| artefacto | commit que lo generó |
|---|---|
| `sonda_alejamiento_cero__6E_09-26_08s.json` | `5ef3498` |
| `sonda_alejamiento_cero__6E_12-25_40s.json` | `5ef3498` |

Los dos están **restaurados a la pareja consistente** de `01a3981`. La corrida
de 8s alcanzó a regenerarse desde `d6b0495` y la de 40s no, así que en disco
quedaron dos versiones de código distintas; se revirtió a la pareja coherente en
vez de dejar una mezcla.

> `comparar_sondas.py` habría cazado la mezcla —`code_commit_start` y
> `generator_sha256` están en `IDENTIDAD_DEBE_COINCIDIR`— pero un artefacto
> incoherente en disco es una trampa para quien lo levante sin comparar.

**Consecuencia:** la pareja committeada es de `5ef3498`, que es **anterior a los
siete arreglos** de `d6b0495`. Hay que **regenerar las dos**.

## 2. Estado de los commits

| commit | qué es | estado |
|---|---|---|
| `01a3981` | pareja de evidencia 8s/40s | **evidencia íntegra, NO certificada** — el productor tenía rutas fail-open |
| `5ef3498` | commit fuente que la produjo | histórico |
| `d6b0495` | **los siete defectos que encontró la auditoría de código** | **es el commit fuente vigente** |
| `6dbe77e` | instrumento del Paso 1 + dos hallazgos propios | tip |

`5ef3498` y `01a3981` **no se reescriben**: quedan como historial. La
clasificación de `01a3981` es la que fijó el auditor —íntegra en sus archivos,
no certificada como canónica— y no cambió.

## 3. Qué hacer al retomar, en orden

```
1. tools\estado.py                              -> tiene que salir 0
2. pytest tests -m "not vectorbt" -q            -> 783 passed, 2 failed declarados
3. regenerar la pareja DESDE 6dbe77e:
     sonda_alejamiento_cero.py --contrato 6E_09-26_ticks.parquet --sesiones 8
     sonda_alejamiento_cero.py --contrato 6E_12-25_ticks.parquet --sesiones 40
   exit code CAPTURADO DIRECTO, sin pipe. La de 40s tarda ~45 min.
4. comparar_sondas.py A B --reporte ...          -> exige exit 0
5. commit EXCLUSIVO de evidencia (5 archivos, nada de código)
6. FRENAR
```

**El paso 6 no es burocracia.** El motivo lo dio el auditor y es mejor que el
mío: si aparece un defecto en las sondas después de haber empezado el recuento
`k_T`, se mezclan dos capas y deja de poder saberse qué resultado depende de qué
versión.

> Si el manifiesto congelado ya no resuelve alguna ruta —cambió el `.venv`, se
> movió un archivo— la sonda **aborta y no publica**. La salida correcta es
> correr una discovery nueva (`--descubrimiento`), regenerar el manifiesto con
> `congelar_dependencias.py` **en su propio commit**, y relanzar las dos. **No**
> ampliar el manifiesto a mano.

## 4. Después del commit de evidencia

`diag/tasa_senales/recuento_kT.py` está **escrito y sin correr**. Es el Paso 1 de
`docs/predictions/ESPEC_TEST_EXPLORE-001_v0.3.md` §7 y hace dos cosas:

1. El recuento con `k_T > 0` y `j > k_T`.
2. Responde si el mecanismo de `Gaps2` aplica a los eventos contados.

```
.venv\Scripts\python diag\tasa_senales\recuento_kT.py --workers 4
```

Costo estimado: sólo tres indicadores (sin `HFTZones2`, que es el 40 % del
cómputo y es reserva). **~3 h con `workers=4`**, autorizado a priori por Nico.

**Predicción registrada antes de correrlo**, en el docstring del módulo: la
frecuencia corregida **no se mueve más de ~0,2 %** en las celdas candidatas. Si
sale muy distinto, la lectura correcta es **buscar un defecto en ese código**,
no anunciar un hallazgo.

## 5. Qué está decidido, qué es bifurcación y qué está abierto

> **Corrección (2026-08-07, después de releer la spec).** Una versión anterior de
> esta sección decía que estos ítems «bloquean el camino a probar edges» e
> incluía la definición de toque de `AACloseOpenDiffs`. **Las dos cosas estaban
> mal** y se dejan corregidas acá en vez de reescritas.

### 5.1 Lo que el auditor YA resolvió — no vuelve a abrirse

- **`AACloseOpenDiffs`**: v0.3 §4.1 dice **«queda fuera de EXPLORE-001 v1»**.
  La definición de toque figura en §4.3 sólo como **una de ocho condiciones para
  una entrada futura vía enmienda**. No bloquea nada. Listarlo como pendiente
  fue arrastrar un ítem de una lista vieja sin releer la spec posterior.

### 5.2 Lo que el auditor dejó como bifurcación, no como bloqueo

- **La regla direccional** de los candidatos 2 y 3. v0.3 §5.3 fija el
  **criterio** —una regla target-free derivada de la semántica, antes de
  outcomes— y también el **default** si no aparece: *el candidato sigue como
  fenómeno exploratorio, pero NO como hipótesis confirmatoria*.

  **Consecuencia que conviene tener clara: el camino a E-R1 no está bloqueado.**
  Con `BigTrap2` solo —dirección nativa— se puede avanzar. Los otros dos entran
  si hay regla defendible, y si no, no entran. Menos hipótesis, no menos camino.

  Análisis por candidato:
  - `Gaps2` — **sí, condicional** a que el recuento muestre que sus retornos
    vienen de gaps genuinamente vacíos. El 75 % de sus zonas contienen al precio
    al quedar disponibles, y un gap con el precio adentro no es un vacío.
  - `aVolCellPOI2` — `ref_side` es **posición, no dirección**: da un
    estratificador, y §5.2 dice que los estratos no rescatan un global muerto.
    Además **muta durante la vida de la zona**, así que exportar el valor final
    sería lookahead. Si se exporta, tiene que ser el de **creación**.
  - `HFTZones2` — **no**, salvo que se conozca la intención de diseño:
    absorción e iniciativa son lecturas opuestas y las dos plausibles.

  Cualquiera de las tres es **material** y exige enmienda fechada (§0.3).

### 5.3 Lo que está genuinamente abierto y no lo cubre la spec

- **`T = 34` es el último punto de `T_DESIGN`.** §7 paso 3 exige «estabilidad
  entre puntos adyacentes», pero para `BigTrap2` y `Gaps2` **no hay vecino
  superior**, así que la regla de banda contigua no se puede evaluar completa en
  esa celda. O se extiende la grilla, o se acepta el borde declarándolo.

  Hallazgo de la pasada adversarial propia, no un pendiente del auditor.

**Consecuencia probable: dos hipótesis, no tres.** v0.3 §6.4 lo autoriza
explícitamente — completar «tres» no justifica admitir una hipótesis mal
definida.

## 6. Prohibiciones que siguen vigentes

No tocar outcomes ni P&L. No abrir el holdout. No adjudicar la curva. No empezar
el recuento antes de cerrar el commit de evidencia. No meter
`AACloseOpenDiffs`. `docs/predictions/ESPEC_TEST_EXPLORE-001_v0.3.md` §8 tiene
la lista completa.

## Aporte al referente

Deja el traspaso sin la ambigüedad que costó el incidente anterior: qué commit
es el vigente, qué artefactos son de qué versión, qué quedó a medias y qué hay
que rehacer. Y corrige una lectura mía que habría frenado la sesión siguiente
sin motivo: **el camino a E-R1 no está bloqueado por ninguna decisión
pendiente** — con `BigTrap2` alcanza para avanzar, y las reglas direccionales de
los otros dos deciden cuántas hipótesis entran, no si se puede empezar.
