# AVCL-PRE — expansión con la ventana previa FUERA del bloque creador — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_PRE_MANIFIESTO_20261006.md`. Kernel `edgelab-avcl-pre-20261006`.
- JSON: `avcl_vol1_20261005/AVCL_PRE_RESULTADOS.json`. 8 pruebas, familia `AVCL_PRE`.
- Esta medición se diseñó para poder refutar el hallazgo principal. **Lo refuta en su interpretación para aVolCluster.**

## Formal (8, Holm, bilaterales). `y_rg_pre` H10, con la métrica vieja sobre la MISMA muestra
| celda | tipo | contraste | `y_rg_pre` | MDE | métrica vieja | Holm |
|---|---|---|---|---|---|---|
| AVCL base | AT | A1 | **+0,015** | 0,010 | 0,081 | 1e-4 |
| AVCL base | AT | A2 | **−0,023** | 0,024 | 0,054 | 0,027 |
| AVCL base | OFF | A1 | **−0,010** | 0,008 | 0,055 | 0,004 |
| AVCL base | OFF | A2 | +0,002 | 0,020 | 0,072 | 0,73 |
| AVCL W20 | AT | A1 | +0,013 | 0,015 | **0,250** | 0,031 |
| AVCL W20 | OFF | A1 | −0,033 | 0,011 | −0,046 | <1e-4 |
| **VTD 150t** | — | A1 | **+0,049** | 0,023 | 0,052 | <1e-4 |
| **VTD 50t** | — | A1 | **+0,019** | 0,016 | 0,037 | 0,004 |

En las 13 celdas de AVCL (descriptivo) pasa lo mismo: con la ventana previa fuera del bloque, AT queda entre −0,003 y
+0,028 y OFF entre −0,03 y −0,006. A H50, AT y OFF dan ≈ 0 o negativo.

## Lectura pre-registrada
**aVolClusterPOI: la "expansión" era, en su mayor parte, un artefacto de la ventana de comparación.**
- La métrica vieja comparaba el rango siguiente contra el rango **del propio bloque creador**. El bloque donde nace una
  zona es, por construcción, un bloque **comprimido**: el volumen se concentra en pocos precios. El cociente
  siguiente/bloque salía alto porque el denominador era chico, no porque el futuro se expandiera.
- Contra el rango **anterior al bloque**, el futuro es casi igual (AT +0,015, aproximadamente un 1,5 %) o un poco
  **menor** (OFF −0,010).
- W20 confirma el mecanismo: +0,25 con la métrica vieja, +0,013 con la corregida.

Reinterpretación correcta de lo medido en AVCL-VOL-1/2/3, DIST, CIERRE y EXIT:
- **La zona marca una compresión local** (un bloque con volumen concentrado en pocos precios y rango chico), y después
  el rango **vuelve a lo normal**. No hay una expansión por encima de la actividad previa a la zona.
- Lo que se interpretó como "dosis" (más anomalía → más expansión) y "la zona angosta expande más" es coherente con
  esto: **más compresión del bloque → más rebote del rango hacia lo normal**.
- DIST y EXIT usaban R o ventanas que también incluían el bloque (las salidas son casi todas inmediatas): sus colas
  "engordadas" quedan sujetas a la misma reinterpretación.
- Lo que **no** se ve afectado: los nulos de dirección (SR-DIR, delta, EXIT continuación), que no usan la ventana
  previa como denominador, y la asimetría de regreso en Q5 (mide la posición relativa del precio).

**VolTicksDef: sobrevive.** En 150t, +0,049 (antes +0,052): el efecto no depende de la ventana. En 50t baja a la mitad
(+0,019) y sigue significativo. VTD es hoy **el único sello de expansión que resiste** esta verificación.

## Por qué no lo detectamos antes (lección)
- La ventana previa = el bloque creador (W = H = 10) se heredó de VOL-1 sin escribirse como decisión. Los controles
  compartían la geometría, y se asumió que eso la neutralizaba. **No la neutraliza**: la condición de creación
  selecciona bloques comprimidos y los controles no.
- La señal que debió alertar antes: la dosis "más anomalía = más efecto" y "zona angosta = más efecto" eran
  exactamente lo que predice el artefacto.
- Regla práctica: **toda métrica relativa (futuro / pasado) tiene que tener el pasado fuera del intervalo donde se
  define el evento.**

## Estado
- **aVolClusterPOI:** `SIN EXPANSIÓN PROPIA (refutada por AVCL-PRE). Marcador de compresión local.` Siguen abiertos la
  asimetría de regreso (Q5) y la salida tras consolidar (candidata de EXIT).
- **VolTicksDef:** `EXPANSIÓN PROPIA, ROBUSTA A LA VENTANA (150t +0,049).` Es la que vale la pena profundizar.
