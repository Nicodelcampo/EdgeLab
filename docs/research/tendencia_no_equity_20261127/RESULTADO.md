# TENDENCIA-NO-EQUITY: resultado

Estado: RESULTADO — SIN_EVIDENCIA, viva (lectura pre-registrada en `PREREGISTRO.md`). La réplica (REP) no se leyó y el HOLDOUT A5 sigue
sellado.

Herramienta: `python tools/tendencia_no_equity.py medir` (`RESULTADO.json`, `SERIE_MENSUAL_LEIDA.csv`). Datos: Yahoo, precio ajustado,
14 ETFs, 2005 → 2026-09-30 (`data/tendencia_no_equity/PROCEDENCIA.json`, con el sha256 de cada respuesta).

## Qué dio (DESC de A5, 130 meses 2008–2026, costo base 5 pb por lado)
| medida | valor |
|---|---|
| retorno medio por mes | +0,29 % del capital |
| t (una cola) | 0,96 (p 0,17) |
| Sharpe anual | 0,29 |
| meses positivos | 50 % |
| MDE (potencia 0,8) | +0,75 %/mes, Sharpe 0,76 |
| con 10 pb por lado | +0,26 %/mes, t 0,87 |
| correlación mensual con la cartera Intradía | +0,07 |

- No llega al umbral pre-registrado (t ≥ 1,65). La media es positiva, así que la lectura es SIN_EVIDENCIA, viva. La MDE (Sharpe 0,76)
  supera el Sharpe esperado de la literatura posterior a 2012 (0,3–0,5): un nulo así no distingue «no hay tendencia» de «hay una chica».
- **No es tendencia general.** Energía aportó el 40 % de la ganancia de DESC y metales el 38 %; USO solo, el 37 %. Tasas aportaron 2,5 %.
- **Años:**
  - fuerte en 2008–2015 (2011 +18 %, 2015 +11 %);
  - negativo en 2016–2017, 2019 y 2021–2024 (2024 −8,9 %).

  Es la misma forma que describe la literatura (la tendencia diversificada se apagó después de 2012, salvo episodios).
- Diversificaría (+0,07 con la Intradía), pero no hay evidencia de que pague.

Diagnóstico de grilla: sin grilla (una regla fija); la contribución por clase y por año está arriba y en `RESULTADO.json`.
Episodios: 50 % de meses positivos en DESC. Años con suma mensual positiva: 11 de 19. Las pérdidas se concentran en 2016–2017 y 2021–2024.

## Qué queda
- No se abre el HOLDOUT A5 ni se lee la réplica: DESC no pasó.
- No cierra la familia (potencia ≈ 0,5 con el efecto esperado). Retomarla sólo con más información por mes: futuros reales con más
  mercados (40–60), o como filtro de régimen de otras reglas, nunca eligiendo los activos que ganaron (energía y metales).

Aporte al referente: descarta, con evidencia publicada y su MDE, que la tendencia mensual estándar en no-equity sea hoy un diversificador
con ventaja neta para la cartera; evita sumar a la cartera un motor que en 2021–2024 perdió.
