# CRIPTO-PIT: resultado

Estado: RESULTADO — viva sin evidencia (lectura pre-registrada en `PREREGISTRO.md`): no pasa al HOLDOUT A5, que sigue sellado. No entra a
la cartera.

Herramienta: `python tools/cripto_pit.py medir` (`RESULTADO.json`, `SERIES_DESC_REP_BASE.csv.gz` con HOLDOUT y EMBARGO en NaN).

Datos:
- **Universo:** `UNIVERSO_PIT.csv`, 239 monedas pasaron alguna vez por el top-25, entre ellas LUNA, SRM, FRONT, TOMO, YFII, HNT y LEND,
  que dejaron de cotizar.
- **Velas y funding:** data.binance.vision, 2020-09 → 2026-09-30, guardadas en `data/crypto_binance_pit/`.
- **Huecos y faltantes:**
  - el archivo de febrero de 2022 de Binance trae un hueco de 3 días en 44 monedas (es del origen y no adelanta información);
  - `币安人生USDT` (2025) quedó sin funding (va con 0).

## Qué dio (USD sobre $10.000, costo base 20 pb ida y vuelta + funding real)

| regla | DESC $/mes (t) | REP $/mes (t) | DESC+REP $/mes (t, p una cola) |
|---|---|---|---|
| 1/N (principal) | +126 (1,79) | **−84 (−0,62)** | +76 (1,21; p 0,11) |
| Donchian 1D | +42 (0,46) | −22 (−0,13) | +27 (0,34; p 0,37) |
| EMA 4H | +235 (1,79) | −166 (−0,63) | +141 (1,18; p 0,12) |
| Momentum transversal | +100 (1,92) | −65 (−0,55) | +61 (1,25; p 0,11) |

- **Ninguna pasa BH q 0,10** sobre las 4 (p mínima 0,106).
- **Contraste con la auditoría:** con las 8 monedas de hoy y sólo comisión, la REP del 1/N daba +$382/mes. Con el universo completo es
  negativa en las tres reglas. La REP positiva venía de haber elegido hoy las monedas que sobrevivieron.
- **Sensibilidad al costo:** con 10 pb (lo de la auditoría) el 1/N da DESC+REP +$102 (t 1,62) y REP −$57. Con 30 pb, +$51 (t 0,80).
  - Ninguna regla pasa de positiva a ≤ 0 entre 10 y 20 pb en DESC+REP: la segunda condición de refutación no se cumple.
  - EMA 4H es la más sensible: −$52/mes por cada 10 pb.

## Lectura pre-registrada
- **Pasa al plan del HOLDOUT A5:** no.
  - t DESC+REP = 1,21 < 2;
  - REP < 0.
- **Refutada:** no. La media DESC+REP es > 0.
- **Queda viva sin evidencia:**
  - papel/forward con vigilancia secuencial si Nico abre una cuenta cripto;
  - no se suma a la cartera;
  - el HOLDOUT A5 de `CRIPTO_BINANCE` sigue sin abrir.

Diagnóstico de grilla: sin grilla (3 reglas fijas y su 1/N); escenarios de costo y meses por bloque arriba y en `RESULTADO.json`.
Episodios: 1/N con 62 % de meses positivos en DESC y 50 % en REP (39 y 12 meses).

## Qué queda
- La decorrelación con la cartera de futuros (+0,02) sigue siendo real. Lo que falta es evidencia de ventaja neta con el universo
  completo.
- No se re-optimizan estas reglas sobre estos datos (sería elegir mirando la réplica). Una campaña nueva necesita reglas pre-registradas
  en DESC y su propia REP.

Aporte al referente: desarma un falso positivo antes de arriesgar capital. La ventaja cripto de la auditoría dependía de las monedas
elegidas con conocimiento de hoy y de no cobrar deslizamiento. Con universo punto en el tiempo y costo realista, la réplica es negativa.
