> **Corrida provisional, reemplazada por `GEX1_Y_GEX1B_COMPLETO_20261005.md`** (datos completos, sin sesiones omitidas).

# GEX-1 — ejecución en Kaggle (2026-10-05): desvíos y avisos

Resultados crudos: `GEX1_RESULTADOS_20261006.json` (kernel `nicolasbuttaro/edgelab-gex1-20261006`, versión 5, 77 s). El script es el del manifiesto con tres cambios que **no tocan el análisis**: (1) `EDGELAB_ALLOW_MISSING=1`, (2) el JSON declara `dropped_sessions`, (3) marcas de diagnóstico de tiempo y memoria. Fuente de ticks de MES: `edgelab-data-catalog` (`edgelab_data.py` con `load_m1` rápida) sobre `edgelab-ticks-nt8-canonical`.

## Desvíos respecto del manifiesto (declarar al leer los resultados)
1. **Se omitieron 8 sesiones de MES** por decisión del usuario («lanzalo sin las que faltan»): 2026-07-29, 07-30, 08-03, 08-06, 08-07, 08-10, 08-13 y 08-14. Solo existen en `edgelab-ticks-nt8-reexport-20261005`, que en Kaggle todavía no tiene los archivos. Quedan 248 sesiones de MES (277 aprobadas menos esas 8 y las que la ventana RTH completa descartó).
2. **50 sesiones de MES se leyeron de una fuente alternativa consistente** (`edgelab-ticks-nt8-canonical`, trades a 1 % del primario previsto), no del re-export.
3. Cuando se suba el re-export conviene repetir la corrida (77 s): cambiarían estas 8 sesiones y la fuente de las 50.

## Aviso de calidad: la prueba `I2d` de MES no es válida
`I2d` de MES dio `obs = NaN` (la pendiente de la regresión necesita más de 5 sesiones con gex < 0 y MES tiene **9 en total**), pero el script calculó `p = 0,0001` y `p_holm = 0,0009`: la comparación `nv >= NaN` es siempre falsa y el p queda en `1/(1+20000)`. **Ese p es un artefacto, no un resultado.** Efecto sobre el resto: ninguno material, porque ese p falso ocupa el primer lugar y deja a los demás con los mismos multiplicadores que tendrían con 11 pruebas (verificado a mano: los Holm de las otras 11 no cambian). Corrección propuesta (no aplicada, requiere decisión sobre el manifiesto): tratar un estadístico no finito como «no evaluable» y excluirlo de Holm.

## Lo que muestra (solo información, como dice el manifiesto)
| Fuente | Sesiones (gex<0 / ≥0) | Pruebas con Holm < 0,05 |
|---|---|---|
| MES (NT8), 2025-09-02 a 2026-09-25 | 248 (9 / 239) | ninguna válida (menor Holm 0,51) |
| USA500 spot (Dukascopy), 2023-01-25 a 2025-06-30 | 757 (39 / 718) | **I1a** (rango/rango previo, Holm 0,0135) e **I1b** (desvío de r5/σ previo, Holm 0,0055): más amplitud con gex negativo (+0,54 y +0,59), también tras controlar por quintiles de σ previo (+0,69 y +0,71) |

- En MES el signo coincide (I1a +0,34, I1b +0,16) pero con **solo 9 sesiones de gex negativo** el MDE es de 0,6 a 0,7: no hay potencia.
- Las pruebas de continuación de cierre (I2d, I2n) y de autocorrelación (I3d, I3n) no muestran nada distinguible.
