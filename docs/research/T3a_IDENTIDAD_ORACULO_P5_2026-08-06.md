# T3a — identidad del oráculo de P5: **SATISFECHO**

**Fecha:** 2026-08-06 · Cierra el ítem 1 de la tabla de K1
(*"archivo presente en el clon de trabajo con sha `7d0f464f…`"*).

## Verificación

```
archivo    oracles/BigTrap2_time1_6E_0926_v2.csv
sha256     7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27
acta K1    7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27
->         IDÉNTICO
bytes      1.110.200
líneas `# meta`  1     (una sola corrida por archivo, como exige P6)
version declarada  2.1  (es el oráculo histórico, correcto)
```

**Qué se leyó y qué no.** Los bytes para el hash y **la línea `# meta`**. No se
leyeron zonas, geometría, precios ni ningún evento económico. Es la misma clase
de lectura estructural que `holdout_access_log.md` ya registró como
`target_free_validation` el 2026-07-29 para decidir aptitud de un oráculo
**antes** de correr el matcher.

**Distinción que importa.** Verificar la identidad de un archivo no es
consumirlo. Correr P5 —que sí lee su contenido económico— **sigue exigiendo la
fila en `holdout_access_log.md`**, porque la ventana del oráculo
(`2026-07-07T19:04` → `2026-07-24T17:59`) cae entera dentro del sello.

## Distinción con los homónimos

Hay cuatro `BigTrap2_time1*` en `oracles/`. Sólo uno es el de P5:

| archivo | sha256 | bytes |
|---|---|---|
| **`_v2.csv`** | **`7d0f464f…`** | 1.110.200 |
| `_samelevel.csv` | `49703a27…` | 2.215.972 |
| `_wickoff.csv` | `8c5db456…` | 1.801.779 |
| `_diag_time1_…` | — | (diagnóstico) |

Elegir por nombre habría sido posible; **elegir por hash es lo que lo hace
acreditable.**

## Lo que sigue bloqueando P5

**D2 del auditor sigue en pie:** `oracles/*.csv` **no está versionado**, así que
en un clon limpio este archivo no existe y T3a volvería a fallar. El hash queda
registrado acá para que la verificación sea reproducible **aunque el archivo
viva fuera de git** — pero eso es un parche, no una solución.

Versionarlo tiene un costo real que no decido yo: el archivo es un EventLog cuya
ventana está **entera dentro del holdout sellado**, y meterlo en git pone ese
material en el repo de forma permanente.
