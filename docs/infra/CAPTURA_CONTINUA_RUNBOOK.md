# Captura continua de datos — runbook

Estado: VIGENTE
Fecha: 2026-10-14
Familia / módulo: liquid-release · R0 (datos)

## Por qué importa
El límite de EdgeLab es el número de sesiones (P-53): R3 sólo detecta efectos ≥ 4 pp a 15 min en NQ/ES y nada a 30–60 min con las sesiones actuales (`docs/research/R3_DIRECCION_15_60M_MANIFIESTO_PROPUESTO_20261014.md` §6). El holdout L2 propio (1-nov a 31-dic de 2026) **sólo existe si la captura sigue**. Una captura que se corta en silencio es la forma más barata de perder N.

## Qué automatiza el repo y qué no
- **Automatizado (esta herramienta):** `tools/daily_data_health.py` avisa si no llegó dato nuevo, si hay huecos de días hábiles y si el respaldo de L2 está atrasado; con `--backup` copia lo nuevo.
- **No automatizable desde el repo:** que NinjaTrader 8 siga exportando ticks y L2. Eso se configura en NT8 (AddOn `EdgeLabTickHistory` para ticks históricos por día; export CSV L1/L2 → Parquet con `tools/convert_l2_to_parquet.py`, ver `docs/research/FUTURES_L2_CSV_TO_PARQUET_2026-08-25.md`).

## Uso diario
```
python tools/daily_data_health.py --l2-root E:/l2_parquet --backup-root D:/_BACKUP_L2_20261014/l2_parquet --ticks-root E:/EdgeLab/data/nt8_reexport_20261005 --out runs/daily_data_health.json --backup
```
Sale 1 y lista las alertas si: un contrato activo lleva más de 3 días hábiles sin sesión nueva; el último export de ticks tiene más de 5 días; o el respaldo no coincide con el origen. Sólo se alerta sobre el contrato más reciente de cada producto (un contrato vencido no es una falla).
Para correrlo solo cada día: tarea programada de Windows (`schtasks /Create /SC DAILY /ST 20:30 /TN EdgeLab_DailyDataHealth /TR "<python> <repo>\tools\daily_data_health.py ..."`). **No se instaló**: es configuración persistente en la PC de Nico y espera su OK.

## Qué hacer ante una alerta
1. **Captura L2/ticks cortada:** abrir NT8 y verificar el gráfico/AddOn de captura de ese contrato y el cambio de contrato (roll a 12-26 / 03-27); reexportar los días faltantes (`docs/infra/MISSING_EXPORTS_20261014.md` lista el formato por día).
2. **Respaldo atrasado:** correr con `--backup`; después regenerar el manifiesto SHA-256 del respaldo (`docs/infra/L2_BACKUP_20261014.md`).
3. **Hueco dentro del rango:** exportar el día faltante; no interpolar nunca.

## Estado verificado el 2026-10-14
`daily_data_health.py` sobre `E:\l2_parquet`: **no hay L2 convertido posterior al 2026-09-27** en ningún producto activo (12-26), y MBT se detuvo el 2026-07-30; el último archivo de la carpeta de ticks re-exportados es del 2026-10-05. Hay que revisar en NT8 si la captura sigue activa o si sólo falta convertir lo capturado. Respaldo: 0 faltantes, 0 diferencias (7.201 archivos de `l2_parquet`).
