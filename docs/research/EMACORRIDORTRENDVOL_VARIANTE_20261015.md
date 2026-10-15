# EmaCorridorTrendVol — variante con prueba de volumen de sector

Estado: VIGENTE (indicador compilado y verificado con csc; no probado en gráfico)
Fecha: 2026-10-15
Familia / módulo: nt8-capture · indicadores de usuario
Procedencia: `nt8/user_indicators/EmaCorridorTrend.cs` (v4.0, original de Nico) → `nt8/user_indicators/EmaCorridorTrendVol.cs`, generado por `tools/build_emacorridortrendvol.py` (el detector de zonas no se toca).

## Regla (confirmada por Nico el 2026-10-15)
Para cada zona terminada:
1. **Sector de evaluación:** ancho = el **último 25 %** del ancho de la zona **más** un **25 % de su ancho más allá del fin** (ambos son parámetros: `TailPct`, `BeyondPct`); alto = la **banda del canal en el extremo final** de la zona, entre la tangente estructural (TL) y la banda de picos lejanos (FAR), extendida en horizontal (las dos líneas azules del ejemplo).
2. **Volumen operado** del sector: suma del volumen de los ticks cuyo **tiempo** cae en las barras del sector y cuyo **precio** cae dentro de la banda (subserie de 1 tick, `AddDataSeries(Tick, 1)`).
3. **Marca:** la zona se marca si ese volumen es **mayor al percentil 90** (parámetro `VolPercentile`, rango por vecino más cercano) del volumen del **mismo sector en las 50 zonas anteriores** (`LookbackZones`), con al menos `MinPriorZones = 20` zonas previas (si no, no se marca).

## Qué dibuja y qué expone
- Rectángulo del sector (dorado si la zona se marca, gris si no) y, si se marca, un texto `Vol>P90 <volumen> (umbral <umbral>)`.
- Plot `VolFlag`: `+1`/`−1` (dirección de la zona) **en la barra en que se evalúa una zona marcada**, 0 en el resto.

## Causalidad (importante)
Una zona se sabe terminada recién cuando la tendencia se rompe, y el sector llega hasta 25 % más allá de su fin; la evaluación ocurre cuando cierra la barra **siguiente** al final del sector, con ticks de tiempo ≤ esa barra. **La marca llega tarde respecto del fin de la zona**: sirve para clasificar y medir lo que sigue, no como señal de entrada en el fin de la zona.

## Verificación hecha
- Compilación con `csc.exe` contra los assemblies de NT8 (`tools/compile_emacorridortrendvol.py`): **0 errores**; el control negativo (copia con un identificador sin declarar) falla como debe. El gate genérico `tools/compilar_nt8_cs.py` hace ABSTAIN en esta máquina por una DLL duplicada de terceros (`GEXRadarWallsOnNT8.dll` repite tipos de `NinjaTrader.Vendor.dll`); el script propio la excluye y agrega `NinjaTrader.Custom.dll`.
- **No se probó en el gráfico ni contra un cálculo independiente.** Falta: abrirlo en NT8 (F5 en el editor de NinjaScript) y comparar los volúmenes de sector de 3–5 zonas con un cálculo manual o en Python sobre los mismos ticks.

## Uso y límites
- Poné `Days to load` moderado (10–20 sesiones): guarda los ticks en memoria (se descartan los de más de `KeepTickBars` = 1500 barras). Necesita historia de ticks en la base de NT8 para el período cargado.
- Con menos de 20 zonas previas no marca nada: en un gráfico corto casi no habrá marcas.
- Volumen **bruto** (no normalizado por tamaño de zona), como se pidió. Zonas largas y anchas acumulan más volumen: conviene mirar también una versión por barra si el resultado se usa para comparar.
- Esto es un indicador descriptivo. Usarlo como filtro de una estrategia exige su propio manifiesto y la prueba contra el timing sin filtro.
