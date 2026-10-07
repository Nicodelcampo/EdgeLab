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

## Re-medición de la consolidación posterior con la aislada causal (2026-10-06)
Kernel `edgelab-avcl-racimo-audit-ypre-20261006`; JSON `AVCL_RACIMO_AUDIT_YPRE.json`. `y_pre` H50 = log(rango de las 50
barras siguientes / rango de las 50 anteriores al primer miembro del racimo). Todas las definiciones usan sólo el pasado.

| y_pre H50 | MNQ AT | MNQ OFF | conf AT | conf OFF |
|---|---|---|---|---|
| vs aislada look-ahead (lo publicado) | −0,063 | −0,058 | −0,053 | −0,037 |
| **vs aislada causal** | −0,019 (z −1,9) | −0,019 (z −2,2) | −0,036 (z −3,9) | −0,027 (z −3,3) |
| vs aislada causal, con control de movimiento previo | −0,036 | −0,036 | −0,040 | −0,030 |
| vs todas las no-racimo | 0,000 | −0,005 | −0,016 | −0,011 |

- A H10 el signo **se contradice** entre conjuntos (MNQ +0,03, confirmación −0,02).
- **Lectura:** queda una consolidación posterior **chica** (−0,02 a −0,04, es decir 2–4 % menos rango) contra la
  aislada causal, del mismo signo en los dos conjuntos. Contra todas las no-racimo es casi nula. Además, la ventana
  previa del racimo está más lejos en el tiempo que la de una aislada, lo que puede mover el cociente por la propia
  persistencia de la volatilidad.
- **Estado:** `CONSOLIDACIÓN POST-RACIMO: débil y dependiente del grupo de comparación`. No es base para lógicas de
  entrada/salida. Se cierra la línea de racimos de AVCL.
