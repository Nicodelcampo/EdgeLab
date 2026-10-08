# Paridad aVolZonePOI2 — MNQ 12-26, 25 tick, configuración de Nico (2026-10-08) — **PASS exacto**

- Oráculo: `data/nt8_oracles/avolzonepoi2_MNQ1226_25t_20260715_20260930.csv`. Chart con merge back-adjusted y roll el
  14-09; misma reconstrucción que la paridad de 200t (offset +299,75 puntos antes del roll).
- **Configuración:**
  - detección y umbral por defecto (10 / ×2 / gap 1 / mín. 2 / Suma / franja 15 min CT / p95 / 20 sesiones / mín. 20);
  - **OB:** 100 barras, **6 alturas**, 8 ticks, **4 %**;
  - **racimo:** **mín. 6 zonas, 500 velas, 30 ticks**.
- Comando: `ZP_SPEC=25 ZP_PARAMS='{"ob_away_heights":6.0,"ob_max_inside_pct":4.0,"racimo_min":6,"racimo_bars":500,"racimo_altura_ticks":30}' python tools/paridad_avolzonepoi2.py <csv>`.

| | NT8 | Python | iguales |
|---|---|---|---|
| bloques | 367.455 | 367.455 | 100 % |
| zonas (barra, bajo, alto, score, umbral) | 21.701 | 21.701 | 100 % |
| clasificación OB (estado y barra de decisión) | 4.118 OB | 4.118 OB | 100 % |
| entrada de cada zona a un racimo (zona y barra) | 1.190 | 1.190 | 100 % |

**No verificado:** el piso, el techo y el inicio de cada racimo (las líneas). El log no trae las filas `C`, porque el
`.cs` que corrió no tenía esa línea compilada. Las líneas se derivan de las zonas del racimo, que sí coinciden.
