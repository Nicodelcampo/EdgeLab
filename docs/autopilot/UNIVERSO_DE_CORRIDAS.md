# Universo de corridas guiado por umbrales

Idea (pedida por Nico): no se corre «lo que parece interesante»; se corre donde un efecto **plausible** puede superar el **umbral de alguna cuenta de challenge**, cuota incluida, y se elige la cuenta que mejor le calza a la estrategia (o a la inversa).

## Cadena
1. **Catálogo de cuentas** (`config/propfirms/`, módulo `edgelab/propfirm/`) con reglas, cuota y si fueron verificadas.
2. **Umbrales** (`tools/propfirm_thresholds.py` → `docs/research/propfirm_thresholds/THRESHOLDS.md`): por cuenta, para una operación de desvío σ (USD con el tamaño) y costo/σ, el acierto mínimo p\* con EV ≥ 0 del ciclo completo (evaluación → fondeada → retiros, `edgelab/propfirm/ev.py`) y su traducción a **ρ\*** (correlación mínima de la señal con el retorno siguiente; ρ\* = (2p\*−1)/0,8). Se excluyen cuentas sin cuota (el EV de una cuenta gratis es trivialmente ≥ 0).
3. **Mapa de volatilidad** (`tools/universe_sigma.py`, corrido como benchmark sin alfa en Kaggle): σ del retorno de 15/30/60 min por instrumento y franja de 30 min (CT), sesiones 2025-07 → 2026-09.
4. **Universo** (`tools/universe_design.py` → `UNIVERSO.md`): para cada celda (instrumento × franja × horizonte) elige tamaño (minis ≤ 4 o micros ≤ 40) y cuenta que minimizan ρ\*.
5. **Generador** (`edgelab/autopilot/generate.py`, regla R9): propone un barrido por instrumento en sus mejores celdas, con `required_rho`; la puntuación se multiplica por la **factibilidad** `min(1, 0,12/ρ*)`.
6. **Camino inverso** (`tools/propfirm_match.py`): dada una estrategia (σ, z bruto) ordena las cuentas por EV y aporte.

## Supuestos que mandan (declarados, editables)
- Costos por contrato: comisión de ida y vuelta 4,80 USD + 1 tick de deslizamiento por lado (ES/NQ/YM conservan los valores más altos de `edgelab.propfirm`); GC 24,8; ZB 67,3; 6E/6J ≈ 17,3. Micros: MES/MNQ/MYM de `edgelab.propfirm`; MGC = 4,80 + 2 (conservador).
- 2 operaciones por día, señal simétrica; el desvío de la operación se toma igual al σ del retorno de la franja (salida por tiempo).
- ρ plausible ≈ 0,12: los efectos intradía reales de las muestras propias; los grandes (GC 14:30-15:00 en 2026Q1, +0,44) fueron episódicos.
- Todas las cuentas están `verified: false` (extraídas por scrapers y por el agente); las cuotas de Lucid son las de lista de la página principal.

## Hallazgo sobre las cuentas: el valor de opción
Con las reglas y cuotas cargadas (todas sin verificar), varias cuentas dan **EV ≥ 0 aun con ventaja bruta cero o negativa** (p. ej. Topstep con cuota 95; ρ\* ≈ −0,04 en `THRESHOLDS.md`): el riesgo está acotado a la cuota y los retiros dan una opción. Es lo que advierte Hall (2026): pasar o «ganar» con la cuenta no prueba habilidad. EdgeLab **no persigue ese valor de opción**: depende de cuotas y retiros no verificados, de descuentos, de la conducta en la cuenta fondeada y de las reglas contra el abuso. Por eso el umbral que se usa para diseñar es el **efectivo = máx(EV ≥ 0 del ciclo, esperanza neta ≥ 0)**, es decir, la estrategia debe tener ventaja neta positiva por sí misma, y el aporte sobre el control sin ventaja debe ser positivo.

## Límites
Es una cota necesaria, no suficiente: una celda con ρ\* bajo no tiene edge; una con ρ\* alto probablemente no sirva. No modela correlación entre estrategias ni consistencia por día más allá de lo que trae `ev.py`.
