# Resultados — Recálculo del candidato LUX-IMB (regla del visor) sobre el release de Kaggle con costos canónicos

Estado: MEDIDO (PROVISIONAL: el release es `CANDIDATE_NOT_RESEARCH_APPROVED`). Fecha: 2026-10-24. Etapa EF2: no confirma.
Pre-registro: `PREREGISTRO_RECALCULO_CANONICO_RELEASE_20261024.md` (commit `1ffa3339`, pusheado antes de correr). Registro global: `luximb_20261024/recalculo_canonico_release`, 1 prueba.
Salida completa: `RECALCULO_CANONICO_RELEASE_20261024.json`. Código: `tools/luximb_parity/luximb_recalculo_canonico_release.py`.
Procedencia: corrió con árbol limpio en `1ffa3339` (rama `claude/project-thread-idwi7k`). Datos: `data/NQ_ticks.parquet` del dataset `nicolasbuttaro/edgelab-liquid-ticks-20261014`, sha256 `cccc7c80…a78a89`, igual al manifiesto. Sin holdout (último trade date 20260925).

## 1. Resultado
**El candidato sigue SIN_POTENCIA. Con la fricción canónica de NQ deja +4,05 pts por operación (+0,20 R), no +4,95.**

| | valor |
|---|---|
| operaciones / sesiones | 500 / 212 |
| neto por op. con la contabilidad de la campaña (0,225 + ticks) | +4,92 pts |
| **neto por op. canónico base (1,5455 pts)** | **+4,05 pts, IC90 por sesiones [+0,36, +7,56]** |
| neto por op. canónico adverso (2,0455 pts) | +3,55 pts |
| en R (riesgo 0,2·D) | +0,198 R, IC90 [+0,013, +0,375], p unilateral 0,035, t 1,81 |
| pruebas en la familia / en el programa LUXIMB | 47 / 106 |
| DSR / efecto esperado fuera de muestra tras selección | 0,33 / 0 |
| económico canónico | pasa los 4 duros: sin top-5 +0,15 R, adverso +0,17 R, ningún período > 80 %, 4/6 períodos positivos |
| escalera | **SIN_POTENCIA**: viva en reserva; harían falta ~944 operaciones para distinguir el efecto del cero |

## 2. Por período (pts NQ)
| contrato | ventana del release | n | TP / SL / tiempo | contab. campaña | neto canónico | por op. |
|---|---|---:|---|---:|---:|---:|
| 09-25 | 20250805–20250916 | 20 | 2 / 18 / 0 | −127,8 | −144,8 | −7,24 |
| 12-25 | 20250917–20251215 | 99 | 19 / 79 / 1 | +370,0 | +284,0 | +2,87 |
| 03-26 | 20251216–20260316 | 100 | 22 / 77 / 1 | +573,9 | +486,4 | +4,86 |
| 06-26 | 20260317–20260612 | 130 | 25 / 102 / 3 | +808,8 | +695,9 | +5,35 |
| 09-26 | 20260616–20260915 | 150 | 36 / 114 / 0 | +846,1 | +714,1 | +4,76 |
| 12-26 | 20260918–20260925 | 1 | 0 / 1 / 0 | −12,1 | −12,9 | −12,90 |

## 3. Reproducción
Los seis períodos reproducen **exacto** (n y puntos) el tablero publicado el 2026-10-20 y la escalera del 2026-10-22, que habían corrido sobre bundles locales de la máquina de Nico. Desde ahora el número es reproducible sólo con el release de Kaggle, sin archivos locales.

## 4. Lectura
- La revisión del 2026-10-24 marcaba «no medido: el candidato con costos canónicos». En realidad la escalera del 22/10 ya lo había calculado (`ESCALERA_CANDIDATOS_REALES.json`); lo que faltaba era hacerlo con datos verificables. Las dos cuentas coinciden.
- La fricción canónica le resta ~0,87 pts por operación. Eso no la mata: el IC90 en puntos sigue arriba de cero. Pero el IC en R apenas excluye el cero (+0,013), con 47 pruebas en su familia el efecto esperado tras selección es 0, y todos los períodos se miraron antes de congelarla. **No es un edge.**
- Lo que puede decidirla es una muestra no mirada: el holdout desde el **2026-10-22** (ventana 10-01 a 10-21 ya consumida, `HOLDOUT_VENTANAS.jsonl`), una sola apertura, por protocolo. A ~2,4 op. por sesión, ~944 op. son unas 400 sesiones; el holdout solo no da la potencia en plazo corto.

## 5. Alcance
Esto mide exactamente la regla congelada (`luximb_holdout_regla_visor.py` sha256 `3c44bc32…`), en NQ, en desarrollo (ago-2025 a sep-2026), con costos canónicos. No dice nada de otras geometrías, otros instrumentos ni del holdout.
