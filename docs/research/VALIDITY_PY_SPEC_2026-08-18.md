# Spec de `validity.py` (v0, 2026-08-18) — absorbe P-39

- **Estado:** `SPEC_NOT_BUILT` — construirlo es C3, y C3 espera el STOP de Nico.
- **Por qué existe:** H-Z2A v3 propuso la cadena `constructo → observable →
  estimador → chequeo`; la entrada 011 la corrigió a `constructo → observable →
  **unidad** → estimador → chequeo`; la entrada 021 la dejó en `constructo →
  observable → **unidad + reloj** → estimador → chequeo`. Este documento fija el
  módulo que la ejecuta.
- **Absorbe P-39** con el criterio de cierre ya escrito: `validity.py` existe,
  tiene la dimensión unidad + reloj, y los tres casos nombrados (`gex_dollar`,
  `zone_age`, `distance_to_nearest_zone`) pasan o fallan **explícitamente**.

## 1. Qué verifica (y qué no)

El proyecto verifica identidad de **archivos** con sha256 por todos lados. Un
sha256 prueba que el archivo es el mismo; **no prueba que la columna `gex_dollar`
tenga dólares adentro**. `validity.py` es el chequeo de que el **nombre** de una
salida corresponde a su **contenido** — en unidad y en reloj.

No verifica archivos (eso ya existe). No toca `features.py` (eso es C3/build,
después del STOP). No es un gate de gating (no cambia semántica de promoción).

## 2. El registro declarativo

Cada salida nombrada de la línea se registra con:

| campo | qué es |
|---|---|
| `nombre` | el nombre público de la salida (el que un consumidor lee) |
| `constructo` | qué cree que mide (una línea) |
| `observable` | qué registra en el dato |
| `unidad` | ticks / ms / ns / barras / contratos / USD… — **obligatorio** |
| `reloj` | calendario / eventos / volumen / directional-change — **obligatorio** |
| `estimador` | con qué código se computa (path + blob) |
| `chequeo` | el test ejecutable que demuestra que captura el constructo |

Ningún eslabón se salta. Si el chequeo no existe o falla, la variable entra como
**proxy declarado con su limitación escrita** — nunca como la cosa misma.

## 3. Los chequeos ejecutables mínimos

1. **Unidad de grilla de ticks.** Toda cantidad declarada en ticks es entera tras
   el snap a la grilla del instrumento (residuo < 1 ULP de la grilla). Si
   `distance_to_nearest_zone` sale en unidades de precio, **falla** acá — no en el
   consumidor.
2. **Unidad temporal.** Toda cantidad declarada en ms/ns/barras cae dentro del
   rango declarado y es consistente con su reloj (p.ej. `zone_age` en ms no puede
   leerse como barras sin conversión declarada — el factor 60.000 de F0.3 es el
   caso canónico).
3. **El nombre lleva la unidad** (sufijo `_ticks`, `_ms`, `_ns`…) o el registro la
   prueba. Un nombre que afirma una unidad que el contenido no produce
   (`gex_dollar` sin dólares) **falla explícitamente**, con el caso nombrado.

## 4. Los tres casos de P-39, como tests

| salida | la etiqueta dice | el contenido es | el test |
|---|---|---|---|
| `gex_dollar` (`edgelab/gex/reconstruct_daily_gex.py`) | dólares | `OI × gamma × 100`, sin spot | falla hasta que se renombre o se compute spot — decisión de Nico (N4) |
| `zone_age` (`edgelab/bridge/features.py`) | edad | **milisegundos**, unidad no declarada | falla hasta `zone_age_ms` aditivo o conversión declarada (N3) |
| `distance_to_nearest_zone` (mismo) | distancia | **unidades de precio**; `tick_size` se acepta y se descarta | falla hasta que la unidad se declare y se cumpla |

«Pasan o fallan explícitamente» significa que el reporte nombra el caso y el
motivo. Un fallo conocido y escrito **no** bloquea el censo (que trae su propio
cálculo con unidad declarada); bloquea que la salida entre a un artefacto formal.

## 5. Integración

- Corre sobre las salidas del panel/censo **antes** de que entren a un artefacto.
  Falla = no entra.
- El registro es aditivo: ninguna salida ya publicada cambia de nombre ni de
  unidad — se agrega la variante con sufijo (precedente: `git_blob_sha1_lf` de
  P-26).
- Reporta por salida: `PASS` / `FAIL(nombre, motivo)` / `PROXY_DECLARADO`.

## 6. Qué no hace

No mide mercado. No lee outcomes. No decide gates. No reescribe lo publicado.

**Aporte al referente:** convierte «la etiqueta no se deriva del contenido» —la
familia más repetida del board (P-34, P-35, P-39, P-41)— de hallazgo periódico en
chequeo ejecutable.
