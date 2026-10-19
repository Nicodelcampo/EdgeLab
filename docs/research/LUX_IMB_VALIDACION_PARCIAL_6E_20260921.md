# LUX-IMB (OG + VI) — reconstrucción en Python y validación parcial contra 6E

> 2026-09-21. Target-free: solo geometría de barras. Sin retornos, sin holdout. Reproducir:
> `.venv\Scripts\python tools\verify_lux_imb_vs_6e_oracle.py` (sale 0).

## Resultado
Oráculo: las 34.179 zonas `ImbalanceDetectorLuxAlgoMTF` (OG + VI, FVG apagado) que NT8 exportó para **6E Continuo**, sobre
353.914 barras M1 (`viewer/nt8_bridge/bundles/6E_CONT.json`). Módulo: `edgelab/research/lux_imb_series.py`
(vectorizado; la referencia escalar sigue en `lux_imb.py`).

| Comparación (geometría `body`) | Coinciden |
|:--|--:|
| Zonas del oráculo que Python también produce (familia, dirección, `t0`) | 34.179 / 34.179 |
| Zonas de Python que el oráculo no tiene | 0 |
| Bordes (`top`, `bottom`) | 34.179 / 34.179 (OG 32.030, VI 2.149) |
| Vencimiento `t1` | 34.179 / 34.179 |
| `fill_level` | 34.179 / 34.179 |
| Bandera de toque | 34.179 / 34.179 |

Con la geometría corregida `wick` (mecha a mecha) los sucesos son los mismos pero **1.078 bordes OG difieren**
(y 690 `fill_level`, 11 toques): el export de NT8 es cuerpo a cuerpo. Eso confirma con datos el hallazgo de
`LUX_NT8_AUDIT_2026-08-11.md`: el `.cs` recibido dibuja el OG con el cuerpo aunque lo detecta con la mecha.

## Semántica reconstruida (`lux_og_vi_series_v1`)
- Pares de barras consecutivas de la lista, sin mirar huecos de tiempo. `t0` = tiempo de la barra previa.
- OG: `low[i] > high[i-1]` (alcista), `high[i] < low[i-1]` (bajista); bordes por cuerpo (`body`, literal del `.cs`).
- VI: las desigualdades del `.cs` (`lux_imb.detect_volume_imbalances`), 2.149/2.149 exactas.
- Vencimiento: barra `i_prev + 501` (Extend 500); se proyecta con el paso de barra si cae fuera de los datos.
- `fill_level`: alcista → `bottom`; bajista → `top`. Toque: cruce **estricto** en las barras `i_prev+2 … i_prev+500`.
- Todas las zonas quedan `ACTIVE`: no hay mitigación que las borre (consistente con la corrección de fuente 2026-08-15).

## Qué valida y qué no (validación PARCIAL)
Valida la lógica de detección y de ciclo de vida, **dadas esas barras**. No valida:
1. Las barras M1: vienen del mismo bundle, no se contrastaron con los ticks.
2. Otros activos, otros timeframes, otro `Extend`, filtro de ancho (el export usa el defecto, sin filtro) ni FVG.
3. Disponibilidad causal: el export no trae `available_at`; se toma el cierre de la barra actual (`i_prev + 1`).
4. Cuál geometría es la «correcta»: `body` reproduce NT8; `wick` es coherente con la condición de detección. Decisión de Nico.
Las 3 variantes restantes del bundle (FVG Only, Near-Miss, Completo) no se reconstruyeron: FVG está fuera de la
configuración de trabajo y Near-Miss es clasificación retrospectiva (mezcla detector y resultado).

## Siguiente
Barras M1 de los otros 10 activos desde ticks pre-holdout → zonas con `body` → bundles del visor; el filtro de ancho, si
se usa, escalado por ATR o porcentaje (no en puntos). Sin oráculo propio esos activos quedan provisionales.

## Barras M1 desde ticks para los 11 activos (2026-09-21)
`tools/build_lux_imb_m1_bundles.py` genera un bundle por contrato (`<ACTIVO>_<contrato>_M1`, 55 en total) con las barras M1
armadas desde ticks pre-holdout y las zonas LUX-IMB (`body`, sin filtro de ancho). Todas `PARITY_ABSTAIN` salvo lo ya validado en 6E.

**Hallazgo sobre la alineación.** Las barras M1 del export de NT8 de 6E (`6E_CONT.json`) solo se reproducen desplazando los ticks
**+30 s** antes de agrupar por minuto: 1.319 de 1.331 barras con OHLC exacto el 2026-06-23 (99,1 %), contra ~15 % con minuto UTC
estándar. El pico es agudo (30 s → 1.319; 29 s y 31 s → ~1.140). No se sabe si es una convención de NT8 o del generador de ese
bundle. Los bundles nuevos usan minuto estándar (`--tick-offset-s 0`); con `--tick-offset-s 30` se reproduce el export de 6E.
Las zonas de este documento (34.179/34.179) se compararon sobre las barras del propio export, así que no dependen de esto.

**Sin filtro de ancho**, la cantidad de zonas por barra depende mucho del activo (MBT, con tick de 5 USD y minutos ralos, genera
~81.900 zonas en 212.000 barras). Comparar activos exige un filtro escalado (ATR o porcentaje), como en HFT.
