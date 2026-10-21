# CANDIDATO AL HOLDOUT — LUX-IMB "fin de caja -> inicio de zona" (regla original del visor), NQ

Estado: **CONGELADO** el 2026-10-21 por decision de Nico ("¿Congelamos la regla original para el holdout?" -> "Si").
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Familia: LUX-IMB-IMPULSOS. Holdout de NQ: sesiones >= 2026-10-01 (HOLDOUT-A3). **Una sola apertura.**

## Regla (identica a `tools/luximb_parity/luximb_holdout_regla_visor.py`)
1. Zonas LUX-IMB OG+VI en M1 (detector con paridad NT8 1507/1507), vida 500 min, nacen al cierre de su vela.
2. Impulsos ESPEJO-IND en M1, marcados en tiempo real: `--modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60`
   (amplitud >= max(p60 causal, 60 pts); >= 3 zonas vivas atravesadas en el 25 % inicial y >= 50 % del total ahi).
3. Entrada al **cierre de la vela M1 de confirmacion**, 1 tick en contra, en contra del impulso.
4. **TP = A** (inicio de la zona, limite). **SL = 1/5 de la distancia entrada-A** del otro lado (+1 tick). Sin break even.
5. Tope 240 min o fin de sesion. Velas 25t; misma vela SL y TP -> SL. Costos NQ $4,50 RT.

## Evidencia previa (toda ya mirada; no es confirmacion)
Realista por periodo (pts NQ/op): 09-25 -6,4 (20) · 12-25 +3,7 (99) · 03-26 +5,7 (100) · 06-26 +6,2 (130) · 09-26 +5,6 (150, diseno).
Total 499: +4,95 [IC +0,55, +9,2]. ES (M11): ~0 (no transporta). Multiplicidad: 14+ mediciones en la familia (sin deflactar).
Auditoria de look-ahead: `AUDITORIA_ENTRADA_LOOKAHEAD_Y_BE_20261021.md` (sesgo de supervivencia corregido, 0 marcas cambian).

## Criterio de decision (fijado ahora)
- Se evalua **una vez** cuando haya **>= 150 operaciones** en el holdout (~3-4 meses) o al 2026-12-31 si no se llega.
- **CONFIRMA**: n >= 150 y limite inferior del IC 95 % (bootstrap por dia) > 0 del P&L neto por operacion.
- **REFUTA**: n >= 150 y media <= 0. Si no: NO_CONCLUYENTE (no se re-intenta ni se ajusta).
- El resultado no se usa para elegir, ajustar ni re-probar variantes (TP/SL/BE, cortes, otros activos).

## Procedencia congelada (commit `4aae46c8`)
| archivo | sha256 |
|---|---|
| tools/luximb_parity/luximb_holdout_regla_visor.py | 3c44bc32c5d3bbdf6a13c51579366532f5b391fc18995844b406ae13c370e3f7 |
| tools/luximb_parity/luximb_impulsos.py | aed8f267625b21388d6da6a54051f314faad792bb1d14695846100a257ae1f5b |
| tools/luximb_parity/luximb_m11.py | ceb659cda76e7375b98f9aa6fccb0514ac7fd45f22f53c55418258aa454f5a29 |
| tools/luximb_parity/luximb_outcomes.py | da83f3e4b40ae382894fdc525ad4dfdd8110973341d6019e48f2f817b74e4e71 |
| tools/luximb_parity/parity_luximb.py | 2c1919d7acf90375703ad7beb91ba5ab00afbb318ee70fcb025776432f58f925 |
| tools/luximb_parity/build_luximb_nq_m1_bundle.py | 211ff5ec6b3f6304f31b3dd06eddd9c653d77c2c95629e73313147541043eb5a |
| edgelab/bridge/indicators/espejo_impulsos.py | ba73b0126fca9aacaef21cb7461090a6711b3d20ca54c0411454ecaf20ab4ea1 |
Verificacion: el script congelado reproduce NQ 12-25 (99 op, +3,738 pts/op, TP 19 / SL 79 / tiempo 1) con la guarda de
fechas desactivada solo en memoria.

## Falta para abrir
1. **Datos**: ticks de NQ (12-26 / 03-27) desde la sesion del 2026-10-01 (hoy el release llega a 2026-09-25). Construir con
   `build_luximb_nq_m1_bundle.py` solo con trade_date >= 20261001 (el script rechaza datos anteriores).
2. **Protocolo** (`edgelab/autopilot/holdout_apertura.py`): la apertura requiere candidato como corrida ANALYZED del autopilot
   con auditoria CONFORME y env identico; registrar en `holdout_aperturas.jsonl` ANTES de correr. Este candidato nacio fuera
   del autopilot: hay que darlo de alta ahi (corrida + auditoria) sin cambiar la regla, o que Nico apruebe la apertura manual
   con el mismo registro append-only.

## MIRADA EXPLORATORIA DEL HOLDOUT (registrada ANTES de correr) — 2026-10-21
Decision de Nico: "correlo igual, exploratoriamente" con 14 operaciones (sesiones 2026-10-01..2026-10-20, hueco 7-8 oct).
Consecuencias declaradas: (1) la apertura limpia de esta familia sobre estas sesiones queda **consumida**; (2) el resultado
no confirma ni refuta (n << 150) y no se usa para ajustar la regla; (3) una confirmacion futura solo puede usar sesiones
**posteriores a 2026-10-21** con la regla congelada intacta. Script: `luximb_holdout_regla_visor.py` (sha256 3c44bc32...).
