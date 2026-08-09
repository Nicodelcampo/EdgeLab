# Enmienda PRED-004 — P5 con pareja de capturas, no con el oráculo histórico

**Fecha:** 2026-08-08 · **Autoriza:** Nico (opción B, en chat)
**Estado:** **REGISTRADA ANTES DE CAPTURAR.** No se corrió P5, no se capturó
nada, no se vio ningún resultado.
**Naturaleza:** enmienda de instrumento, no de criterio. El umbral de
falsación **no se toca**.

---

## 1. Por qué

`PRED-004_tickbar_attribution_v23.json` fija:

```
"oraculo_referencia_sha256": "7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27"
```

Ese archivo es `oracles/BigTrap2_time1_6E_0926_v2.csv` (1.110.200 B, v2.1).
**No existe en esta máquina** — verificado en los tres worktrees, en la carpeta
de migración y por búsqueda de tamaño exacto en disco. Está sólo en la otra
máquina, y es de los `oracles/*.csv` gitignoreados, así que nunca viajó por el
repo. Nico no puede recuperarlo hoy.

### Por qué no se puede reproducir

**No es un artefacto de código: es una captura de NinjaTrader.** El fuente v2.1
sí es recuperable (`0e12d9f`, 31.636 B, CRLF puro, `COMPILA` verificado hoy
contra los assemblies reales), pero **capturar de nuevo no reproduce el
archivo**:

- su ventana es `2026-07-07T19:04 → 2026-07-24T17:59`, **entera dentro del
  holdout sellado** (2026-07-01 → 12-31), así que recapturarla costaría una
  apertura registrable del firewall;
- y aun pagando ese costo, **el hash no volvería a salir**: el
  `6E_09-26_ticks.parquet` de esta máquina tiene más historia que el de la otra
  (45,4 MB contra 37,6 MB declarados), así que el insumo es distinto por
  construcción.

Pagar una apertura de holdout para obtener igualmente un archivo que **no**
cumple el hash pre-registrado es el peor de los caminos. Queda descartado.

## 2. Qué se cambia

**Antes** — P5 compara la captura nueva de v2.4 contra un oráculo **histórico**
de v2.1, capturado en otra máquina, sobre otros datos, en ventana de holdout.

**Ahora** — P5 compara **dos capturas nuevas hechas acá**:

| | |
|---|---|
| A | `BigTrap2.cs` **v2.1** (`0e12d9f`) |
| B | `BigTrap2.cs` **v2.4** (`9b63959a62f08860…`, ya instalado y compilado) |
| ventana | `6E 09-26`, **End date 18/06/2026, Days to load 5** — pre-holdout |
| resolución | **1 minuto** (`--resolucion Minute1`) |
| parámetros | **defaults en las dos**, verificado que v2.1 expone la misma superficie (`UseWickFilter`, `InvalidationMode`, `MaxAgeBars`, `ImbalanceMode`, `TrapVolumeSource`, `MinExportVolume`) |

**El criterio de PASS/FAIL no cambia**: subsecuencia económica ordenada idéntica
(tipo, ts, payload) según el contrato del analizador v6; `seq` se reporta y no
es condición de FAIL (enmienda N1, ya vigente).

## 3. Por qué esto es más fuerte, no una concesión

La pregunta que P5 hace es: **¿el camino de tiempo cambió entre v2.1 y v2.4?**
El oráculo histórico la respondía de forma **confundida**: comparaba dos
versiones **y** dos conjuntos de datos **y** dos máquinas a la vez. Una
diferencia podía venir de cualquiera de los tres.

La pareja nueva **aísla la variable**: mismos datos, misma máquina, misma
ventana, mismos parámetros. Lo único que cambia es el código. Si aparece una
diferencia económica, es del código y de nada más.

Ventaja adicional: **no toca el holdout.** La ventana pre-holdout
2026-06-15 → 06-18 son cuatro días `APTO`, ya vetados en
`PEDIDOS_NT8_2026-07-27` y ya usados para TICKBAR-001. No hace falta una fila en
`holdout_access_log.md`.

## 4. Por qué enmendar ahora es legítimo

**No se ha visto ningún resultado de P5.** Lo que el proyecto prohíbe es cambiar
el criterio **después** de ver los datos; acá no hay datos que ver todavía. Esta
enmienda se registra y se commitea **antes** de la primera captura, y el umbral
de falsación queda intacto.

Se declara explícitamente como enmienda —no se presenta como preregistro
original—, siguiendo la forma de
`docs/amendments/TICKBAR-001-2026-08-04_attribution_reclassification.md`.

## 5. Cuidado operativo: v2.1 APPENDEA

`BigTrap2_v21.cs:511` → `new StreamWriter(EventLogPath, true)`. **`true` es
append.** Es anterior al fix de rotación (P6), así que:

- la captura de v2.1 debe ir a un **nombre de archivo que no exista**;
- después hay que verificar **una sola línea `# meta`** y que `seq` arranque una
  sola vez.

Si el archivo sale con dos corridas concatenadas, **se descarta y se repite** —
es el modo de falla que ya contaminó un oráculo el 2026-08-04.

La captura de v2.4 no tiene ese riesgo: rota sola por resolución e índice.

## 6. Riesgo declarado

Esta pareja **no verifica** que v2.4 coincida con lo que la otra máquina midió
históricamente. Verifica que **el camino de tiempo no cambió entre v2.1 y v2.4
sobre datos idénticos**, que es la regresión que P5 existe para detectar.

Si algún día aparece el oráculo histórico, la comparación original sigue siendo
posible y **este resultado no la reemplaza**: la complementa.

## 7. Qué se ejecuta

```
1. instalar v2.1 en NT8, compilar, capturar time:1  -> A
2. reinstalar v2.4, compilar, capturar time:1       -> B
3. pred004_analyze.py p5-time --historico A --nuevo B --resolucion Minute1
4. p6-file sobre los dos archivos (una corrida por archivo)
```

Después de P5, recién ahí K25 y K10, en el orden que el contrato ya fija.
