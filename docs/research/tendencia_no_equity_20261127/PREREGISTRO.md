# TENDENCIA-NO-EQUITY: momentum de serie de tiempo mensual en 14 mercados no ligados a acciones (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — una sola hipótesis, fijada antes de bajar retornos.

- **Origen:** frente 3 de `docs/research/auditoria_cartera_20261126/REVISION_CLAUDE.md` §3, aprobado por Nico el 2026-11-27 («arrancá y
  realizá todos los pasos»). Es la forma que `F-LIT-MACRO-CFD` dejó abierta: TSMOM **mensual**, manteniendo fines de semana. Requiere
  una cuenta que permita mantener posiciones (FTMO Swing o broker propio): eso ya está aprobado como frente.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2→EF3** (una hipótesis de la literatura: se descubre en DESC y se replica en REP de A5). **Familia nueva:**
  `TENDENCIA_NO_EQUITY`. **Pruebas:** 1.
- **Herramienta:** `python tools/tendencia_no_equity.py bajar` (precios, sin retornos) y `medir` (llama a `exigir_contada`).

Cambio respecto a falla previa: lo que falló fue en otra forma y otro dato.
- `F-LIT-MACRO-CFD`: TSMOM semanal sin fines de semana, sobre CFD de Dukascopy.
- `F-TURTLES-ORO-*`: rupturas Turtles con cierre de viernes, activo por activo.

Esta prueba cambia tres cosas:
- es TSMOM mensual (Moskowitz, Ooi y Pedersen 2012), una cartera con riesgo parejo y una sola prueba;
- mantiene la posición todo el mes;
- usa precios ajustados que ya incluyen el costo del roll (ETFs).

No hay perillas ni grilla.

Antecedentes:
- `macro_literatura_20261114/RESULTADO.md` (`F-LIT-MACRO-CFD`): las formas semanal e intradía no superan el nulo en 27 activos.
- `F-TURTLES-ORO-MESETA-C`: CL, 6E, 6J y ZB ≈ 0 con Turtles de viernes.
- `auditoria_cartera_20261126` (`F-MULTIACTIVO-MECANISMOS-AL-NIVEL-DEL-AZAR`): WTI Donchian 55/20 con 56 operaciones.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36: la unidad es el retorno sobre el capital de la cartera, % mensual; K49:
costos declarados antes; K27: potencia antes de abrir holdout).

Potencia previa: TSMOM diversificado tuvo Sharpe ≈ 1 en 1985–2012 y ≈ 0,3–0,5 después de 2012 (la literatura posterior). Con Sharpe anual
0,5 y ≈ 130 meses DESC (2008-01 → 2026-09, 7 de cada 12 meses), t esperado ≈ 0,5/√12 × √130 ≈ 1,65: potencia ≈ 0,5 al 5 % de una cola.
Con REP (≈ 37 meses), t esperado ≈ 0,9. **Es una prueba con potencia baja**: un nulo no cierra la familia (se publica con su MDE); un
positivo sólo pasa a papel con la potencia del HOLDOUT A5 recalculada (`tools/potencia_previa.py`) antes de abrirlo.

Diagnóstico de mecanismo: sin grilla. La única regla es el signo del retorno de 12 meses, con tamaño inverso a la volatilidad de 63 días.
Se publican:
- los meses positivos por año (episodios);
- la contribución por clase de activo (tasas, metales, energía, granos, divisas), para ver si es «tendencia general» o un solo activo
  (como el oro en Turtles).

## Justificación económica
Los mercados de tasas, materias primas y divisas tienen tendencias de meses. Las mueven los ciclos de política monetaria, las sorpresas de
oferta y la cobertura lenta de productores y bancos centrales. Seguirlas con riesgo parejo cobra una prima documentada desde hace un siglo
(Hurst, Ooi y Pedersen 2017). Además rinde más cuando las acciones caen fuerte (2008, 2022), que es justo lo que le falta a una cartera
de índices intradía.

## Diseño (fijo)
- **Activos (14, elegidos por clase y liquidez, no por resultado):**

  | Clase | ETFs |
  |---|---|
  | Tasas | TLT, IEF |
  | Metales | GLD, SLV, DBB |
  | Energía | USO, UNG |
  | Granos | DBA |
  | Divisas | FXE, FXY, FXB, FXA, FXC, FXF |

  Precio de cierre ajustado de Yahoo (dividendos y splits; los ETFs de materias primas ya cargan el costo del roll). Datos 2005 →
  2026-09-30, corte estricto.
- **Señal:** al último cierre de cada mes, signo del retorno de 12 meses (252 sesiones) de cada activo con ≥ 252 sesiones de historia.
- **Tamaño:** peso_i = señal_i × (0,40 / σ_i) / N.
  - σ_i es la volatilidad anualizada de 63 sesiones (al cierre de la señal).
  - N es la cantidad de activos con señal.
  - Tope de 2 por activo.
  - Es el diseño de Moskowitz, Ooi y Pedersen.
- **Ejecución:** al cierre del último día hábil del mes; se mantiene el mes entero, con fines de semana.
- **Costos:** 5 pb por lado sobre el cambio de peso (spread y comisión de ETFs líquidos); se informa también 10 pb por lado.
- **Medida:** retorno mensual de la cartera (% del capital).
- **Partición A5 por el mes del retorno:**
  - DESC: descubrimiento (1.ª lectura).
  - REP: réplica.
  - HOLDOUT y EMBARGO: sellados, sin leer.
  - Desde 2026-10-01: nada.
- **Prueba (1):** media mensual > 0 en DESC (t de una cola, α 0,05). La réplica se lee recién si DESC pasa.

## Cómo se lee (decidido antes)
- **Pasa a papel con plan de potencia del HOLDOUT A5** si las dos se cumplen:
  - t ≥ 1,65 en DESC;
  - media > 0 en REP.
- **Sin evidencia, viva:** DESC con t < 1,65 y media > 0. Se publica el MDE; no cierra la familia (potencia ≈ 0,5).
- **En contra:** media ≤ 0 en DESC. Se publica con su MDE. Tampoco cierra si el MDE supera Sharpe 0,5.
- Además, siempre: correlación mensual con la cartera Intradía (series de `estabilidad_cartera_20261126`, sólo meses DESC), para saber
  cuánto diversificaría.

## Cómo podría refutarse
- DESC con media ≤ 0 y MDE menor que un Sharpe de 0,5: la tendencia en no-equity, con este diseño estándar, no paga después de costos en
  2008–2026.
- Si la ganancia viene de un solo activo (> 60 % del total en DESC), no es «tendencia diversificada» sino ese activo. Se informa así y
  no se promueve como cartera.
