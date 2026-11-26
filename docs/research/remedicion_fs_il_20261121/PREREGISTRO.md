# REMEDICION-FS-IL: los 15 módulos de FundedSync con la traducción corregida por Antigravity (pre-registro, 2026-11-21)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de correr.
- **Pedido de Nico (2026-11-21):** «fijate lo que subió recientemente Antigravity porque nos dimos cuenta que el FundedSync estaba mal
  traducido».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2:** re-medición descriptiva, regla de la guía: una corrida con código que después se corrigió no se mira; se relanza.
- **Familia:** `FUNDEDSYNC`.

Antecedentes:
- `docs/research/fundedsyncstack_20261115/AUDITORIA_PARIDAD_IL_20261120.md`: 6 errores de paridad IL corregidos en el commit `7965e7fb`.
  - V: la hora bloqueada se evaluaba en ET y va en CT.
  - Q: el valor del punto es el de MNQ.
  - E, A1, A20, S y N: faltaba el cierre diario 15:44–17:01 CT.
  - T: `same_et_date`.
- Todas las operaciones de FundedSync que usó EdgeLab salieron del código anterior: `m1_largo_20261117/FS_OPS_*`, `neto_pistas_20261119/RZ_OPS`,
  A20-REGIMEN, FILTROS-CONTEXTO, el holdout terminal de A20, CANASTA-CORRELACION y la verificación del vendedor.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 escalas, K40 motor, K51 conteo).

Potencia previa: no aplica. Es una re-medición de reglas ya medidas; se comparan las operaciones viejas contra las nuevas.

Diagnóstico de mecanismo: no aplica (sin grilla). Se publica, por módulo:
- operaciones;
- neto en puntos y t mensual en 2010–2021, 2022–2026 y 2025-09 → 2026-09;
- la diferencia contra las operaciones viejas.

## Justificación económica
Las mismas reglas del vendedor, ahora fieles al binario. Si un módulo cambia de signo o de t, la conclusión anterior sobre ese módulo
no vale.

## Qué se corre (fijo)
- **Corrida:** `tools/m1_largo.py::correr_fs` sobre el M1 de NT8 de NQ (2006 → 2026-09-30, sin el holdout terminal), con la fricción
  canónica.
- **Salida:** en esta carpeta (`FS_OPS_NQ_IL.csv.gz`). Los archivos viejos no se pisan.
- **Contador:** 1 (re-medición de la familia, descriptiva).

## Cómo podría refutarse
- Si las operaciones nuevas de T, R, Z y A20 cambian de forma material (t mensual 2022–26 con diferencia > 1), las conclusiones de las
  campañas que las usaron se re-hacen.
