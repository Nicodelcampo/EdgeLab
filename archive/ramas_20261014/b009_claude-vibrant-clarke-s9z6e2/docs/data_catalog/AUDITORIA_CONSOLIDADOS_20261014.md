# Auditoría de los 7 datasets «consolidated» anunciados el 2026-10-13 (otro agente)

**Estado: NO verificados. Los datasets no aparecen en la cuenta `nicolasbuttaro`** (40 datasets propios listados por la API; ninguno `*-approved-20261013-consolidated`; el más reciente es del 2026-10-12). Pueden estar en otra cuenta, privados con otro slug, o no haberse publicado. Hace falta el enlace o el nombre de usuario de Kaggle donde se subieron (y compartirlos con `nicolasbuttaro` si es otra cuenta).

## Lo que se puede decir solo con el anuncio y el RESOLVER (`RESOLVER.json`, sesiones aprobadas)
| Activo | Filas declaradas | Trades esperados (suma de sesiones aprobadas) | Diferencia |
|---|---:|---:|---:|
| ES | 213,9 M | 249,9 M | −14,4 % |
| GC | 38,1 M | 42,7 M | −10,8 % |
| MBT | 2,0 M | 2,6 M | −23,0 % |
| MES | 171,9 M | 191,5 M | −10,2 % |
| MNQ | 336,3 M | 460,6 M | **−27,0 %** |
| NQ | 123,5 M | 142,5 M | −13,4 % |
| YM | 22,3 M | 24,1 M | −7,3 % |
| **Total** | **907,9 M** | **1.114,0 M** | **−18,5 %** |

- Las filas declaradas son **menores en 7–27 %** que los trades de las sesiones aprobadas. Puede haber una explicación (filas ≠ trades, recorte por ventana de sesión, deduplicación), pero hasta que se compare **sesión por sesión** no se puede dar por bueno. MNQ es el caso más grande (−124 M).
- **Cobertura incompleta:** el resolver aprueba 14 activos; la consolidación trae 7. Faltan 6B, 6E, 6J, MGC, MYM, RTY y ZB (varios usados en estudios activos: MGC, ZB, 6E).
- «Mergeé 4 contratos con cobertura parcial» (ES_09-26, NQ_09-26, MNQ_09-26, MNQ_06-26): hay que comprobar que las sesiones de esos contratos coinciden con las que el resolver asigna (el catálogo marca fuentes en conflicto y días con trades distintos entre copias).
- Un parquet por activo cambia cómo se leen los datos (el resolver y `edgelab_data` trabajan por archivo de contrato y sesión); sirve solo si conserva la columna `contract`, el orden temporal y un manifiesto con hashes.

## Verificación preparada
`tools/audit_consolidated.py` (corre en Kaggle con los datasets adjuntos): por activo compara filas por sesión contra el resolver, y revisa esquema canónico, monotonía temporal, duplicados exactos consecutivos, holdout (≥ 2026-10-01), libro bid/ask válido, nulos y reparto por contrato. Salida: `AUDIT_RESULTS.json` (agregados, sin ticks). Cuando se conozcan los slugs: `AUDIT_CFG={"datasets":{"NQ":"/kaggle/input/<slug>", ...}}`.

## Criterio de «sirve»
Un consolidado sirve para estudios si (1) cada sesión aprobada tiene exactamente los trades del resolver (o la diferencia está explicada y documentada), (2) esquema canónico y tiempo monótono, (3) nada desde 2026-10-01, (4) conserva `contract` por sesión y trae manifiesto con hashes, (5) cubre los activos que usan los estudios.
