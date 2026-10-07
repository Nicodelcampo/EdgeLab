# RETRACTACIÓN — AVCL-RACIMO y AVCL-RACIMO-CONF: el efecto direccional era un artefacto de look-ahead — 2026-10-06

## Qué estaba mal
El grupo de comparación "aislada" se definió como "ninguna otra zona a ≤ 40 ticks en **±200 barras**". La ventana
incluía las 200 barras **posteriores**. Si el precio vuelve al nivel, nacen zonas nuevas ahí, y la zona deja de contar
como aislada. El grupo de comparación quedó así sesgado hacia "el precio no volvió". El contraste racimo − aislada
(s < 0, "regreso") quedó **fabricado por la definición**.

Lo detectó la auditoría que pidió Nico antes de profundizar (`tools/avcl_racimo_audit.py`, kernel
`edgelab-avcl-racimo-audit-20261006`, JSON `avcl_racimo_conf_20261006/AVCL_RACIMO_AUDIT.json`).

## Evidencia
| s_50, zonas OFF | MNQ | ES+YM+RTY+MGC |
|---|---|---|
| racimo vs aislada con look-ahead (lo publicado) | −0,039 (z −2,6) | −0,038 (z −2,1) |
| **racimo vs aislada causal (`burst = 1`)** | **−0,006 (z −0,5)** | **−0,007 (z −0,6)** |
| racimo vs todas las no-racimo | −0,019 (z −1,5) | −0,010 (z −0,9) |

- s medio del grupo "aislada vieja": **+0,030**; del causal: −0,006. Ahí está el sesgo.
- Controlar el movimiento previo (a favor del lado, 10/50 barras, con y sin signo) no cambia nada: ese segundo
  candidato a artefacto no operaba.

## Qué queda invalidado
- **AVCL-RACIMO-CONF "CONFIRMA"**: invalidado. No hay dirección propia de los racimos.
- AVCL-RACIMO "dirección / regreso": invalidado.
- AVCL-RACIMO "consolidación posterior" (`y_pre` H50 < 0): también comparaba contra la aislada con look-ahead (las
  zonas cuyo nivel el precio abandonó tienen, por construcción, más rango después). **Queda en suspenso**, hasta
  re-medirla con la aislada causal.
- El indicio de "regreso en alta anomalía" de AVCL-CIERRE (Q5) **no** usa esa definición y sigue registrado como
  estaba (débil, sin réplica).

## Lección (regla)
Los grupos de comparación tampoco pueden definirse con información posterior al evento, igual que las variables. Toda
definición de "aislado", "sin vecinos", "único", etc. se escribe **sólo con el pasado**.
