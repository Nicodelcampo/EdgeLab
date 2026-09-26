# GexLevels para NT8 — instalación y uso

## Qué hay en el paquete

| archivo | qué es |
|---|---|
| `tools/gex/gex_levels.py` | Genera el CSV de niveles. Lee tus parquets SPY (~17 años) para la historia y baja la cadena delayed de CBOE para el día actual. |
| `nt8/GexLevels.cs` | Indicador NT8. Dibuja Call Wall, Put Wall y Gamma Flip por día sobre el chart. |

## Instalación (5 minutos)

1. **El indicador ya está en su lugar**: `nt8/GexLevels.cs`. Copiarlo a
   `C:\Users\<tu usuario>\Documents\NinjaTrader 8\bin\Custom\Indicators\`.
2. En NT8: **New → NinjaScript Editor → click derecho → Compile** (o F5).
   Sin errores = listo.
3. **Generar la historia** (una sola vez, en una terminal de Windows):
   ```
   python tools/gex/gex_levels.py --history
   ```
   Lee `E:\options_data\SPY_options.parquet` y escribe
   `D:\EdgeLab\data\gex\gex_levels.csv`.
4. **Actualizar el día actual** (cuando quieras, 10 segundos):
   ```
   python tools/gex/gex_levels.py --today
   ```
   Baja la cadena delayed de CBOE (gratis, sin API key) y agrega la fila de hoy.
5. En el chart de NT8: **Indicators → GexLevels → OK**.

## Parámetros del indicador

- **Levels File**: dónde está el CSV (default `D:\EdgeLab\data\gex\gex_levels.csv`).
- **Symbol**: `SPY` (el CSV puede tener varios símbolos; filtra).
- **Price Offset (basis)**: los niveles están en puntos de índice (SPY×10 ≈ SPX).
  Si el chart es **ES**, el futuro cotiza ~SPX + basis (típicamente +20 a +60,
  varía con tasas y días al vencimiento). Mirá la diferencia ES − SPX del día y
  ponela acá. Si el chart es SPY/SPX directo, dejalo en 0.
- **Max Days Back**: cuántos días hacia atrás dibuja (para no saturar el chart).
- **Show Labels**: etiquetas con el precio de cada nivel y el régimen.

## Qué dibuja

- **Call Wall** (naranja): strike con mayor gamma de calls → techo / resistencia.
- **Put Wall** (verde): strike con mayor gamma de puts → piso / soporte.
- **Gamma Flip** (amarillo punteado): corte de régimen. Arriba = mercado que
  amortigua (rango); abajo = mercado que amplifica (tendencia/violencia).
  La etiqueta incluye el régimen (`POS`/`NEG`) y el GEX neto en miles de millones.

## Notas honestas

- Los datos de CBOE vienen con **15 minutos de delay**. Para niveles GEX diarios
  no importa: el OI es un snapshot de la noche anterior de todos modos.
- La **convención de signo** (calls positivo, puts negativo) es la estándar de la
  industria, pero sigue sin validación formal — es el pendiente P-39/GEX-M0 del
  repo. Los **niveles** (walls, flip) son robustos a eso; la **narrativa** de
  "los dealers están largos/cortos" es el supuesto, no el dato.
- El gamma de la historia (parquets) viene del proveedor de esos datos; el gamma
  del día actual (CBOE) lo calcula el script con Black-Scholes desde la IV.
  Mismo esquema de salida en ambos caminos.
- Este indicador es para **observar** cómo el precio se comporta respecto de los
  niveles. No es una señal de entrada.
