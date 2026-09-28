# Enmienda PROPUESTA: holdout propio para modelos de L2 (2026-09-24)

**Estado:** FIRMADA por Nico el 2026-09-24 (chat). Incorporada al North Star (nuevo sha256 del cuerpo: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`).
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1` (la enmienda lo modifica; al firmarse cambia el hash).

## Qué cambia

Para **toda investigación que use datos L2 (MBP-10)**: modelos como DeepLOB, detectores, atlas y familias medidas sobre el libro. Solo en los instrumentos con L2 capturado (GC, 6E, NQ, ES, MES, MNQ, ZB). Ampliado el 24/09 a pedido de Nico ("balancear rigurosidad y disponibilidad"):

| Tramo | Rol |
|---|---|
| L2 del 01/07/2026 al 31/10/2026 | **Desarrollo**: se permite entrenar, validar y elegir |
| L2 del 01/11/2026 al 31/12/2026 | **Holdout L2 sellado**: una sola apertura por modelo, con protocolo firmado antes |

## Qué NO cambia

- El holdout de ticks, barras y cualquier familia que no sea un modelo de L2 sigue siendo 01/07–31/12/2026.
- La regla 95 ("la frontera es un sello, no un cursor") se respeta: esta es una **frontera nueva, fijada antes de mirar noviembre y diciembre, que todavía no existen**. No es mover la frontera vieja después de ver resultados.
- El 24/09/2026 sigue excluido de cualquier confirmación de TBZ.

## Costo, escrito para que quede claro al firmar

1. Julio a octubre de 2026 **deja de ser holdout ciego** en esos instrumentos para cualquier hipótesis que después use L2. Un resultado de ticks sobre esos meses sigue valiendo, porque el holdout de ticks no cambia, pero **no se puede combinar** con un modelo L2 entrenado ahí.
2. El holdout L2 queda en **~40 sesiones por instrumento**: menos potencia que seis meses.
3. Toda familia o modelo L2 registra en el Brain su partición de entrenamiento y su apertura del holdout L2, igual que las familias.

## Firma

"Firmo la enmienda ENMIENDA_PROPUESTA_HOLDOUT_L2_20260924" (en el chat). Con eso se actualiza el North Star, se recalcula su hash y se registra en `docs/holdout_access_log.md`.
