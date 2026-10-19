# F0B — Compatibility Probe + Entorno Reproducible (EdgeLab core + NT8 Bridge)

> Branch `foundation/f0b-compatibility-probe` · Base `cde6d93` (`baseline-pre-foundation`, intocable).
> Probes en venvs aislados; **Python global nunca modificado**; sin datos reales.
> Matriz regenerada desde los JSON de la suite (no editada a mano).

## 1. Entorno base
- Python 3.12.10 64-bit; pip global 26.1.2 (no tocado); **uv ausente**.
- CPU Intel i5-1135G7 (4c/8t); Windows 11 10.0.26200.

## 2. Dependencias reales (import graph)
- **core:** numpy, pandas, numba(+llvmlite), pyarrow — motor + I/O.
- **research (fuera de alcance):** vectorbt (**9 scripts** `validation/*vectorbt*`, `diversification_strategies`, `macro_news_filter`), scipy (1), arch (`spa.py`, opcional).
- **bridge/dev (aún no importados):** pydantic, duckdb, polars, pytest, hypothesis, typer.

## 3. Identidad de vectorbt
Dist `vectorbt` **1.1.0** (site-packages, no editable, sin `vectorbtpro`). `Requires-Dist`: **numpy>=2.4.6, pandas<4;>=3.0.3, numba>=0.66** + plotly/ipywidgets/anywidget/sklearn (42 deps; extras `[full]` con ccxt/ray/TA-Lib, NO instalados). **Exige stack moderno; pesado; el core no lo importa → extra aislado.**
AST/getattr (sin ejecutar los 9 scripts): APIs usadas = `Portfolio.from_signals`, `MA.run`, `ATR.run`, `BBANDS.run`, `RSI.run` (+ clases) → **todas existen en 1.1.0**.

## 4. Candidatos y versiones resueltas
| | numpy | pandas | numba | pyarrow | pydantic | duckdb | polars | vectorbt |
|---|---|---|---|---|---|---|---|---|
| **L** legacy (pins requirements.txt) | 1.26.4 | 2.2.2 | 0.66.0 | 20.0.0 | 2.13.4 | 1.5.4 | 1.43.0 | **imposible** |
| **M** modern lean | 2.4.6 | 3.0.3 | 0.66.0 | 25.0.0 | 2.13.4 | 1.5.4 | 1.43.0 | (extra) |
| **G** global as-is | 2.4.6 | 3.0.3 | 0.66.0 | 22.0.0 | 2.12.5 | ausente | ausente | 1.1.0 |
| **ModernFull** (gate, todo junto) | 2.4.6 | 3.0.3 | 0.66.0 | 25.0.0 | 2.13.4 | 1.5.4 | 1.43.0 | 1.1.0 |

**Gate F0B.1A:** la resolución conjunta (`ModernFull`) fijó el núcleo **idéntico a M** → **SIN DRIFT** (el resolver bajó numpy 2.5.1→2.4.6 por el cap de numba). `pip check` limpio (los 81 paquetes con vectorbt coexisten).

## 5. Matriz de compatibilidad (A–I, regenerada desde JSON)
| Test | L (legacy) | M (modern) | G (global) | ModernFull |
|---|:--:|:--:|:--:|:--:|
| A imports | PASS | PASS | PASS | PASS |
| B numba int64/float64 | PASS | PASS | PASS | PASS |
| C ns round-trip | PASS | PASS | PASS | PASS |
| D schema NT8 | PASS | PASS | PASS | PASS |
| E barras [ini,fin) | PASS | PASS | PASS | PASS |
| F vectorbt runtime | SKIP | SKIP | PASS | PASS |
| G engine self-check | PASS | PASS | PASS | PASS |
| H pydantic | PASS | PASS | PASS | PASS |
| I duckdb/polars | PASS | PASS | ABSENT | PASS |
| **Resumen** | 8 PASS + 1 SKIP | 8 PASS + 1 SKIP | 8 PASS + 1 ABSENT | **9 PASS** |

Estados: PASS / FAIL / SKIP / ABSENT / NOT_APPLICABLE. SKIP y ABSENT no cuentan como PASS. Único warning: en G/ModernFull, 1–2 `DeprecationWarning` cosméticos de deps transitivas de vectorbt (websockets). El engine self-check no escribe artefactos en ningún entorno.

## 6. Locks + verificación desde cero
| Lock | pkgs | SHA-256 |
|---|---|---|
| `requirements/core-bridge-dev.lock` | 30 | `0cb96d72…efaf1f` |
| `requirements/full-research.lock` | 81 | `6e175988…a3ef2` |
- Consistencia base⊂full: núcleo idéntico; test automático en `tests/foundation/test_environment_contract.py`.
- **verify_base** (solo lock base, `--require-hashes`): suite 8 PASS + 1 SKIP(vectorbt ABSENT); `sys.prefix` en el venv; vectorbt/scipy/arch ABSENT → **cero filtración del global**.
- **verify_full** (solo lock full, `--require-hashes`): suite **9 PASS** incl. F; vectorbt 1.1.0 dentro del venv; `pip check` limpio.

## 7. Conclusión / recomendación — Resultado 1: stack único MODERNO
Core y Bridge funcionan idénticos en L y M; **vectorbt es la única restricción dura** y exige moderno. Legacy es obsoleto. → **`.venv` = lock base (core+bridge+cli+dev)** como entorno de trabajo; **vectorbt vía `full-research.lock`** materializado on-demand (no `.venv-vectorbt` persistente). Sin entorno legacy separado.

## 8. Integridad
- Python global sin cambios (numpy 2.4.6/pandas 3.0.3; duckdb/polars siguen ausentes en global).
- Sin datos reales (fixtures sintéticos en `_env_probes/_tmp/`). Sin EURUSD/ARB/tickfade. Sin corregir rutas (F0C).
- Baseline `cde6d93` + tag intactos.
