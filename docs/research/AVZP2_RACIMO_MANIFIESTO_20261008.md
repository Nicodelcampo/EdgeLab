# AVZP2-RACIMO — ¿qué hace el precio en relación con los racimos de aVolZonePOI2? — manifiesto — 2026-10-08

Pedido de Nico: "obtener información sobre los racimos, para decidir en qué aspecto del precio en relación a ellos me
conviene enfocarme para diseñar una estrategia". Hash NORTH_STAR:
`ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. **Información, no P&L.** Escrito antes de calcular
nada con estos datos.

## Indicador y configuración (paridad exacta en 25t, `PARIDAD_AVOLZONEPOI2_MNQ1226_25T_20261008.md`)
aVolZonePOI2 en barras de **25 ticks**:
- detección por defecto;
- racimo: **≥ 6 zonas, ventana de 500 velas, altura ≤ 30 ticks**;
- OB (100 / 6 alturas / 8 ticks / 4 %): no participa.

Familia nueva `AVZP2_RACIMO`, con ledger propio. No hereda de AVCL-RACIMO (retractado) ni de AVZP2-REBOTE.

## Antecedentes que condicionan el diseño
1. AVCL-RACIMO se retractó por usar información futura en el grupo de comparación. Acá **todo se define en la barra
   de formación del racimo `t0`** (la barra en que se completa). Nunca se usa el violeta "desde el inicio", que en el
   chart está repintado.
2. En AVZP2-REBOTE, el efecto de las rojas era mayormente el "alejamiento limpio". El nulo tiene que aparear la
   característica obvia del evento.
3. **Confusor central:** un racimo de 6 zonas en 30 ticks implica que el precio pasó mucho tiempo en esa franja.
   El nulo se aparea por **ocupación previa**: la fracción de las 500 velas anteriores con cierre dentro de la franja.
4. Cerebro SSRN: no hay evidencia empírica directa sobre clusters de volumen como S/R. Hay penetración transitoria
   de niveles por mechas (doc 22/400), por eso las salidas se miden por **cierre**. La volatilidad se agrupa
   (doc 138), así que se mide la expansión con una ventana pasada fuera del evento.

## Datos
- MNQ, cada contrato con sus propios ticks (sin merge), sesiones del RESOLVER, todas las horas.
- **Descubrimiento:** 09-25, 12-25, 03-26 y 06-26. **Confirmación (una sola vez, sólo lo que pase):** 09-26 y 12-26.
- Holdout ≥ 2026-10-01: no se lee.

## Espacio de eventos
| evento | ¿se mide? |
|---|---|
| **formación del racimo (t0)** | **sí: evento base** |
| salida de la franja (primera vela que cierra fuera) | sí, como desenlace |
| primer regreso a la línea después de salir (retest) | sí, como desenlace |
| toques posteriores de las líneas (n-ésimo, sesiones siguientes) | no (ver No medido) |
| zonas individuales del racimo | no (ya fue AVZP2-REBOTE) |
| estado continuo (distancia a las líneas en cada barra) | no |

## La franja del racimo
`[L, H]` = piso y techo del racimo **en t0** (snapshot; las ampliaciones posteriores no se usan). `h = H − L + 1`
ticks.

## Desenlaces (desde t0 + 1, en la misma sesión)
- **O1, dirección de salida:** primera vela con cierre > H (arriba) o < L (abajo), hasta 2.000 velas.
  - Se mide como **continuación**: si la salida va a favor de la tendencia previa (signo de close[t0] −
    close[t0 − 500]).
- **O2, seguimiento de la ruptura:** después de la salida, el precio llega a `borde ± h` del lado de la salida antes
  de volver a cerrar dentro de la franja.
- **O3, retest:** después de la salida, el precio vuelve a tocar el borde por el que salió (hasta 2.000 velas). Si
  vuelve, se mide si rebota (llega a borde ± h del lado de la salida) o rompe (llega a borde ∓ h).
  - O3a: P(retest). O3b: P(rebote | retest).
- **O4, duración:** log(velas hasta la salida).
- **O5, expansión (no direccional):** log(rango de las 200 velas posteriores a la salida / rango de las 200 velas
  anteriores a la primera zona del racimo). La ventana pasada queda fuera del intervalo del evento.

## Nulo: pseudo-racimos
- 5 por racimo real, en velas al azar del mismo contrato y la misma franja de 30 min CT.
- Misma altura `h` y misma posición relativa al close que el racimo real en t0.
- Misma regla de desenlaces.
- **Apareamiento:** efectos fijos por decil de ocupación previa (fracción de las 500 velas anteriores con cierre en la
  franja), por contrato × franja horaria y por tercil de amplitud previa (200 velas).

## Estimador y pruebas
β real − pseudo, con LPM o MCO y FE, y SE por sesión. **5 pruebas formales con Holm:** O1 (continuación), O2, O3b,
O4 y O5. O3a es descriptiva. Se publica el MDE de cada una.

**Descriptivos para diseño, que son el objetivo práctico:** las tasas reales (aunque no le ganen al azar), la
distribución de la excursión después de la salida en múltiplos de `h`, la distribución del tiempo hasta la salida,
la cantidad de racimos por sesión y la distancia del precio a la franja en t0.

## Justificación económica
Un racimo de zonas de volumen anómalo marca un precio donde se acumuló inventario repetidamente. Si esas posiciones
se defienden o se liquidan al salir, la salida debería tener seguimiento, el retest debería rebotar o la volatilidad
expandirse **más que en una consolidación cualquiera de la misma ocupación**.

## Cómo podría refutarse
β ≈ 0 en O1–O5 con el MDE publicado: lo que pasa alrededor del racimo es lo mismo que en cualquier franja donde el
precio estuvo igual de tiempo.

## NO MEDIDO (explícito)
1. **P&L, costos, entradas, stops.**
2. **Toques de las líneas en sesiones posteriores** (las líneas de 5.000 velas), ni el toque n-ésimo.
3. **Otras configuraciones:** sólo ≥ 6 zonas, 500 velas, 30 ticks y 25t. No se mide la sensibilidad a esos valores.
4. **Otros instrumentos y escalas** (sólo MNQ 25t).
5. **El chart fusionado:** se mide cada contrato con sus propios ticks.
6. **Racimos que se amplían:** sólo el snapshot en t0, sin ampliaciones posteriores ni racimos que se fusionan.
7. **La composición del racimo** (rojas/azules, scores, densidad) como moderador.
8. **El régimen** (tendencia o rango a mayor escala) más allá de la amplitud y la tendencia de 500 velas.
9. **Salidas por mecha** (sólo por cierre) y **salidas en otra sesión** (lo que no sale en la misma sesión es NaN).
10. **El lado de formación** (precio arriba o abajo de la franja en t0) como moderador: queda descriptivo.
11. **La comparación con los racimos de AVCL.**
