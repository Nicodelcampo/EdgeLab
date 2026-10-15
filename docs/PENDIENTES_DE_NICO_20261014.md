# Pendientes que sólo puede cerrar Nico (2026-10-14)

Estado: VIGENTE
Fecha: 2026-10-14
Familia / módulo: governance · producto

Todo lo demás del roadmap (`docs/PRODUCT.md`) está ejecutado, verificado y versionado. Lo que sigue depende de NinjaTrader, de hardware o de una decisión que no se delegó. Cada ítem dice qué desbloquea y cómo verificar que quedó hecho.

| # | Acción | Dónde | Desbloquea | Cómo se verifica |
|---|---|---|---|---|
| 1 | **Reanudar la grabación de Market Replay** (NT8 dejó de grabar el 2026-09-24/28): Tools → Options → Market data → *Record market replay data*, NT8 conectado al feed durante la sesión | NT8 | N (muestras), holdout L2 propio (1-nov → 31-dic) | `db\replay\<instrumento>` con `.nrd` nuevos **sin** `.invalid`; `tools/daily_data_health.py` deja de alertar |
| 2 | **Exportar los 309 tramos P0** de sesiones faltantes (AddOn `EdgeLabTickHistory`, un archivo por día) | NT8 | Completar la release; menos conflictos de fuente | `docs/infra/MISSING_EXPORTS_20261014.md` regenerado con `tools/missing_exports_report.py` baja de 158 tramos |
| 3 | **Copia de L2 fuera de la PC** (disco externo o nube privada propia, no Drive compartido con agentes, no Kaggle, no GitHub) | hardware | Protección ante pérdida de la máquina (hoy: 2ª copia en `D:`, 69,69 GB, SHA-256 por archivo) | copiar `D:\_BACKUP_L2_20261014` y comparar con `docs/infra/L2_BACKUP_MANIFEST_SHA256_20261014.csv` |
| 4 | **OK a R3** (STOP): manifiesto, 2 celdas primarias (NQ 15 min, familias A y B), una sola apertura de la replicación 2026-04-01 → 2026-09-30, cuenta de referencia para la fricción | chat | La primera búsqueda sobre retornos | commit del manifiesto congelado + acta de resultados |
| 5 | **Decidir cuenta/broker de referencia** (Lucid, NT8 real u otra) | chat | Fricción exacta en vez de rango (ES 0,28–0,46 ticks de comisión) | tarifa efectiva en `docs/research/REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md` |
| 6 | **Ejecutar** (o autorizar) el borrado de datasets de Kaggle reemplazados; hoy **no se borró nada** y 248 kernels dependen de ellos (`docs/infra/KAGGLE_KERNEL_DEPENDENCIES_20261014.csv`) | Kaggle | Limpieza del espacio | lista final en `docs/infra/KAGGLE_BORRADO_CANDIDATOS_20261014.md` |

## Ya decidido (para no volver a preguntar)
`main` integrada y alineada · `CLAUDE.md` de `foundation` · release v4 aprobada · tarea diaria instalada · excepción de las páginas `espejo` del visor · ver `docs/DECISIONES_20261014.md`.

## Qué NO se hace sin ti
P&L, manifiestos de campaña, apertura del holdout (`trade_date ≥ 2026-10-01`), publicación de datos fuera de Kaggle privado.
