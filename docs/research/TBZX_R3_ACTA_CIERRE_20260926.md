# Acta de cierre — TBZX-R3 (reingreso a la franja TBZX), ES, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pre-registro:** `docs/research/MANIFIESTO_TBZX_REINGRESO_3T_20260925.md` (§1–7 y enmiendas §8–§10, todas escritas antes de medir).
**Cerebro:** `artifacts/hippocampus/tbzx_r3_20260926.jsonl` (partición `P-TBZX-R3-EXP`, 181 sesiones).
**Estado:** `TBZX_R3_CERRADA` con el alcance de abajo. Abr–jun (confirmación) y holdout **intactos**.

## Qué se midió

Secuencia de Nico: se crea la zona TBZX → el precio se aleja D → vuelve → penetra p → retrocede r → entrada.
Grilla: 12 configuraciones del detector, D ∈ {2..20}, p ∈ {0..12 t, 0,25/0,5/0,75 W}, r ∈ {0..4}, dos direcciones
(sigue / rebota), ejecución perfecta (trade y medio), realista (EXEC-QI sin QI) y agresiva, nulos N1 y fantasma
(otra sesión, misma hora).

| Iteración | Muestra | Resultado realista | Dirección (medio, real − fantasma) |
|---|---|---|---|
| 1 — TP 3, SL 2–8 | 181 ses., 102 M disparos | 0 de 66.000 celdas > 0 (mejor −1,15 t) | patrón de rebote bid/ask (artefacto de medir al precio de trade) |
| 2 — medio, 3 fantasmas | 181 ses. | 0 de 66.000 (mejor −1,15 t) | sigue r=0 +3,0 pp; rebota r≥2 +1,8–2,0 pp |
| 3 — TP/SL 3–20 | 46 ses. (local) | 0 FDR; media −1,55..−1,66 t en todo TP | la ventaja de «sigue r=0» se sostiene hasta TP 10 (+2,5..3,5 pp) |
| 4 — escenarios macro | 181 ses., 4,1 M disparos | 14.464 escenarios: 0 elegidos, 0 sostenidos | ningún contexto suma los ~8 pp que faltan |

## Veredicto (alcance preciso)

**La zona TBZX tiene información direccional propia** (~+2 a +3 pp sobre el fantasma, unos 0,2 t por operación),
**pero no alcanza para una estrategia neta** en ES con entradas por reingreso, TP/SL de 3 a 20 ticks, horizonte de
hasta 30 min, costo realista (~1,5 t) y con o sin filtros de contexto de tendencia, volatilidad, VWAP, hora o lado.

Esta muerte invalida exactamente ese mecanismo, esa población (disparos por reingreso sobre las 12 configuraciones),
ese estimand (P&L realista por operación) y esa ejecución. **No** invalida: la zona TBZX como filtro o como capa de
timing de una estrategia de horizonte más largo, ni otros instrumentos, ni horizontes mayores a 30 min.

## Lecciones que deja (en el cerebro)

- `LES-R3-ENTRY-AT-LEVEL-GAP-20260925`: entrar al precio del nivel cuando el trade lo saltó regala ticks.
- `LES-R3-TRADE-PRICE-BOUNCE-20260925`: con TP chicos, medir al precio de trade mide el rebote bid/ask.
- Evidencias IT1, IT2, IT3 y IT4 con el sha de sus artefactos.
- Consistente con el mapa IVC (`docs/research/IVC_RESULTADOS_20260926.md`): la información de corto plazo existe y es
  más chica que la fricción en ES, NQ e YM.

## Pendiente

- La iteración 3 sobre la muestra completa (kernel `edgelab-tbzx-r3-v3`) sigue corriendo. Si llega, se asienta como
  evidencia adicional. Sólo reabre el acta si contradice a la corrida local de 46 sesiones con FDR en la familia
  realista.

## Cómo podría refutarse este cierre

Una regla de reingreso con costo realista y P&L > 0 con IC inferior > 0 en descubrimiento, sostenida en validación
y confirmada en abr–jun, dentro del alcance declarado.
