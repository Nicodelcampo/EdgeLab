# Pre-registro — CARRIL2_VOL_LOCAL: Corrección K61 de Volatilidad Implícita Local en Reglas `C2_VBB`, `C2_VZ` y `C2_EVRP` (2006–2026-09)

Estado: PREREGISTRO — EF3 corrección K61 en `CARRIL2_VOL_LOCAL`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v5 — §0–§8 (K32, K51 conteo previo, K61 insumo local obligatorio al transferir reglas de volatilidad, K62 verificación previa de disponibilidad de fuentes).
Antecedentes: «VBB VZ EVRP volatilidad local AXVI VXD RVX GVZ» — familias parecidas: ninguna; NO_REPETIR: F-C2-VBB-DBO-P80, F-DIA-TENDENCIA-NO-ANTICIPABLE; código: tools/confianza_sin_forward.py:58, edgelab/config.py:84, edgelab/bridge/sessions.py:18
Cambio respecto a falla previa: `F-C2-VBB-DBO-P80` evaluó `C2_VBB` con `^VIX` y `confianza_sin_forward.py` aplicó por error `^VIX` de EE. UU. a índices extranjeros (`K61`); `F-DIA-TENDENCIA-NO-ANTICIPABLE` refiere a filtrar tendencia intradía. Aquí corregimos el error K61 sustituyendo `^VIX` por la **volatilidad implícita local real** exclusivamente en los instrumentos donde la fuente verificada tiene serie histórica real con TLS válido.
Diagnóstico de mecanismo: no aplica — cero grilla paramétrica (`3` contrastes pareados «volatilidad local vs VIX» sobre reglas congeladas `C2_VBB`, `C2_VZ` y `C2_EVRP` y sus controles `N`).
Potencia previa: `4` activos × `18–20` años (`2006/2008 → 2026-09`, `< 2026-10-01`) evaluando sensibilidad pareada del mecanismo de volatilidad (potencia ~`0,50–0,70` para diferencias moderadas en las 3 reglas de volatilidad).

## Justificación económica, cobertura verificada (K62) e instrumentos evaluados
Antes de pre-registrar se verificó la disponibilidad real desde este entorno:
- **Disponibles y verificados:**
  1. `ASX200` (Yahoo `data/confianza_sf/ASX200.parquet`) ← **`^AXVI`** (Yahoo Finance S&P/ASX 200 VIX, `2008-01-01 → 2026-09-30`, `n=4744`, TLS OK).
  2. `Dow` (Yahoo `data/confianza_sf/Dow.parquet`) ← **`vxd_close`** (`^VXD`, CBOE DJIA Volatility, `2006-01-03 → 2026-09-30`, ya local en `cboe_volatility_daily.parquet`).
  3. `Russell2000` (Yahoo `data/confianza_sf/Russell2000.parquet`) ← **`rvx_close`** (`^RVX`, CBOE Russell 2000 Volatility, `2006-01-03 → 2026-09-30`, ya local en `cboe_volatility_daily.parquet`).
  4. `GC` (futuro oro M1 NT8) ← **`gvz_close`** (`^GVZ`, CBOE Gold ETF Volatility, `2008-06-03 → 2026-09-30`, ya local en `cboe_volatility_daily.parquet`).
- **No disponibles sin fuente paga/externa en este entorno (K62 documentado):** `^V2TX` (EuroStoxx VSTOXX), `^VDAX` (DAX), `^VHSI` (Hang Seng) y `^JNIV` (Nikkei) devuelven `HTTP 404` en Yahoo Finance; `stoxx.com` / `stooq.com` fallan verificación TLS y `FRED` hace timeout. Quedan declarados como no medibles con fuentes gratuitas aquí sin inventar sustitutos.
- **Reglas probadas:**
  - `C2_VBB` (exacta de `carril2._senales2`: `iv_local > SMA20 + 2*STD20`, control `C2_VBBN: iv_local < SMA20 - 1*STD20`).
  - `C2_VZ` (versión univariable local donde no hay VIX9D local: `z6(iv_local) < -1`, control `z6(iv_local) > +1`).
  - `C2_EVRP` (versión local sin term-structure VIX9D/VIX donde no existe VIX9D del subyacente: `iv_local - rv10 > 0`, contraste contra `iv_local - rv10 <= 0`).
  - En todos los casos se compara explícitamente **`IV_LOCAL` vs `VIX_EEUU`** y **Regla vs Control `N`**.

## 2. Cómo podría refutarse
- Si al corregir a volatilidad implícita local (`^AXVI`, `^VXD`, `^RVX`, `^GVZ`), las reglas `C2_VBB`, `C2_VZ` y `C2_EVRP` siguen negativas o no superan a su control `N` ni mejoran frente a usar `^VIX`, queda refutado que la falla previa se debiera sólo al insumo exógeno.
