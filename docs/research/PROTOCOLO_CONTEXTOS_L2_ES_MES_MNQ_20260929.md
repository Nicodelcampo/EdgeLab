# Protocolo de contextos L2 (4 climas) en ES, MES y MNQ — PRE-REGISTRO target-free (2026-09-29)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** escrito antes de extraer ni entrenar (pedido de Nico: «ejecutá todos los pasos»). Target-free: no mira
retornos, P&L ni MAE/MFE. Método **idéntico** al de NQ (`PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md` + enmienda 1, auditado
en 051/053): mismas features, mismo HMM de 3 estados + overlay tóxico, desestacionalización, semillas 1–10, sticky, y las
mismas compuertas con PASS/STOP automático. Runner: `tools/build_l2_contexts.py --inst {ES,MES,MNQ}` (copia parametrizada
del de NQ; el de NQ no se toca).

## Independencia
Un modelo por instrumento, entrenado sólo con sus sesiones. **Nada se transporta**: ni el modelo de NQ, ni sus umbrales,
ni la lectura de sus climas. Un «toxic» de MNQ no significa lo mismo que uno de NQ; no se comparan climas entre activos
sin un análisis propio.

## Datos y split (catálogo `L2_sessions_catalog_20260927.json`, contrato 09-26, sin roll en el catálogo)
| Inst | Sesiones | Entrenamiento (primer tercio) | Evaluación |
|---|---|---|---|
| ES | 48 (30-jun → 11-sep) | 16 | 32 |
| MES | 50 (30-jun → 11-sep) | 17 | 33 |
| MNQ | 52 (29-jun → 14-sep) | 17 | 35 |

El split es la regla fija «primer tercio entrena» (NQ fue 20/60), elegida antes de mirar features. Sin compuerta de roll
(no hay roll dentro del catálogo); la deriva de contrato no se puede medir aquí y se declara como no medida.

## Compuertas (las de NQ, sin relajar)
Cobertura ≥ 99 % en evaluación; estabilidad por semilla y por estado ≥ 0,80; STOP por estado si > 80 % de sus minutos cae
en 2 h; STOP global si un clasificador de sólo-hora acierta ≥ 90 %. Si un instrumento da STOP, ese instrumento queda sin
climas: no se cambian parámetros ni el split después de ver el reporte.
Compuerta de eventos (≥ 40 sesiones de evaluación con eventos por celda): con 32–35 sesiones **se espera SIN_POTENCIA**
en los tres; se publica, no se relaja.

## Operación
Extracción de a un instrumento por vez (16 GB de RAM; regla de un solo proceso L2 pesado), en orden ES → MES → MNQ.
Etiquetas a UTC con `tools/l2_labels_utc.py`.

## Cómo podría refutarse
Acuerdo entre semillas bajo, estados que son sólo la hora, persistencia de 1–2 minutos, o elegibilidad de minutos baja por
problemas de libro propios del instrumento (causa raíz antes de seguir, como en NQ).

## Enmienda 1 (29/09, durante la extracción de ES y ANTES de entrenar ningún modelo)
- **Hallazgo:** ES 12/08 dio 0 minutos elegibles (5,7 M eventos de libro inválido). Causa raíz: el archivo L2 del 11/08
  empieza a las 14:11 ART (grabación NT8 incompleta) y termina 01:04 del 12/08, **después** del inicio del archivo del
  12/08 (01:00). La regla de carga heredada de NQ descartaba el comienzo del archivo siguiente y con él su foto inicial
  del libro. Solapamientos > 5 s: ES 11→12/08 (241 s); MES y MNQ 11→12/08 (13 h); fuera del catálogo 28→29/06.
- **Cambio de carga (sin cambio de método):** se recorta la cola del archivo previo y el siguiente se conserva entero.
  Como también hay solapamientos de pocos segundos (donde las dos reglas difieren en qué filas se descartan), se
  **re-extraen todas las sesiones de ES** con la regla nueva: una sola regla para todo el instrumento. La caché vieja se
  movió a `E:\_PARA_BORRAR_l2ctx_ES_regla_vieja`.
- **NQ (ya entrenado):** la misma regla afectó su sesión 29/06 (entrenamiento; 793 s de solapamiento). Falló cerrada:
  1.291 de ~1.371 minutos elegibles, sin minutos contaminados. No se re-entrena NQ; queda anotado.
- **Pérdida por el dato, no corregible:** ES 11/08, libro cruzado 12:11–16:04 CT (grabación del 11/08 incompleta);
  1.102/1.393 minutos elegibles. ES 06/08: libro inválido fuera de la ventana de sesión, sin efecto.
