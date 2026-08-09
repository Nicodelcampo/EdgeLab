# PRED-004 · P5 — **PASS**. El camino de tiempo no se movió

**Fecha:** 2026-08-08 · **Máquina:** la de OneDrive (`C:\ProyectosQuant\EdgeLab`)
**Enmienda que lo habilita:** `docs/amendments/PRED-004-2026-08-08_P5_pareja_de_capturas.md`,
registrada y commiteada **antes** de la primera captura.

---

## Resultado

```
estado                        PASS
n_diferencias                 0
n_eventos_economicos          2282 / 2282
seq_corrido                   false
footprint_mismatch_por_lado   0 / 0
n_no_economicos               0 / 0
resultado_sha256              be277e6649d257f0c44614bc96f694389b76386d0f0fba04d1771afa752f64b1
```

Es el resultado más fuerte que P5 puede dar. La enmienda N1 previó que un
`seq_corrido=true` sin diferencias económicas debía resolverse como **ABSTAIN de
política**, no como PASS. **Acá ni siquiera hubo corrimiento**: `seq_corrido` es
`false`, así que la identidad es económica *y* de secuencia absoluta.

## Qué se comparó

| | A | B |
|---|---|---|
| versión | **2.1** (`0e12d9f`) | **2.4** (`9b63959a62f08860…`) |
| archivo | `BigTrap2_time1_6E_0926_v21_A__Minute1.csv` | `BigTrap2_time1_6E_0926_v24_B__Minute1.csv` |
| bytes | 383.473 | 383.528 |
| eventos | 2.282 | 2.282 |

Idénticos en instrumento (`6E 09-26`), resolución (**1 minuto**), ventana
(`End date 18/06/2026`, `Days 5` → `2026-06-14T19:02` a `2026-06-18T17:56`),
parámetros (**defaults**) y `Maximum bars look back` (**256**).

Conteos por tipo, iguales en las dos: `ZONE_TOUCHED` 932 · `TRAP` 773 ·
`ZONE_CREATED` 293 · `ZONE_INVALIDATED` 281 · `ZONE_EXPIRED` 3.

## Qué prueba, y qué no

**Prueba** que los cambios de atribución BIP1→barra introducidos entre v2.2 y
v2.4 **no tocaron el camino de tiempo**. Ése era el riesgo real y concreto:
arreglar la atribución en barras de tick y romper en silencio `time:1`, que ya
estaba en **PASS 225/225** (oráculo O1). No pasó.

Es coherente con el diseño: `DrainReadyBars` bifurca por `fpTicksPerBar` y el
camino de tiempo quedó intacto por construcción. P5 lo **verifica** en vez de
confiar en la lectura del código.

**No prueba** que v2.4 coincida con lo que la otra máquina midió históricamente.
El oráculo pre-registrado (`7d0f464f…`) no está en esta máquina y no se puede
reproducir — §1 y §2 de la enmienda. Si algún día aparece, esa comparación sigue
siendo posible y **este resultado no la reemplaza**.

## P6 — integridad de archivo

Los dos en **PASS**: una línea `# meta`, un solo inicio de `seq`, cero líneas
malformadas.

**Una corrección de nomenclatura, sin tocar contenido.** La captura A salió como
`..._v21_A.csv` y P6 la marcó `FAIL` por una sola razón: *«el nombre no declara
la resolución esperada `Minute1`»*. Es consecuencia de que **v2.1 no tiene la
rotación automática** que sí agrega v2.4 (P6) — ya anotado en §5 de la enmienda.
Se renombró a `..._v21_A__Minute1.csv` y se verificó por hash que el contenido
quedó intacto:

```
sha antes   223872c41397c4d1247406ca192465f648d2f1208db975842b12cc54b13a8bf0
sha después 223872c41397c4d1247406ca192465f648d2f1208db975842b12cc54b13a8bf0
```

El chequeo existe para impedir comparar un `Tick25` contra un `Minute1` por
error, así que hacer que el nombre lo declare es cumplirlo, no evadirlo.

## Procedencia

`oracles/*.csv` está gitignoreado, así que los CSV **no viajan**. Su identidad
quedó versionada en `docs/oraculos_manifiesto.json` (5 archivos, `todo
coincide`). El JSON del análisis vive en `runs/`, también gitignoreado; su
`resultado_sha256` está arriba.

`BigTrap2.cs` v2.1 se recuperó de `0e12d9f` y se verificó **idéntico al backup
instalado del 27-jul** salvo la región que NT8 genera sola — diff de una línea
en blanco. Las dos versiones pasaron el gate real de compilación
(`tools/compilar_nt8_cs.py`, con control negativo).

Holdout: **no se tocó**. La ventana es pre-holdout y son cuatro días `APTO` ya
vetados en `PEDIDOS_NT8_2026-07-27`. Sin fila nueva en `holdout_access_log.md`.

## Qué sigue

Con P5 en PASS, el orden del contrato habilita **K=25 (P1)** y después
**K=10 (P2)**, que son las predicciones que de verdad ponen a prueba el fix de
atribución. La refutación está declarada: `FOOTPRINT_MISMATCH > 1%`.

Recordatorio de lo que se mide contra qué: PRED-003 fue **refutada** con 3,91 %
en K=25 y 81,78 % en K=10. Ése es el punto de partida que v2.4 tiene que mover.
