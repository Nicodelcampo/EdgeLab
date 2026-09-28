# Auditoría del dataset Kaggle `nicolasbuttaro/edgelab-ticks-nt8-canonical` (2026-09-28)

Pedido de Nico. Verificación contra la canonización local (`tools/build_es_ext_2026q3.py --nt8`, salida
`E:\EdgeLab\data\nt8_2025_2026q3`, catálogos en `docs/research/contract_regimes/*_nt8_2025_2026q3_sessions_catalog.json`).

## Correcto
- **30 contratos (MES, MNQ, MYM, RTY, YM × 6): filas idénticas** a los manifiestos locales en los 30.
- **Holdout A3 respetado:** máximo `ts` del dataset 1.790.564.399.896.000.000 (27/09 ~21:00 CT) < frontera 1.790.805.600…
  (apertura de la sesión del 1-oct). No hay filas del holdout.
- **Catálogos idénticos byte a byte** (sha256) a los del repo.
- Recompresión zstd:19 declarada (6,5 GB vs 14,6 GB): el sha de los parquet cambia por diseño; el `AUDIT_MANIFEST.json`
  publica el sha del archivo recomprimido.

## Discrepancias
1. **Conteos de sesiones del resumen que acompañó el upload no coinciden con el propio dataset.** Resumen: MES 264, MNQ 265,
   MYM 230, RTY 223, YM 253. Catálogos del dataset (= repo): **MES 266, MNQ 227, MYM 186, RTY 235, YM 255.** Las cifras del
   resumen no salen de estos archivos; hay que corregirlas donde se hayan copiado.
2. El README dice «roll por volumen»; la regla real del catálogo es «líder (más ticks) de la sesión anterior COMPLETA, sólo
   hacia adelante» (auditoría 046 §5) — ticks, no volumen.
3. Contratos casi vacíos: **MYM 09-25 (2 filas) y RTY 09-25 (1 fila)**. No hay datos NT8 de esos vencimientos; el catálogo ya
   los excluye. Documentarlos como vacíos, no como contratos disponibles.
4. No verificado todavía: igualdad de **contenido** fila a fila tras la recompresión (sólo conteos). Chequeo barato pendiente:
   suma de `price_ticks`, `volume`, mín/máx `ts` por contrato en Kaggle vs local.

ES y NQ NT8 (solape y extensión) están sólo en disco local, como indica el resumen.
