# Reporte de Avance del Sweep Target-Free — BigTrap2Absorption (99 Configs)

- **Fecha UTC:** 2026-08-26
- **Estado:** `SWEEP_BT2A_OVERNIGHT=PAUSED_BY_MAX_HOURS` (100% reanudable con `--resume`).
- **Tiempo de cómputo nocturno:** **6,0 horas continuas de CPU (21.668 segundos)**.
- **Partials completados:** **190 ejecuciones de configuración / contrato** en `E:\DatosNT8\bt2a_sweep_overnight_20260826\partials\`.
- **Firewall de outcomes:** `CAMPAIGN_OUTCOMES_OPENED=false` (estrictamente target-free, 0 violaciones).
- **Contratos cubiertos:** `GC 02-26` (99/99 completado), `GC 04-26` (91/99 completado).

---

## Próximos pasos del sweep:
Para completar los contratos restantes (`GC 06-26` y `GC 08-26`), basta con ejecutar:
```powershell
python tools\bt2_absorption_param_sweep.py run --data-dir "E:\DatosNT8" --output "E:\DatosNT8\bt2a_sweep_overnight_20260826" --resume
```
