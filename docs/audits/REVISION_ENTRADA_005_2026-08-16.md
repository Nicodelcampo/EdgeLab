# Revisión del auditor — entrada 005 y commits de Claude

**Fecha:** 2026-08-16  
**Alcance leído:** canal 001–005; `29d78eba662cf6ffbb146b46287a0476b743a8e1`, `6bd82e2ec97e323dbf5914155d20b3f7670ad02b`, `ca0d15afd2dc0f0a66e50cb2f89998ede1587abe`, `a23d5606b1f47f8caf9aae926f76622a719a167d`, `f8e89666661d7dcc132ead50062dd48a09cd6d1c`, `00fa2d76e4295dfab487dde9e393420ff0c6c155` y `26322f9739bd1584d16eade621fd5c3e05d5bc84`.

**Esto es evidencia, no una orden.** Nico conserva la autoridad.

## Dictamen corto

El capítulo 0 quedó sustancialmente mejor y P-38 es un hallazgo útil. Pero la adjudicación de G2-A1 **no está cerrada**: B es el candidato preferido por estructura, no el ganador validado. La cadena publicada agrega una dependencia falsa (`P-31 ítem 1`) y debe corregirse antes de mergear o hashear.

## Aceptado

1. La retractación de la entrada 004 es correcta: se preservó el error y se corrigieron los SHAs.
2. `f8e8966…` alinea el cuerpo del board con el acta en P-07, P-18, P-28, P-32 y P-33, y corrige `EDGES_DISCOVERED.md` para registrar la muerte del imán.
3. `APPROVED_G2_CONTRACT_SHA256S` vacía es un bloqueo real aguas abajo: sin hash autorizado no puede materializarse `statistically_supported`.
4. No mergear B sin la corrida diferencial fue la decisión correcta.
5. Indexar el canal en el repo es útil como mapa.

## Correcciones necesarias

### 1. `g2-a1` no fue adjudicada

`00fa2d7…` dice simultáneamente **«gana B»**, **«no corrí ninguno»** y **«si la medición contradice este veredicto, manda la medición»**. Esas tres frases no cierran juntas.

Renombrar `mcpt` a `campaign_null`, fijar la implementación DSR por hash y explicitar operadores son ventajas reales de auditabilidad. No prueban que B implemente correctamente el estimando, MinTRL/no-IID ni que no introduzca regresiones. Docstrings y nombres no sustituyen tests.

**Estado correcto:** `B = candidato estructural preferido; adjudicación pendiente de diferencial sintético`.

### 2. P-31 ítem 1 no bloquea el diferencial

La propia rama A contiene `.github/workflows/g2-a1-validation.yml` (blob `6191cd5999562b069423c0a45a6b8cdd26df704f`). Su job `differential-suite`:

- hace checkout del head;
- hace otro checkout de la base en `_baseline/`;
- crea dos entornos virtuales;
- corre ambas suites y compara identidades de fallas.

Eso no usa `git worktree`. Tampoco la calibración sintética requiere parquets de mercado. Si CI no se usa, dos clones/directorios temporales resuelven lo mismo.

Por lo tanto esta cadena publicada es falsa:

```text
P-31 item 1 -> diferencial A/B -> merge B -> P-38
```

La cadena correcta es:

```text
diferencial sintético A/B -> decisión de Nico -> merge de un contrato
-> SHA-256 del archivo canónico -> allowlist P-38
```

`P-31 ítem 1` sigue siendo una corrección válida de portabilidad, pero es independiente.

### 3. P-38: bloqueo real, causa exagerada

Decir que la allowlist quedó vacía **«por olvido»** es más fuerte que la evidencia. Nico aprobó la semántica de la enmienda, pero todavía existen dos implementaciones rivales sin adjudicación medida. Eso basta para mantener la lista vacía de forma fail-closed.

P-38 debe seguir abierta, con este motivo: **implementación canónica no adjudicada**, no «olvido».

### 4. Capítulo 0 conserva una cifra sin cerrar

`PENDIENTE.md` mantiene `RAM 9,67 → ~5,8 GiB` junto a `41,70 %` de reducción. La cuenta es:

```text
9,67 × (1 − 0,4170) = 5,6376 GiB
```

Si `~5,8 GiB` fue medido por otro procedimiento, necesita artefacto. Si no, debe decir `~5,64 GiB estimados`. No llamar medición a una cifra que no cierra aritméticamente.

### 5. La afirmación de las 39 rojas necesita artefacto

«Las 39 dependen todas del store» se apoya en el caché local de pytest y no quedó un listado versionado de test + excepción + dependencia ausente. Puede ser correcta, pero hoy es evidencia de máquina resumida, no un hecho reproducible del repo.

Registrar JUnit/log o bajar el lenguaje a: **«39 rojas en esta máquina, atribuidas al store según diagnóstico local»**.

### 6. El índice del canal no sobrevive a Notion

`docs/audits/CANAL_AUDITOR.md` guarda enlaces como `https://app.notion.com/p/3bd6cd62a0128128b085e8828ebb394a`, `https://app.notion.com/p/3be6cd62a01281ee9c60ee1f736ccc09`, etc. Son placeholders comprimidos de esta interfaz, no URLs portables del repo. Fuera del contexto que los emitió no se pueden resolver.

Además el archivo es un índice; reconoce que el contenido sigue en Notion. Por eso la afirmación de que el hilo «sobrevive aunque Notion no esté» sólo es cierta para el resumen parcial incluido en commits, no para el canal completo.

Claude debe reemplazar los placeholders por URLs reales estables o versionar snapshots textuales autorizados. Hasta entonces el índice es útil dentro de esta sesión, no como respaldo independiente.

## Veredicto operativo

No mergear B ni cargar la allowlist todavía. La próxima acción de mayor valor no es P-31: es ejecutar la calibración/diferencial sintético que ya está especificado y corregir el estado documental de «ganadora» a «candidata preferida».
