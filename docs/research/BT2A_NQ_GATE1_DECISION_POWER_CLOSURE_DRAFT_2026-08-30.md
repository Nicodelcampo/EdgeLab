# BT2A NQ Gate 1 — cierre target-free adicional (draft)

Fecha: 2026-08-30. Alcance: diseño y planificación sin leer outcomes, future path, PnL ni holdout.

## Cerrado desde este entorno

1. **Encoding primario:** valor firmado en ticks por celda: `+b` si cruza primero a favor, `-b` si cruza primero en contra y `0` en timeout; empate en la misma observación = adverso; trayectoria incompleta = exclusión con motivo.
2. **Contraste confirmatorio:** `K_ABS - N_RAND`, pareado dentro de sesión CME.
3. **Multiplicidad:** Holm bilateral sobre las 16 celdas del único contraste confirmatorio. `K_BT2` y `K_ABS_SHUFFLE` quedan como controles secundarios que no pueden, por sí solos, activar la etiqueta positiva.
4. **Varianza:** varianza muestral no sesgada de los contrastes por sesión con peso igual. Réplicas N_RAND se promedian dentro de la sesión antes de formar un único contraste; se prohíbe tratar eventos como réplicas independientes.
5. **MDE de diseño:** 1 tick NQ, significado mecánico y no económico.
6. **ICC de planificación:** 0,20, máximo de la grilla preregistrada; es un supuesto conservador, no una estimación desde outcomes NQ.
7. **K_ABS medido:** 152.695 eventos / 234 sesiones = 652.542735042735 eventos/sesión, ligado al manifest físico `b3177b...` y Parquet `96281e...`.
8. **SD conservador:** bajo el encoding firmado y barrera máxima 30, el contraste por sesión vive en [-60,60]; Popoviciu da SD <= 60 ticks. Con Bonferroni 16, alpha 0,05, power 0,80 y MDE 1, se requieren 51,897 sesiones efectivas. Hay 234. Esta cota es válida pero demasiado conservadora para autorizar la corrida.

## Lo que queda necesariamente para Claude

- Publicar y bindear físicamente el resultado V2 (`bt2_v2_result_file_sha256`, dataset y path).
- Extraer del artefacto congelado los eventos/sesiones/densidad de `tick_25_IMB30_VOL10`.
- Demostrar capacidad N_RAND por los estratos congelados.
- Si se quiere reemplazar la cota SD=60 por un prior empírico, aportar una fuente pre-outcome, hash-bound y justificación escrita de transferencia; no usar outcomes NQ Gate 1.
- Rebasar este patch sobre el tip vivo, actualizar hashes padre, correr suite/preflight y mantener freeze y run separados.

## Estado

`NOT_READY`: resolví las cuatro decisiones y todos los inputs que se desprenden de los datos ya publicados, pero no falsifiqué la densidad K_BT2 ni la capacidad N_RAND. La cota de potencia conservadora tampoco sostiene suficiencia con 234 sesiones.
