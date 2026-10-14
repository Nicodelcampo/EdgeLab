# Etapa C — celda GC 04:15 sobre oro spot, lecturas intermedias (2026-10-04)

Pre-registro: `PREREGISTRO_ETAPA_C_GC_SPOT.md` con enmiendas C1 y C2 (escritas antes de cada corrida). Datos: ticks de XAU/USD de Dukascopy (cotizaciones bid y ask). Resultados: `etapaC_spot_R1.json`, `etapaC_spot_R2.json`; código: `tools/barrido_horario_etapa_c_spot.py`.

**Según la enmienda C2, R1 y R2 son miradas intermedias y descriptivas.** El rótulo «Replica» que imprime el script no es una decisión; la decisión se toma una sola vez sobre la ventana completa 1-jul a 30-sep, cuando esté descargado el tramo restante. Sin calibración de fuente (enmienda C1): spot no es futuros.

| | R1: 14 a 30-sep (13 sesiones, todas elegibles) | R2: R1 + 1 a 9-jul (20 sesiones, 18 elegibles) |
|---|---|---|
| Celda (corto tras subida), operaciones | 9 | 11 |
| Neto medio por operación (ticks de GC tras spread y comisión) | **+22,3** | **+17,9** |
| Operaciones ganadoras | 67 % | 64 % |
| z / p unilateral (descriptivo, sin ajuste por miradas) | 1,85 / 0,031 | 1,82 / 0,034 |
| Corto sin condición, operaciones / neto medio / p | 13 / +28,9 / 0,011 | 18 / +30,9 / 0,002 |
| Largo tras bajada (espejo), operaciones / neto medio | 4 / −56,5 | 7 / −63,2 |

- El 8 y 9 de julio salen no elegibles por tener la descarga incompleta (falta una de las dos horas); la regla de elegibilidad de la enmienda los excluyó sin mirar resultados. Se completarán en la descarga pendiente.
- Spread mediano de la ventana en spot: USD 0,58 (≈ 5,8 ticks de GC), ya incluido en los netos; es casi el doble que el de COMEX.
- R1 por día (neto en ticks): −10,3; −21,1; +61,8; +51,3; +91,3; +10,8; +23,0; −10,7; +4,9. Tres de nueve son negativos y el 21-sep aporta el 45 % de la suma; sin él, el neto medio es +13,7.

## Lectura
- Con muestras muy pequeñas (9 y 11 operaciones), el signo y el orden de magnitud coinciden con lo observado en los futuros antes de junio (+21,3 ticks). No es una decisión ni una confirmación.
- **«Corto sin condición» rinde igual o más que la celda condicionada** en estas sesiones (+28,9 y +30,9 contra +22,3 y +17,9), y el espejo «largo tras bajada» pierde fuerte. En los datos de futuros la condición sumaba unos 9 ticks; aquí no suma. Lo que se repite es un sesgo vendedor a esa hora, no el filtro de la subida previa.
- Las dos miradas comparten sesiones (R2 contiene a R1): no son dos pruebas.
- Pendiente: tramo del 10-jul al 11-sep (descarga en curso). La decisión pre-registrada se aplica entonces a la ventana completa.
