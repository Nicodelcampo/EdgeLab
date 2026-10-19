# Candidato GC (reversión tras el espejo) — controles P1 y P2 (2026-09-29)

Pedido del auditor (062/063), OK de Nico condicionado, sólo descubrimiento. Código `tools/espejo_gc_p1p2.py`;
artefactos `artifacts/espejo/gc_p1p2/`. Corrido localmente (liviano), no en Kaggle.

## Cohorte (tabla de exclusión)
Réplica exacta del runner que dio el candidato: **2.103 eventos** (coincide). Antes de la cohorte: 190 excluidos porque la
vela de completación no pasó A ≥ 1 tick (regla de llenado), 4 por completarse en la última vela de la sesión, 0 por pool.
El control viejo (2.076) perdía 27 por las reglas `bar < 60` / sesiones cortas, que dependían de la hora; P1 no las usa.
**Sin soporte de control: 0** (los 2.103 tienen 3 controles comparables).

## P1 — control emparejado por hora (±30 min) y volatilidad previa (terciles), otras sesiones, diferencias pareadas
| Filtro | TP / SL | n | R evento | R control | Diferencia pareada (IC 90 %) | t | max-T (crítico 3,09) |
|---|---|---|---|---|---|---|---|
| todos | **2 W / 1 W** | 2.103 | +0,026 | −0,054 | **+0,080 [+0,035; +0,123]** | 2,93 | **no sobrevive** |
| todos | 1,5 W / 1 W | 2.103 | +0,011 | −0,046 | +0,057 [+0,017; +0,093] | 2,48 | no |
| no lista + inef | 2 W / 1 W | 391 | +0,048 | −0,050 | +0,098 [−0,007; +0,206] | 1,48 | no |
- Con controles emparejados la diferencia **se mantiene** (+0,080, casi igual al +0,078 del control sin emparejar).
- **Pero no sobrevive la corrección por haber elegido entre 30 celdas** (t 2,93 < 3,09). Leída como una sola hipótesis
  pre-especificada sería significativa; como la mejor de 30, no alcanza.

## P2 — llenado tick a tick (piloto 200, estratificado 1 por sesión en ronda, semilla fija, elegido antes de mirar)
- Orden límite en A colocada al cierre de la vela del 75 %; llenado por trade-through de 1 tick: **199/200 llenados**
  (esperable: la regla de velas ya exigía que A se atravesara).
- **La regla de velas sobreestima:** por trade, R tick a tick − R por velas = **−0,034 W** en media (mediana 0).
  Salidas: SL 85, cierre al horizonte 78, TP 36.
- Fricción congelada (comisión + tasas US$ 2,50 por lado, supuesto declarado): −0,004 W. Spread medido en el llenado:
  mediana 4 ticks (p10 2, p90 10) — **anómalo para GC** (típicamente 1–2 ticks); el deslizamiento del SL sale ≤ 0
  (favorable), otra señal de que el bid/ask de Lucid en GC puede no ser confiable para costos finos (cf. P-28).
- El piloto no es representativo en nivel: su R por velas medio es +0,142 contra +0,026 de la cohorte (la ronda
  1-por-sesión sobrepondera sesiones con pocos eventos). Lo transportable es la **degradación** velas → ticks.

## Lectura
Aplicando la degradación medida (−0,034 W) y la comisión (−0,004 W) al R de la cohorte (+0,026 W): **R neto esperado
≈ −0,01 W, negativo**. La ventaja relativa contra el control emparejado (+0,08 W) sigue en pie, pero no alcanza
para una operación rentable con esta ejecución, y no sobrevive la corrección por selección.
**Veredicto: el candidato GC no pasa a confirmación en su forma actual.** Queda como información (el espejo en GC con
W ≥ 100 mejora la reversión respecto de un momento cualquiera), no como estrategia.
