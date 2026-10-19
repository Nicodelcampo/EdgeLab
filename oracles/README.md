# oracles/ — EventLogs reales de NT8 (oráculos de paridad P2)

Acá van los CSV/logs que exportan los indicadores NT8 corriendo de verdad
(`EventLogPath`). Son el oráculo contra el que se mide la paridad P2 de cada
kernel Python. **Prohibido fabricar o editar estos archivos** (ver
`docs/nt8_indicator_parity_contract.md` §4): sin el export real, ningún kernel
se declara "paridad real confirmada".

## Primer oráculo pre-registrado — Gaps2

- **Archivo esperado:** `oracles/Gaps2_6E_06-26_may.csv`
- **Selección:** 6E 06-26 · 1 minuto · defaults del kernel · rango UTC
  `2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z` (2 sesiones CME).
- **Pasos NT8:** `docs/nt8_indicator_parity_contract.md` §2.
- **Header esperado:** `event_seq,event_type,ts,unix_ms,gap_id,...`

Cuando el CSV exista, correr el matcher (idéntico al dry-run de readiness ya
verificado, agregando `--oracle`):

```powershell
.\.venv\Scripts\python tools\run_nt8_bridge.py `
  --data data\nt8\6E\6E_06-26_ticks.parquet --contract "6E 06-26" `
  --start-utc 2026-05-05T22:00:00 --end-utc 2026-05-07T21:00:00 `
  --bars time:1 --indicator Gaps2 `
  --chart-tz America/Argentina/Buenos_Aires `
  --oracle Gaps2=oracles\Gaps2_6E_06-26_may.csv `
  --zone-store runs\nt8_bridge\zone_store `
  --out runs\nt8_bridge\parity_gaps2_0626_may
```

El gate P2 y los diagnósticos quedan en `parity_report.json`; si pasa PASS, la
partición del zone store correspondiente queda marcada `trusted=True`.

## Protocolo para los otros kernels (F5+)

Mismo contrato para VolTicksPOC2, BigTrap2 (formato pipe, barras tick:N),
HFTZones2 (arrancar en borde de sesión con ≥1 sesión previa) y aVolCellPOI2
(≥ semanas de historia cargada). Un oráculo por indicador y por configuración
paramétrica a promover — ver `docs/nt8_indicator_parity_contract.md` §5.
