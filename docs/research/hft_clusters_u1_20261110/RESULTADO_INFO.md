# Resultado del paso INFO (definición de 4 zonas) — rebote e imán contra control

Estado: RESULTADO (2026-11-10). Pre-registro `PREREGISTRO_E0_E_INFORMACION.md` §3 y §7. Datos: `HFTC_info.json`, `HFTC_info.csv`.
Recomendaciones: `RECOMENDACIONES_info.md`. DESC 2025-07 → 2026-03, definición elegida por el E0 (4 zonas; 22–73 clusters por sesión).

## Rebote en el borde (real − control desplazado), carrera ±X en bruto
| Activo | Eventos reales | Control | Media real | Media control | Diferencia | IC90 | MDE |
|---|---|---|---|---|---|---|---|
| NQ | 3.097 | 7.515 | +0,003 | +0,030 | −0,027 | [−0,065, +0,012] | 0,058 |
| ES | 1.342 | 2.250 | 0,000 | +0,004 | −0,004 | [−0,064, +0,053] | 0,089 |
| GC | 5.184 | 7.893 | −0,002 | +0,018 | −0,020 | [−0,051, +0,011] | 0,046 |
| YM | 129 | 206 | −0,031 | −0,024 | −0,007 | [−0,18, +0,16] | 0,255 |
| **Conjunto** | **9.752** | **17.864** | **0,000** | **+0,021** | **−0,021** | **[−0,043, +0,001]** | **0,033** |
Stouffer p = 0,89. **No pasa.** El rebote en un cluster de 4 zonas no supera al de un nivel cualquiera; si algo, va levemente en
contra (el precio atraviesa el cluster un poco más que el nivel desplazado), sin separarse de 0. Con MDE 0,033 queda descartado
cualquier efecto a favor que importe. El desenlace real (≈ 0) está lejos del umbral económico 0,08.

## Imán (vuelve al borde antes que al espejo; real − control temporal)
| Activo | Reales | Control | Media real | Media control | Diferencia | IC90 |
|---|---|---|---|---|---|---|
| NQ | 3.690 | 5.864 | +0,025 | +0,053 | −0,027 | [−0,065, +0,010] |
| ES | 2.858 | 4.662 | +0,012 | +0,036 | −0,024 | [−0,062, +0,013] |
| GC | 8.581 | 8.131 | +0,029 | +0,043 | −0,013 | [−0,040, +0,014] |
| YM | 219 | 726 | 0,000 | −0,091 | +0,091 | [−0,027, +0,211] |
| **Conjunto** | **15.348** | **19.383** | **+0,025** | **+0,039** | **−0,014** | **[−0,033, +0,004]** |
Stouffer p = 0,81. **No pasa.** El cluster no atrae más que un nivel de otra hora con la misma geometría (MDE 0,028). YM, el único
positivo, tiene muy pocos eventos y su IC cruza 0.

## Lectura y alcance
- Muerte con alcance preciso: **clusters de 4 zonas** (la definición frecuente y angosta), rebote en el primer toque tras alejarse
  X/2 e imán a la distancia del alejamiento, en 4 activos. No alcanza a las definiciones grandes del E0-b ni a las siete
  definiciones de rebote, que corren aparte.
- Error de método encontrado con este resultado y corregido antes de usarlo: el recomendador ignoraba el signo esperado y medía la
  inconsistencia entre activos con el error combinado; marcaba «INDAGAR» un efecto en contra. Ver `edgelab/research/recomendador.py`.
