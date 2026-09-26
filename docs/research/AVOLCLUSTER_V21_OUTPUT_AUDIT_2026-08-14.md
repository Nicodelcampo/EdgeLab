# Auditoría del primer output real v2.1 (2026-08-14)

Payload: `avolcluster_formal_v2_1`, sha `97cd11a6…6fb`, 6E 09-26, 133 zonas OFF_PRICE,
48 sesiones, M1. Aritmética verificada independientemente desde las `session_means`
pegadas: los cinco bloques (zone, control, control_random, ambos contrastes)
reproducen media, SE y CI95 al dígito.

## Veredicto

`AVOL_UNDERPOWERED` **se mantiene** (ties 11,3% > 10%). Además, aunque el gate
hubiera pasado: el estimando primario (zona vs espejo) es +0,153 con IC95
[−0,062, +0,368] — cruza cero. No hay edge adjudicado.

## Lo que el diagnóstico v2.1 midió (funcionó)

| Brazo | Media | IC95 | Lectura |
|---|---|---|---|
| Zona | +0,153 | [−0,062, +0,368] | dirección correcta, NS |
| Control nearest (pad 12) | −0,238 | [−0,396, −0,081] | **sigue contaminado** |
| Control random | −0,077 | [−0,305, +0,150] | ~0, honesto |
| Zona − nearest | +0,391 | [+0,093, +0,689] | mide el defecto, no la zona |
| Zona − random | +0,230 | [−0,101, +0,561] | NS |

El defecto v2 (pad 3, controles dentro del bloque) quedó confirmado y medido.
Pero pad 12 **no alcanza**: `control_diagnostics` muestra `median_bar_distance = 13 = min` —
la selección "nearest" está saturada en el borde del pad. Mecanismo residual: el
control a 13 barras comparte el path del desplazamiento que creó la zona (las
ventanas de carrera se solapan ~en totalidad: offset de 13 sobre horizonte 2000)
y, cuando es pre-bloque, su ancla es de precios pre-movimiento: el intervalo
del lado de la zona queda atrás y el espejo se lo lleva el propio desplazamiento.
El control random rompe esa adyacencia y normaliza a ~0.

## Potencia (el constraint que manda)

- SE zona = 0,110 → MDE95/80 ≈ **0,31**. El efecto observado (+0,15) es la mitad
  del MDE: este estudio no puede resolver el efecto que dice testear.
- SE contraste random = 0,169 → MDE ≈ **0,47**.
- `by_side`: above +0,216 (n=74), below +0,169 (n=59) — ambos positivos. Lead
  genuino y consistente por lado, sin potencia para adjudicar.

## Decisiones declaradas ANTES de la corrida por ticks

1. **Benchmark primario = `control_random`.** `nearest` queda como diagnóstico.
   Declarado ahora, antes de ver resultados por ticks.
2. El gate de ties **no se relaja**. Los ties se resuelven con datos de tick
   (la maquinaria `tick_first_touch` de F2.7 ya existe).
3. El contraste "zona − nearest" de esta corrida no se cita como evidencia a favor.

## Siguiente paso (adjudicador)

Formal por ticks sobre los parquets canónicos F2.7 (4 quarters research,
firewall 2026-06-30), no sólo 09-26:

- Kernel aVol v0.5 en Python sobre barras M1 construidas desde ticks (`bars.py`).
- **P2**: el replay debe reproducir las 133 zonas del CSV NT8 (geometría ±0 ticks,
  barra ±1). Commitear `avolcluster_v05_20260813.csv` como oráculo en
  `data/nt8_oracles/` antes de correr.
- Carrera con desempate por ticks. Benchmark: control_random (primario), nearest
  (diagnóstico). Mismos gates, mismas etiquetas.
- Potencia esperada: ~4× zonas (4 quarters) → SE zona ≈ 0,05 → MDE ≈ 0,15,
  suficiente para el efecto observado si es real.

No tocar: holdout, P&L, barrido de parámetros del detector, cruce con otras familias.
