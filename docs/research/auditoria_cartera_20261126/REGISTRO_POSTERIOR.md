# Auditoría de cartera de Antigravity (2026-11-26): registro POSTERIOR de las pruebas en el contador global

Estado: REGISTRO POSTERIOR — las corridas de esta carpeta se hicieron el 2026-11-26 sin pre-registro ni conteo (K32). Este documento se
escribió el 2026-11-27, **después** de ver los resultados, sólo para que entren al contador global y a la corrección por multiplicidad.
No es un pre-registro y no da a ningún resultado de la carpeta el valor de confirmación: todo lo de acá es EF2 exploratorio.

- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2** (exploratorio, después de mirar). **Autor de las corridas:** Antigravity (Gemini), sesión local de Nico. **Registro:** Claude.
- **Revisión de lo corrido:** `REVISION_CLAUDE.md` (misma carpeta).

## Pruebas contadas (por familia)

| Campaña | Familia | Pruebas | Qué se probó |
|---|---|---:|---|
| `AUDITORIA-CARTERA-AG-20261126/FS_VARIANTES` | `FUNDEDSYNC` | 21 | 10 variantes de V, C, N, O (`ADAPTAR_PRESENTE_V2.json`) + 11 variantes CME (stops ATR de R/Z/N/W, SOM al cierre, V nm30, T transferido a ES/YM/RTY; `EXPANSION_MULTIACTIVO.json`) |
| `AUDITORIA-CARTERA-AG-20261126/MULTIACTIVO_M1` | `MULTIACTIVO_MECANISMOS` | 120 | 99 de Kaggle (15 mercados × 6 mecanismos) + 21 locales M1DK (8 activos × DON/ORB/OVN) |
| `AUDITORIA-CARTERA-AG-20261126/CRIPTO` | `CRIPTO_BINANCE` | 7 | 5 reglas sobre 8 perpetuos + 2 carteras (1/N, HRP) |
| `AUDITORIA-CARTERA-AG-20261126/ASIGNADORES` | `CANASTA_CORRELACION` | 21 | 7 asignadores × 3 universos en walk-forward 2021-07 → 2026-09 |

Total: 169. Las ~116 combinaciones de política y cuenta del Monte Carlo de 20 000 caminos son dimensionamiento sobre series ya contadas;
no se cuentan como pruebas de ventaja, y sus EV son exploratorios (ver K28 en `REVISION_CLAUDE.md`).

Antecedentes: `regla_cartera_20261126/RESULTADO.md`, `estabilidad_cartera_20261126/RESULTADO.md`, `fs_nfco_a5_20261126/RESULTADO.md`,
`adaptar_presente_20261126/RESULTADO.md` (lo que la auditoría revisa).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — no se leyó antes de correr (las corridas no son de Claude); se aplica ahora en la revisión.

Potencia previa: no se calculó antes de correr. Se informa después en la revisión: ninguna regla nueva tiene t ≥ 2 en REP; la REP de
cripto tiene 12 meses.

Diagnóstico de mecanismo: no se hizo antes de correr. Las grillas son chicas (mecanismos canónicos con parámetros fijos, sin barrido
interno), salvo las variantes de stop ATR (0,25/0,50), elegidas después de mirar toda la ventana.

## Justificación económica
La declarada por la auditoría: sumar motores de activos y horarios distintos (energía, metales, índices de otros husos, cripto) baja la
correlación de la cartera; la tendencia en cripto y en materias primas es un efecto documentado en la literatura (momentum de serie de
tiempo). Se registra igual que la declararon: después de ver los resultados.

## Cómo podría refutarse
Cada pista se refuta si, con un pre-registro propio, la réplica en meses no mirados (HOLDOUT A5 de la familia, o el forward) da media
≤ 0 o un t que no distingue de cero con potencia suficiente. Para las variantes FUNDEDSYNC no queda HOLDOUT A5 limpio (ver revisión):
se refutan sólo en el terminal y el forward.
