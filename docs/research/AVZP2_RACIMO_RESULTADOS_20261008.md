# AVZP2-RACIMO — qué hace el precio en relación con los racimos — resultados (MNQ 25t) — 2026-10-08

Manifiesto: `AVZP2_RACIMO_MANIFIESTO_20261008.md`. Kernels `edgelab-avzrac-k1..k3`. JSON: `avzp2_racimo_20261008/`.

**Muestra:**
- Descubrimiento (09-25 → 06-26): **454 racimos** en 124 sesiones (3,7 por sesión), contra 1.716 pseudo-racimos
  apareados por ocupación previa.
- Confirmación (09-26, 12-26): 256 racimos.

## Formal (Holm 5): real contra pseudo con la misma ocupación previa
| desenlace | real | pseudo | β (FE) | MDE | p Holm |
|---|---|---|---|---|---|
| O1, la salida va a favor de la tendencia previa | 58,8 % | 55,2 % | +3,4 pp | 7,3 pp | 0,56 |
| O2, la ruptura sigue 1 altura antes de volver adentro | 14,1 % | 18,7 % | −3,6 pp | 5,4 pp | 0,25 |
| O3b, rebote en el retest del borde | 45,7 % | 48,3 % | −2,5 pp | 8,0 pp | 0,60 |
| O4, duración hasta salir (log velas) | 1,78 | 1,63 | +0,06 | 0,17 | 0,60 |
| **O5, expansión después de la salida (log rango)** | **−0,055** | **+0,025** | **−0,077** | 0,051 | **0,0001** |

**Confirmación de O5** (prueba única): **−0,067, p = 0,010, confirma.**

## Lectura
1. **Lo único propio del racimo es la compresión.** Después de salir de la franja, el precio se mueve **≈ 7 % menos**
   (rango de 200 velas) que después de una consolidación con la misma ocupación. Se confirma fuera de muestra.
2. **No tiene dirección.** La salida no está sesgada a favor ni en contra de la tendencia más que el azar.
3. **Las rupturas casi nunca siguen.** Sólo el 14 % de las salidas llega a 1 altura más allá del borde antes de volver a
   cerrar adentro (pseudo 19 %, la diferencia no es significativa). La excursión mediana después de salir es **0,25
   alturas** (unos 7 ticks), con p90 de 1,26 alturas (pseudo 1,95). El racimo "frena" las colas.
4. **El retest es casi seguro y no rebota.** El 99 % vuelve a tocar el borde (igual que el pseudo), y en el retest
   rebota el 46 % contra el 48 %: es una moneda.
5. **Doc 222 del cerebro (soporte o atractor):** el racimo no funciona como soporte (O3b ≈ azar) ni como atractor más
   que una consolidación cualquiera (O3a ≈ azar). Lo que hace es **amortiguar el movimiento**.

## Para diseñar (descriptivo; no es P&L)
- Un racimo aparece 3–4 veces por sesión. La franja mide 21–30 ticks. En t0, el precio está dentro en el 78 % de los
  casos.
- Sale rápido: la mediana es de 7 velas de 25t y el p90 de 33. Pero sale **poco y vuelve**.
- Lo que la evidencia sostiene es el ángulo de **rango / compresión** (por ejemplo, operar el regreso hacia la franja
  o vender volatilidad mientras el precio está alrededor del racimo). **No** sostiene el de ruptura ni el de rebote en
  la línea. El P&L de cualquiera de los dos no está medido.

## NO MEDIDO (además de la lista del manifiesto, que sigue vigente)
- **El P&L de una lógica de rango alrededor del racimo**, con costos. La compresión es del 7 % del rango: puede no
  pagar la fricción. Requiere STOP y manifiesto.
- **Cuánto dura la compresión** más allá de 200 velas, y si las líneas de 5.000 velas siguen mostrando algo en
  sesiones posteriores.
- **La sensibilidad a la configuración** (6 zonas, 500 velas, 30 ticks).
- **Otros instrumentos.**
- **La reversión dentro de la franja** (si desde un borde el precio va al otro) como desenlace propio.

## Estado
- `AVZP2-RACIMO: COMPRESIÓN POSTERIOR CONFIRMADA` (−7 % de rango, MNQ 25t).
- Sin dirección, sin seguimiento de ruptura y sin rebote propios.
