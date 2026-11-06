# Mejoras del embudo por impacto — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar las 17 mejoras identificadas en la investigación del 2026-10-04 sobre el embudo existente de EdgeLab, en orden de impacto, dejando cada una cubierta por un test sintético que falla si la mejora se rompe.

**Architecture:** Se modifica el embudo de `main` (`edgelab/funnel`, `edgelab/audit.py`, `validation/`) sin reescribirlo. Cada mejora es un módulo chico o un cambio localizado con su test. Las mejoras que cambian la semántica de validación (DSR diario, N de por vida, compuerta SPA, MCPT con reoptimización, canarios) quedan citadas en la enmienda al NORTH_STAR que se escribe en la Tarea 1, porque el referente exige que todo cambio de semántica esté versionado antes de correr la campaña afectada.

**Tech Stack:** Python 3.12 (venv `.venv`), numpy, numba, pyarrow, pandas, scipy, arch, pytest. Sin dependencias nuevas salvo `arch` (ya listada en `requirements-funnel.txt`).

**Spec:** `docs/research/AGENTE_ESPIRAL_20261004.md` (secciones 2.3, 2.4, 4.3, 5, 8.1, 9) y los dossiers `docs/research/agente_espiral/DOSSIER_B_validacion_estadistica.md` y `DOSSIER_D_futuros_intradia.md`. El resumen de las 17 mejoras está en la conversación del 2026-10-04 y se reproduce en la tabla de abajo.

## Mapa mejora → tarea

| # | Mejora | Tarea |
|---|---|---|
| 14 | Unificar ramas, enmienda, hash de AGENTS.md | 1 |
| 3 | PBO S=16 | 2 |
| 5 | SPA con bloque óptimo PPW | 3 |
| 1 | DSR sobre P&L diario, no por trade | 4 |
| 2 | N de multiplicidad acumulado de por vida | 5 |
| 6 | Compuerta SPA + t mínimo en EF2 | 6 |
| 4 | MCPT que reoptimiza el grid | 7 |
| 7 | Oráculo de costos y sensibilidad ×1/×1,5/×2 | 8 |
| 8 | Controles canario: oráculo con fuga, nulo, benchmark | 9 |
| 10 | Tests de delay (K8) y pesimista/optimista (K9) | 10 |
| 9 | Testing diferencial de motor | 11 |
| 12 | Familia intraday momentum última media hora | 12 |
| 11, 13, 16 | Priors de familias (refutadas/folklore/requiere L2) y archivo de scripts vectorbt | 13 |
| 15 | Kaggle batch con `dataset_sources` | 14 |
| 17 | Alpha-wealth con e-LOND para aperturas de holdout | 15 |

## Global Constraints

- Holdout sellado `2026-07-01 → 2026-12-31`; `trade_date >= 20260401` cerrado para MGC. Ningún test ni tarea lee datos reales: todo es sintético.
- `asserts_edge: false` en toda propuesta; un resultado LLM nunca es evidencia.
- Ledger append-only con cadena SHA-256 (`edgelab.edge_brain.registry.append_record`); nunca reescribir filas.
- Commits en formato convencional, sin líneas de atribución a IA. Nunca `git push` dentro de este plan.
- Nunca correr `build` ni instalar nada fuera del venv `.venv`.
- No modificar `databuild/`, parquets ni manifiestos históricos.
- Toda constante de costo o umbral lleva comentario con la fuente (dossier y sección).

## Review Focus

1. **P&L con días sin trades.** La agregación diaria debe producir ceros explícitos en días de sesión sin operaciones, no omitirlos; si los omite, el Sharpe diario se infla. Test en Tarea 4.
2. **Campaña sin familia declarada.** Un registro de candidatos sin `family_id` debe caer en `UNDECLARED_FAMILY` y la compuerta SPA debe tratarla como familia propia, no saltearla. Test en Tarea 6.
3. **`arch` ausente.** El runner debe seguir funcionando y marcar `spa: NOT_RUN_ARCH_MISSING` en vez de lanzar. Test en Tarea 6.
4. **Canario que coincide por azar con una señal real.** El oráculo con fuga se identifica por `family_id` reservado, nunca por su rendimiento. Test en Tarea 9.
5. **Alpha-wealth con e-valor exactamente en el umbral.** La regla es `e >= 1/alpha_t`; igualdad rechaza (abre). Test en Tarea 15.

---

### Task 0: Entorno reproducible (Python 3.12 + deps + suite verde)

**Files:**
- Create: `.venv/` (no versionado; ya está en `.gitignore` como `.venv/`? verificar; si no, agregar línea)
- Modify: `requirements-funnel.txt` (agregar `pytest`)

**Interfaces:**
- Produces: comando `.venv\Scripts\python -m pytest tests -q` verde, usado por todas las tareas.

- [ ] **Step 1: Crear venv con Python 3.12 y instalar dependencias**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -U pip
.venv\Scripts\python -m pip install -r requirements-funnel.txt pytest
```

- [ ] **Step 2: Verificar que `.venv/` está ignorado**

Run: `git check-ignore .venv`
Expected: imprime `.venv`. Si no imprime nada, agregar la línea `.venv/` al final de `.gitignore`.

- [ ] **Step 3: Correr la suite existente**

Run: `.venv\Scripts\python -m pytest tests -q`
Expected: todos PASS (hoy: `test_funnel.py` 4 tests, `test_funnel_signals.py` 3 tests, `test_bridge_imports.py`).

- [ ] **Step 4: Commit**

```bash
git add requirements-funnel.txt .gitignore
git commit -m "chore(env): pytest en requirements-funnel y venv ignorado"
```

---

### Task 1: Unificar referente en `main` y enmienda (mejora 14)

**Files:**
- Create (copiados desde `origin/claude/focused-fermat-qjt805`): `docs/NORTH_STAR.md`, `docs/edge_validation_contract.md`, `docs/kernel_contract.md`, `tests/test_north_star_hash.py`, `CLAUDE.md`, `AGENTS.md`
- Modify: `docs/NORTH_STAR.md` (enmienda A-2026-10-05 + autocita), `AGENTS.md` (hash)

**Interfaces:**
- Produces: `docs/NORTH_STAR.md` con sección `## Enmienda A-2026-10-05` y hash refrescado; `tests/test_north_star_hash.py` verde.

- [ ] **Step 1: Traer los archivos desde la rama de gobernanza**

```bash
git checkout origin/claude/focused-fermat-qjt805 -- docs/NORTH_STAR.md docs/edge_validation_contract.md docs/kernel_contract.md tests/test_north_star_hash.py CLAUDE.md AGENTS.md
```

- [ ] **Step 2: Correr el test de hash para confirmar el estado base**

Run: `.venv\Scripts\python -m pytest tests/test_north_star_hash.py -q`
Expected: PASS (la autocita `ed4293b5…` coincide con el cuerpo traído).

- [ ] **Step 3: Agregar la enmienda al cuerpo de NORTH_STAR, antes del marcador**

Insertar inmediatamente antes de la línea `<!-- SHA256-BODY-ABOVE -->`:

```markdown
## Enmienda A-2026-10-05 — Delegación al agente de investigación y semántica de validación

Las decisiones de promoción en G0–G4, incluida la apertura única del holdout,
se delegan al agente descrito en `docs/research/AGENTE_ESPIRAL_20261004.md`,
bajo condiciones no negociables: (a) el perímetro de su §3.5 está en código y
cubierto por tests; (b) ninguna salida de LLM es evidencia; (c) el número de
pruebas se cuenta acumulado de por vida y el presupuesto de α para aperturas
de holdout es finito y preregistrado (e-LOND); (d) los cambios a
`edge_validation_contract.md` siguen requiriendo decisión explícita del
responsable. Esta enmienda no mueve ninguna frontera de holdout.

Cambios de semántica de validación aprobados por esta enmienda, implementados
en `docs/superpowers/plans/2026-10-05-mejoras-embudo-por-impacto.md`:
DSR sobre P&L diario; N de multiplicidad acumulado de por vida; compuerta SPA
por familia y t mínimo en EF2; MCPT con reoptimización del grid; controles
canario obligatorios (oráculo con fuga, nulo aleatorio, benchmark pasivo);
PBO con S=16; costos desde oráculo verificado con sensibilidad ×1/×1,5/×2.
```

- [ ] **Step 4: Correr el test de hash para verificar que ahora FALLA**

Run: `.venv\Scripts\python -m pytest tests/test_north_star_hash.py -q`
Expected: FAIL en `test_la_autocita_del_pie_coincide_con_el_cuerpo_actual` con el hash nuevo impreso en el mensaje.

- [ ] **Step 5: Refrescar la autocita con el hash nuevo**

```powershell
.venv\Scripts\python -c "import hashlib,re,pathlib;p=pathlib.Path('docs/NORTH_STAR.md');raw=p.read_bytes();body=raw.split(b'<!-- SHA256-BODY-ABOVE -->',1)[0].replace(b'\r\n',b'\n');h=hashlib.sha256(body).hexdigest();t=raw.decode('utf-8');t=re.sub(r'(\*\*sha256 \(cuerpo hasta el marcador\):\*\* `)[0-9a-f]{64}(`)',r'\g<1>'+h+r'\g<2>',t);p.write_bytes(t.encode('utf-8'));print(h)"
```

Copiar el hash impreso. Reemplazar en `CLAUDE.md` y `AGENTS.md` el hash viejo (`ed4293b5…` en CLAUDE.md; `d85364e2…` en AGENTS.md) por el nuevo.

- [ ] **Step 6: Correr el test de hash para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_north_star_hash.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add docs/NORTH_STAR.md docs/edge_validation_contract.md docs/kernel_contract.md tests/test_north_star_hash.py CLAUDE.md AGENTS.md
git commit -m "gov: NORTH_STAR y contratos en main; enmienda A-2026-10-05 con hash refrescado"
```

---

### Task 2: PBO con S=16 (mejora 3)

**Files:**
- Modify: `validation/pbo.py:23` (default `S=16`), `edgelab/funnel/runner.py:38` (`S=16`)
- Test: `tests/test_pbo.py`

**Interfaces:**
- Produces: `pbo_cscv(R, S=16) -> {"pbo", "n_splits", "lambdas"}`; `n_splits == 12870` con S=16.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_pbo.py
import numpy as np
from validation.pbo import pbo_cscv

def test_cscv_default_s16_has_12870_splits():
    rng = np.random.default_rng(1)
    R = rng.normal(size=(16 * 4, 3))          # T >= S*4 exigido por la función
    out = pbo_cscv(R)
    assert out["n_splits"] == 12870            # C(16,8); el paper dice 12.780 por errata (Dossier B §2)

def test_cscv_detects_overfit_selection():
    rng = np.random.default_rng(2)
    T, N = 640, 50
    R = rng.normal(size=(T, N))                # puro ruido: el mejor IS no debería ganar OOS
    out = pbo_cscv(R, S=16)
    assert out["pbo"] > 0.3
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_pbo.py -q`
Expected: FAIL en el primer test (`n_splits == 252`).

- [ ] **Step 3: Cambiar el default y el llamado del runner**

En `validation/pbo.py` línea 23: `def pbo_cscv(R, S=16):` y en el docstring `S par (default 16 -> 12870 splits, Bailey et al. 2017)`.
En `edgelab/funnel/runner.py` línea 38: `pbo=pbo_cscv(daily,S=16)`.

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_pbo.py tests/test_funnel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add validation/pbo.py edgelab/funnel/runner.py tests/test_pbo.py
git commit -m "fix(validation): PBO/CSCV con S=16 por defecto (12870 combinaciones)"
```

---

### Task 3: SPA con longitud de bloque óptima (mejora 5)

**Files:**
- Modify: `validation/spa.py`
- Test: `tests/test_spa.py`

**Interfaces:**
- Produces: `spa_pvalue(benchmark_losses, models_losses, reps=1000, seed=7, block_size=None) -> float`; con `block_size=None` usa `arch.bootstrap.optimal_block_length` (media de `b_sb` sobre columnas). `optimal_block(models_losses) -> float`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_spa.py
import numpy as np
import pytest
arch = pytest.importorskip("arch")
from validation.spa import spa_pvalue, optimal_block

def _ar1(T, K, phi, rng):
    x = np.zeros((T, K))
    for t in range(1, T):
        x[t] = phi * x[t - 1] + rng.normal(size=K)
    return x

def test_optimal_block_grows_with_autocorrelation():
    rng = np.random.default_rng(3)
    weak = optimal_block(_ar1(2000, 4, 0.1, rng))
    strong = optimal_block(_ar1(2000, 4, 0.9, rng))
    assert strong > weak * 2

def test_spa_pvalue_in_unit_interval_and_noise_not_rejected():
    rng = np.random.default_rng(4)
    losses = rng.normal(size=(600, 20))         # 20 modelos de ruido contra benchmark cero
    p = spa_pvalue(np.zeros(600), losses, reps=300)
    assert 0.0 <= p <= 1.0 and p > 0.05
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_spa.py -q`
Expected: FAIL con `ImportError: cannot import name 'optimal_block'`.

- [ ] **Step 3: Implementar**

Reemplazar el contenido de `validation/spa.py` por:

```python
"""SPA de Hansen (2005) sobre `arch`, con bloque óptimo de Patton-Politis-White (2009).

Dossier B §3 y §5: `arch` usa √T por defecto; el bloque óptimo evita sub/sobre-estimar
la dependencia temporal de las pérdidas diarias.
"""
import numpy as np

try:
    from arch.bootstrap import SPA, optimal_block_length
    HAS_ARCH = True
except ImportError:  # pragma: no cover
    HAS_ARCH = False


def optimal_block(models_losses):
    """Media de la longitud óptima del stationary bootstrap (`b_sb`) sobre las columnas."""
    x = np.asarray(models_losses, dtype=np.float64)
    bl = optimal_block_length(x)
    return float(np.nanmean(bl["stationary"]))


def spa_pvalue(benchmark_losses, models_losses, reps=1000, seed=7, block_size=None):
    """p-value consistente de SPA: H0 = ningún modelo supera al benchmark.
    Pérdidas: menor es mejor. NaN si arch no está instalada."""
    if not HAS_ARCH:
        return np.nan
    m = np.asarray(models_losses, dtype=np.float64)
    b = np.asarray(benchmark_losses, dtype=np.float64)
    if block_size is None:
        block_size = max(1.0, optimal_block(m))
    spa = SPA(b, m, block_size=block_size, reps=reps, seed=seed, bootstrap="stationary")
    spa.compute()
    return float(spa.pvalues["consistent"])
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_spa.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add validation/spa.py tests/test_spa.py
git commit -m "fix(validation): SPA con longitud de bloque óptima PPW en vez de sqrt(T)"
```

---

### Task 4: DSR sobre P&L diario (mejora 1)

**Files:**
- Create: `edgelab/stats/__init__.py` (vacío), `edgelab/stats/daily.py`
- Modify: `edgelab/audit.py` (docstring: aclarar que `deflated_sharpe` espera momentos por período homogéneo)
- Test: `tests/test_dsr_daily.py`

**Interfaces:**
- Produces: `daily_pnl(trade_pnl, trade_dates, session_dates) -> np.ndarray` (una entrada por sesión, cero donde no hubo trades); `daily_moments(x) -> dict(n, sharpe, skew, kurt)`; `dsr_daily(trade_pnl, trade_dates, session_dates, sr0_daily) -> float`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_dsr_daily.py
import math
import numpy as np
from edgelab.audit import deflated_sharpe, sr0_haircut, PHI_INV, EULER_GAMMA
from edgelab.stats.daily import daily_pnl, daily_moments, dsr_daily

def test_dsr_reproduces_bailey_lopez_de_prado_2014_example():
    # Dossier B §1: N=100, V[SR] anual=1/2, T=1250, skew=-3, kurt=10, SR anual=2.5 -> DSR≈0.90
    N, T = 100, 1250
    sr0_annual = math.sqrt(0.5) * ((1 - EULER_GAMMA) * PHI_INV(1 - 1 / N) + EULER_GAMMA * PHI_INV(1 - 1 / (N * math.e)))
    assert abs(sr0_annual - 1.79) < 0.02
    sr_daily, sr0_daily = 2.5 / math.sqrt(250), sr0_annual / math.sqrt(250)
    dsr = deflated_sharpe(sr_daily, T, -3.0, 10.0, sr0_daily)
    assert abs(dsr - 0.90) < 0.01

def test_daily_pnl_keeps_zero_days():
    pnl = np.array([10.0, -4.0, 6.0])
    td = np.array([20260101, 20260101, 20260103])
    sessions = np.array([20260101, 20260102, 20260103])
    d = daily_pnl(pnl, td, sessions)
    assert d.tolist() == [6.0, 0.0, 6.0]

def test_per_trade_and_daily_sharpe_differ():
    rng = np.random.default_rng(5)
    sessions = np.arange(20260101, 20260101 + 400)
    td = rng.choice(sessions, size=3000)            # ~7,5 trades por día, distribución desigual
    pnl = rng.normal(0.2, 1.0, size=3000)
    per_trade = pnl.mean() / pnl.std()
    daily = daily_moments(daily_pnl(pnl, td, sessions))["sharpe"]
    assert not math.isclose(per_trade, daily, rel_tol=0.05)
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_dsr_daily.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.stats`.

- [ ] **Step 3: Implementar**

```python
# edgelab/stats/daily.py
"""Agregación a P&L diario para PSR/DSR.

Dossier B §1: el PSR/DSR asume retornos a frecuencia homogénea. Calcularlo por trade
(duración variable, n = trades) descalibra el denominador. Se agrega por sesión y los
días de sesión sin trades valen cero explícito.
"""
import numpy as np
from edgelab.audit import deflated_sharpe


def daily_pnl(trade_pnl, trade_dates, session_dates):
    s = np.asarray(session_dates)
    out = np.zeros(len(s), dtype=np.float64)
    pos = {int(d): i for i, d in enumerate(s)}
    for p, d in zip(np.asarray(trade_pnl, dtype=np.float64), np.asarray(trade_dates)):
        out[pos[int(d)]] += p
    return out


def daily_moments(x):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < 2 or x.std() <= 0:
        return {"n": n, "sharpe": np.nan, "skew": np.nan, "kurt": np.nan}
    mu, sd = x.mean(), x.std()
    z = (x - mu) / sd
    return {"n": n, "sharpe": float(mu / sd), "skew": float((z ** 3).mean()), "kurt": float((z ** 4).mean())}  # curtosis cruda, no excedente


def dsr_daily(trade_pnl, trade_dates, session_dates, sr0_daily):
    m = daily_moments(daily_pnl(trade_pnl, trade_dates, session_dates))
    return deflated_sharpe(m["sharpe"], m["n"], m["skew"], m["kurt"], sr0_daily)
```

Crear `edgelab/stats/__init__.py` vacío. En `edgelab/audit.py`, cambiar la línea del docstring `deflated_sharpe : PSR(sr | sr0) de Bailey & Lopez de Prado (sr POR TRADE).` por `deflated_sharpe : PSR(sr | sr0) de Bailey & Lopez de Prado. Momentos por PERÍODO HOMOGÉNEO (diario); ver edgelab/stats/daily.py. Por trade sólo como diagnóstico.`

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_dsr_daily.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add edgelab/stats/__init__.py edgelab/stats/daily.py edgelab/audit.py tests/test_dsr_daily.py
git commit -m "feat(stats): DSR sobre P&L diario con días cero explícitos; reproduce el ejemplo de Bailey-López de Prado 2014"
```

---

### Task 5: Ledger de pruebas de por vida y N de multiplicidad acumulado (mejora 2)

**Files:**
- Create: `edgelab/funnel/trials.py`
- Modify: `edgelab/funnel/runner.py` (registrar cada celda; `sr0` desde N de por vida)
- Test: `tests/test_trials.py`

**Interfaces:**
- Produces: `TrialStore(path)` con `record(campaign_id, family_id, candidate_id, split_hash, sharpe_daily)`, `n_lifetime() -> int`, `sr_dispersion_lifetime() -> float`, `n_effective(corr_mean) -> float`. SQLite, tabla `trials`, inserción única por `(campaign_id, candidate_id)`.
- `FunnelRunner.__init__` acepta `trials_path` (default `out_dir.parent / "trials.sqlite"`) y `campaign_id` (default `split_hash[:16]`); `run_e1_e3` escribe cada celda y agrega `multiplicity.n_lifetime` y `multiplicity.sr0_lifetime` al payload.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_trials.py
import numpy as np
from edgelab.funnel.trials import TrialStore

def test_trials_accumulate_across_campaigns(tmp_path):
    s = TrialStore(tmp_path / "trials.sqlite")
    for i in range(5):
        s.record("camp_A", "FAM1", f"c{i}", "h1", sharpe_daily=0.01 * i)
    for i in range(3):
        s.record("camp_B", "FAM1", f"c{i}", "h2", sharpe_daily=-0.01 * i)
    assert s.n_lifetime() == 8
    assert s.sr_dispersion_lifetime() > 0

def test_duplicate_trial_is_idempotent(tmp_path):
    s = TrialStore(tmp_path / "t.sqlite")
    s.record("c", "F", "x", "h", sharpe_daily=0.1)
    s.record("c", "F", "x", "h", sharpe_daily=0.1)
    assert s.n_lifetime() == 1

def test_n_effective_interpolates_by_mean_correlation(tmp_path):
    s = TrialStore(tmp_path / "t.sqlite")
    for i in range(100):
        s.record("c", "F", f"x{i}", "h", sharpe_daily=float(i) / 100)
    assert s.n_effective(corr_mean=1.0) == 1.0          # todas idénticas -> 1 prueba
    assert s.n_effective(corr_mean=0.0) == 100.0        # independientes -> M
    assert 1.0 < s.n_effective(corr_mean=0.5) < 100.0
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_trials.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.funnel.trials`.

- [ ] **Step 3: Implementar**

```python
# edgelab/funnel/trials.py
"""Ledger de pruebas de por vida (Dossier B §1, §9 Etapa 0).

El False Strategy Theorem exige contar TODAS las pruebas desde que existe el proyecto,
no por campaña. N_eff por la interpolación de Bailey & López de Prado (2014, Apéndice A.3):
N_eff = rho + (1 - rho) * M.
# ponytail: N_eff por correlación media; ONC (López de Prado & Lewis 2019) cuando M sea grande.
"""
import sqlite3
from pathlib import Path
import numpy as np

_DDL = """CREATE TABLE IF NOT EXISTS trials(
  campaign_id TEXT NOT NULL, family_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
  split_hash TEXT NOT NULL, sharpe_daily REAL, recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (campaign_id, candidate_id))"""


class TrialStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute(_DDL)

    def record(self, campaign_id, family_id, candidate_id, split_hash, sharpe_daily):
        sd = None if sharpe_daily is None or not np.isfinite(sharpe_daily) else float(sharpe_daily)
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT OR IGNORE INTO trials(campaign_id,family_id,candidate_id,split_hash,sharpe_daily) VALUES (?,?,?,?,?)",
                      (campaign_id, family_id, candidate_id, split_hash, sd))

    def n_lifetime(self):
        with sqlite3.connect(self.path) as c:
            return int(c.execute("SELECT COUNT(*) FROM trials").fetchone()[0])

    def sr_dispersion_lifetime(self):
        with sqlite3.connect(self.path) as c:
            rows = [r[0] for r in c.execute("SELECT sharpe_daily FROM trials WHERE sharpe_daily IS NOT NULL")]
        return float(np.std(rows)) if len(rows) > 1 else 0.0

    def n_effective(self, corr_mean):
        m = self.n_lifetime()
        rho = float(np.clip(corr_mean, 0.0, 1.0))
        return float(rho + (1.0 - rho) * m)
```

En `edgelab/funnel/runner.py`:

1. Agregar al import: `from .trials import TrialStore` y `from edgelab.audit import sr0_haircut`.
2. En `__init__`, al final: `self.campaign_id=campaign_id or self.split.split_hash[:16];self.trials=TrialStore(trials_path or self.out.parent/'trials.sqlite')`. Agregar `campaign_id=None,trials_path=None` a la firma.
3. En `run_e1_e3`, dentro del bucle `for local,c in enumerate(self.cfg[start:end]):`, después de calcular `a` y `b`, agregar:

```python
                pooled=np.r_[a,b];sr_cell=float(pooled.mean()/pooled.std()) if len(pooled)>1 and pooled.std()>0 else None
                self.trials.record(self.campaign_id,c['family_id'],c['candidate_id'],self.split.split_hash,sr_cell)
```

4. Antes de `payload={...}`, agregar:

```python
        n_life=self.trials.n_lifetime();sr0_life=sr0_haircut(self.trials.sr_dispersion_lifetime(),n_life)
        multiplicity.update({'n_lifetime':n_life,'sr0_lifetime':float(sr0_life),'n_campaign':len(rows)})
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_trials.py tests/test_funnel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add edgelab/funnel/trials.py edgelab/funnel/runner.py tests/test_trials.py
git commit -m "feat(funnel): ledger SQLite de pruebas de por vida y sr0 con N acumulado"
```

---

### Task 6: Compuerta SPA por familia y t mínimo en EF2 (mejora 6)

**Files:**
- Modify: `edgelab/funnel/runner.py`
- Test: `tests/test_runner_gate.py`

**Interfaces:**
- Produces: `run_e1_e3(min_trades=30, min_t=2.0, spa_alpha=0.10)`; cada fila agrega `t_d1`; payload agrega `family_gates: {family_id: {"spa_p": float|None, "status": "PASS"|"KILLED"|"NOT_RUN_ARCH_MISSING"}}`; una celda sólo sobrevive si su familia pasó SPA y `t_d1 >= min_t`.
- Helper interno `_daily_matrix(self, cols)` reutilizado por PBO.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_runner_gate.py
import numpy as np
import pytest
from edgelab.funnel.runner import FunnelRunner

def _arrays(seed, n_days=200, bars_per_day=40, edge_ticks=0):
    rng = np.random.default_rng(seed)
    n = n_days * bars_per_day
    td = np.repeat(np.arange(20250101, 20250101 + n_days), bars_per_day).astype(np.int32)
    steps = rng.integers(-3, 4, n).astype(np.int32)
    close = 10000 + np.cumsum(steps)
    high = close + rng.integers(0, 3, n); low = close - rng.integers(0, 3, n)
    bo, ao = close - 1, close + 1
    sig = np.arange(5, n - 50, 17); dirs = np.ones(len(sig), np.int8)
    if edge_ticks:                                   # edge plantado: empujar el precio a favor tras la señal
        for s in sig:
            high[s + 1:s + 6] += edge_ticks; close[s + 1:s + 6] += edge_ticks
    return td, sig, dirs, high.astype(np.int32), low.astype(np.int32), bo.astype(np.int32), ao.astype(np.int32)

def _cfg(fam):
    return [{"candidate_id": f"{fam}-{sl}-{tp}", "family_id": fam, "direction": "normal", "sl_ticks": sl, "tp_ticks": tp}
            for sl in (10, 20) for tp in (10, 20, 30)]

def test_noise_family_is_killed_and_edge_family_passes(tmp_path):
    pytest.importorskip("arch")
    td, sig, dirs, h, l, bo, ao = _arrays(7, edge_ticks=0)
    r = FunnelRunner(trade_dates=td, signal_idx=sig, signal_dir=dirs, high=h, low=l, bid_open=bo, ask_open=ao,
                     configs=_cfg("NOISE"), out_dir=tmp_path / "a", backend="cpu")
    out = r.run_e1_e3(min_trades=10)
    assert out["family_gates"]["NOISE"]["status"] == "KILLED" and out["survivors"] == 0
    td, sig, dirs, h, l, bo, ao = _arrays(7, edge_ticks=8)
    r = FunnelRunner(trade_dates=td, signal_idx=sig, signal_dir=dirs, high=h, low=l, bid_open=bo, ask_open=ao,
                     configs=_cfg("EDGE"), out_dir=tmp_path / "b", backend="cpu")
    out = r.run_e1_e3(min_trades=10)
    assert out["family_gates"]["EDGE"]["status"] == "PASS" and out["survivors"] > 0

def test_undeclared_family_is_its_own_gate(tmp_path):
    td, sig, dirs, h, l, bo, ao = _arrays(8)
    cfg = [{"candidate_id": "x", "family_id": "UNDECLARED_FAMILY", "direction": "normal", "sl_ticks": 10, "tp_ticks": 10}]
    r = FunnelRunner(trade_dates=td, signal_idx=sig, signal_dir=dirs, high=h, low=l, bid_open=bo, ask_open=ao,
                     configs=cfg, out_dir=tmp_path, backend="cpu")
    out = r.run_e1_e3(min_trades=10)
    assert "UNDECLARED_FAMILY" in out["family_gates"]

def test_runner_survives_without_arch(tmp_path, monkeypatch):
    import validation.spa as spa
    monkeypatch.setattr(spa, "HAS_ARCH", False)
    td, sig, dirs, h, l, bo, ao = _arrays(9)
    r = FunnelRunner(trade_dates=td, signal_idx=sig, signal_dir=dirs, high=h, low=l, bid_open=bo, ask_open=ao,
                     configs=_cfg("F"), out_dir=tmp_path, backend="cpu")
    out = r.run_e1_e3(min_trades=10)
    assert out["family_gates"]["F"]["status"] == "NOT_RUN_ARCH_MISSING"
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_runner_gate.py -q`
Expected: FAIL con `KeyError: 'family_gates'`.

- [ ] **Step 3: Implementar en `runner.py`**

Agregar import: `from validation.spa import spa_pvalue, HAS_ARCH`.

Agregar método a `FunnelRunner`:

```python
    def _daily_matrix(self,keep,sl,tp,mult,sigdays):
        days=np.unique(sigdays[np.isin(sigdays,np.r_[self.split.d0_dates,self.split.d1_dates])])
        daily=np.zeros((len(days),len(keep)),np.float64);day_pos={int(d):i for i,d in enumerate(days)}
        for start,end,matrix,_ in iter_screen_batches(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl[keep],tp[keep],mult[keep],backend=self.backend):
            for local in range(end-start):
                for day,val in zip(sigdays,matrix[:,local]):
                    if int(day) in day_pos and np.isfinite(val):daily[day_pos[int(day)],start+local]+=val
        return daily
```

Cambiar la firma a `def run_e1_e3(self,min_trades=30,min_t=2.0,spa_alpha=0.10):` y la línea del cálculo de `survive` por:

```python
                t1=float(b.mean()/b.std()*np.sqrt(len(b))) if len(b)>1 and b.std()>0 else 0.0
                survive=len(a)>=min_trades and a.mean()>0 and len(b)>=min_trades and b.mean()>0 and t1>=min_t   # K2 (Dossier D): t neto OOS >= 2
                rows.append({**c,'d0_n':len(a),'d0_mean':float(a.mean()) if len(a) else None,'d1_n':len(b),'d1_mean':float(b.mean()) if len(b) else None,'t_d1':t1,'survives_e1_e2':bool(survive)})
```

(reemplaza la línea `rows.append(...)` original). Después de ese bucle y antes de `surv=[...]`, agregar la compuerta por familia:

```python
        gates={}
        for fam in sorted({r['family_id'] for r in rows}):
            keep=[i for i,c in enumerate(self.cfg) if c['family_id']==fam]
            if not HAS_ARCH:gates[fam]={'spa_p':None,'status':'NOT_RUN_ARCH_MISSING'};continue
            daily=self._daily_matrix(keep,sl,tp,mult,sigdays)
            if daily.shape[0]<30:gates[fam]={'spa_p':None,'status':'NOT_RUN_TOO_FEW_DAYS'};continue
            p=spa_pvalue(np.zeros(daily.shape[0]),-daily,reps=500)   # pérdidas = -P&L; benchmark cero
            gates[fam]={'spa_p':float(p),'status':'PASS' if p<=spa_alpha else 'KILLED'}
        for r in rows:
            if gates[r['family_id']]['status']=='KILLED':r['survives_e1_e2']=False
```

Reemplazar en el bloque de multiplicidad las líneas que construyen `days/daily/day_pos` y el bucle, por `daily=self._daily_matrix(keep,sl,tp,mult,sigdays)`. Agregar `'family_gates':gates` al `payload`.

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_runner_gate.py tests/test_funnel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add edgelab/funnel/runner.py tests/test_runner_gate.py
git commit -m "feat(funnel): compuerta SPA por familia y t>=2 en D1 antes de contar sobrevivientes"
```

---

### Task 7: MCPT que reoptimiza el grid (mejora 4)

**Files:**
- Create: `edgelab/stats/mcpt.py`
- Modify: `tools/mcpt_mgc_ema.py` (usar `grid` y `max` en `stat`)
- Test: `tests/test_mcpt.py`

**Interfaces:**
- Produces: `mcpt_pvalue(real_max, null_max) -> float` ((1 + #null ≥ real) / (B + 1)); `select_best(stats_per_config) -> (idx, value)`; en el tool, `stat(...)` devuelve el **máximo** sobre las 42 celdas y se registra `selection: "max_over_grid"`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_mcpt.py
import numpy as np
from edgelab.stats.mcpt import mcpt_pvalue, select_best

def test_pvalue_counts_ties_conservatively():
    assert mcpt_pvalue(5.0, np.array([1.0, 5.0, 9.0])) == (1 + 2) / 4

def test_selection_bias_is_captured_by_max():
    rng = np.random.default_rng(11)
    B, K = 2000, 42
    null_single = rng.normal(size=B)                    # estadístico de UNA celda fija bajo H0
    null_max = rng.normal(size=(B, K)).max(axis=1)      # máximo sobre el grid bajo H0
    real = 2.0
    assert mcpt_pvalue(real, null_single) < 0.05        # la celda fija "parece" significativa
    assert mcpt_pvalue(real, null_max) > 0.20           # el máximo sobre 42 celdas no lo es

def test_select_best_returns_argmax():
    assert select_best(np.array([1.0, 7.0, 3.0])) == (1, 7.0)
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_mcpt.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.stats.mcpt`.

- [ ] **Step 3: Implementar**

```python
# edgelab/stats/mcpt.py
"""MCPT con reoptimización (Masters 2020; Dossier B §5).

Para capturar el sesgo de selección, en cada permutación se recorre TODO el grid y se
toma el máximo; el real se compara contra la distribución de máximos.
"""
import numpy as np


def select_best(stats_per_config):
    s = np.asarray(stats_per_config, dtype=np.float64)
    i = int(np.argmax(s))
    return i, float(s[i])


def mcpt_pvalue(real_max, null_max):
    nm = np.asarray(null_max, dtype=np.float64)
    return float((1 + np.sum(nm >= real_max)) / (len(nm) + 1))
```

En `tools/mcpt_mgc_ema.py`: importar `grid` desde `tools.run_mgc_ema_screen` y `from edgelab.stats.mcpt import mcpt_pvalue, select_best`; definir los arrays del grid preregistrado de 42 celdas (`SLS=np.array([100,150,200]*14)`, `TPS`, `MULTS` según `screen_42_core.json` del artefacto; leerlos del JSON con `json.load(open(ROOT/'screen_42_core.json'))['grid']` si existe esa clave, y si no, construirlos como producto {normal, inversa} × SL {100,150,200} × TP {150,…,450}); reemplazar `stat` por:

```python
def stat(c,h,l,bo,ao,bc,ac,cid,td):
 e2=ema(c,cid,200);e5=ema(c,cid,500);e20=ema(c,cid,2000);si,sd=signals(e2,e5,e20,cid)
 nets=grid(si,sd,h,l,bo,ao,bc,ac,cid,td,SLS,TPS,MULTS,.5)   # devuelve neto por celda
 i,v=select_best(nets);return v,si.size,i
```

y en `main`, `pval=mcpt_pvalue(real,vals)`; agregar al JSON `'selection':'max_over_grid_42','schema_version':'mgc_ema_mcpt_v2'`. Si `grid` devuelve una estructura distinta de "neto por celda", adaptar con una línea (`nets=np.array([g[k]['net'] for k in ...])`), verificando primero `grid`'s return en `run_mgc_ema_screen.py:45-50`.

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_mcpt.py -q`
Expected: PASS (3 tests). El tool no se ejecuta (requiere `/data`); se verifica con `.venv\Scripts\python -m py_compile tools/mcpt_mgc_ema.py`.

- [ ] **Step 5: Commit**

```bash
git add edgelab/stats/mcpt.py tools/mcpt_mgc_ema.py tests/test_mcpt.py
git commit -m "feat(stats): MCPT con reoptimización del grid; el p-value compara contra la distribución de máximos"
```

---

### Task 8: Oráculo de costos y sensibilidad (mejora 7)

**Files:**
- Create: `edgelab/costs/__init__.py` (vacío), `edgelab/costs/oracle.py`, `config/costs/instruments.yaml`
- Modify: `edgelab/funnel/runner.py` (parámetro `cost_rt_ticks` y escenarios), `tools/run_funnel_arrays.py` (`--instrument`)
- Test: `tests/test_costs.py`

**Interfaces:**
- Produces: `CostModel(fees_side_usd, nfa_side_usd, broker_side_usd, spread_ticks, stop_slip_ticks, tick_value_usd)` con `rt_ticks(multiplier=1.0) -> float`; `load_cost_model(instrument) -> CostModel` desde YAML; `SCENARIOS = (1.0, 1.5, 2.0)`.
- `FunnelRunner.run_e1_e3(..., cost_rt_ticks=None)`: si se pasa, reemplaza `fees=.5`; payload agrega `cost_scenarios: {"1.0": survivors, "1.5": ..., "2.0": ...}` recomputando sólo el criterio de supervivencia sobre las medias (los valores por celda se ajustan restando `(mult-1)*cost_rt_ticks`).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_costs.py
from edgelab.costs.oracle import CostModel, load_cost_model, SCENARIOS

def test_mgc_round_trip_is_far_above_half_tick():
    m = load_cost_model("MGC")
    assert m.rt_ticks() >= 2.4           # Dossier D §8: 0.70 exch + 0.01 NFA por lado, tick 1 USD, spread >= 1 tick

def test_multiplier_scales_only_variable_part():
    m = CostModel(fees_side_usd=0.35, nfa_side_usd=0.01, broker_side_usd=0.3, spread_ticks=1.0, stop_slip_ticks=0.5, tick_value_usd=0.5)
    assert abs(m.rt_ticks(2.0) - 2 * m.rt_ticks(1.0)) < 1e-9

def test_scenarios_are_fixed():
    assert SCENARIOS == (1.0, 1.5, 2.0)
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_costs.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.costs`.

- [ ] **Step 3: Implementar**

```yaml
# config/costs/instruments.yaml
# Fuentes: Dossier D §8 (IBKR pass-through 2026, NFA desde 2026-07-01). broker_side_usd es SUPUESTO: confirmar con el broker real.
MGC: {fees_side_usd: 0.70, nfa_side_usd: 0.01, broker_side_usd: 0.25, spread_ticks: 1.0, stop_slip_ticks: 0.5, tick_value_usd: 1.00}
MNQ: {fees_side_usd: 0.353, nfa_side_usd: 0.01, broker_side_usd: 0.25, spread_ticks: 1.0, stop_slip_ticks: 0.5, tick_value_usd: 0.50}
MES: {fees_side_usd: 0.353, nfa_side_usd: 0.01, broker_side_usd: 0.25, spread_ticks: 1.0, stop_slip_ticks: 0.5, tick_value_usd: 1.25}
M2K: {fees_side_usd: 0.353, nfa_side_usd: 0.01, broker_side_usd: 0.25, spread_ticks: 1.0, stop_slip_ticks: 0.5, tick_value_usd: 0.50}
MYM: {fees_side_usd: 0.35, nfa_side_usd: 0.01, broker_side_usd: 0.25, spread_ticks: 1.0, stop_slip_ticks: 0.5, tick_value_usd: 0.50}
```

```python
# edgelab/costs/oracle.py
"""Oráculo de costos separado del motor (Dossier D §8; Yin et al. 2026).
Costo round-trip en ticks = 2*(fees+nfa+broker)/tick_value + spread + slippage de stop."""
from dataclasses import dataclass
from pathlib import Path
import yaml

SCENARIOS = (1.0, 1.5, 2.0)
_CFG = Path(__file__).resolve().parents[2] / "config" / "costs" / "instruments.yaml"


@dataclass(frozen=True)
class CostModel:
    fees_side_usd: float
    nfa_side_usd: float
    broker_side_usd: float
    spread_ticks: float
    stop_slip_ticks: float
    tick_value_usd: float

    def rt_ticks(self, multiplier=1.0):
        fixed = 2.0 * (self.fees_side_usd + self.nfa_side_usd + self.broker_side_usd) / self.tick_value_usd
        return float(multiplier * (fixed + self.spread_ticks + self.stop_slip_ticks))


def load_cost_model(instrument):
    data = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    return CostModel(**data[instrument])
```

En `runner.py`: firma `run_e1_e3(self,min_trades=30,min_t=2.0,spa_alpha=0.10,cost_rt_ticks=None)`; pasar `fees=cost_rt_ticks if cost_rt_ticks is not None else .5` a `iter_screen_batches` (agregar el parámetro `fees` a `iter_screen_batches` y `cheap_screen` si no lo propagan; `cheap_screen` ya tiene `fees=.5`). Después de calcular `rows`, agregar:

```python
        from edgelab.costs.oracle import SCENARIOS
        base=cost_rt_ticks if cost_rt_ticks is not None else .5;scen={}
        for mlt in SCENARIOS:
            extra=(mlt-1.0)*base
            scen[str(mlt)]=int(sum(1 for r in rows if r['survives_e1_e2'] and (r['d0_mean'] or 0)-extra>0 and (r['d1_mean'] or 0)-extra>0))
```

y `'cost_rt_ticks':base,'cost_scenarios':scen` en el payload. En `tools/run_funnel_arrays.py`: `p.add_argument('--instrument')` y, si se pasa, `cost=load_cost_model(a.instrument).rt_ticks()` → `r.run_e1_e3(cost_rt_ticks=cost)`.

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_costs.py tests/test_runner_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add edgelab/costs config/costs/instruments.yaml edgelab/funnel/runner.py edgelab/funnel/screen.py tools/run_funnel_arrays.py tests/test_costs.py
git commit -m "feat(costs): oráculo de costos por instrumento con fuentes y escenarios x1/x1.5/x2 en el embudo"
```

---

### Task 9: Controles canario (mejora 8)

**Files:**
- Create: `edgelab/funnel/canary.py`
- Modify: `edgelab/funnel/runner.py` (`require_canaries`)
- Test: `tests/test_canary.py`

**Interfaces:**
- Produces: `CANARY_LEAK="__CANARY_LEAK__"`, `CANARY_NULL="__CANARY_NULL__"`, `CANARY_BENCH="__CANARY_BENCH__"`; `leaked_oracle(close, trade_date, horizon=5) -> (idx, dirs)` (dirección = signo del retorno FUTURO); `random_null(n_bars, trade_date, n_signals, seed) -> (idx, dirs)`; `passive_benchmark(trade_date) -> (idx, dirs)` (long en la primera barra de cada sesión); `prefix_leak_test(signal_fn, args, cut) -> bool` (True si las señales del prefijo coinciden con las de la serie completa truncada, o sea, NO hay fuga).
- `FunnelRunner.run_e1_e3(..., require_canaries=False)`: si True y faltan los tres `family_id` reservados en `configs`, lanza `ValueError("missing canaries")`; el payload agrega `canaries: {leak_flagged: bool, null_survivors: int, bench_survivors: int}` y si `leak_flagged` es False la corrida se marca `invalid: "LEAK_NOT_DETECTED"`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_canary.py
import numpy as np
import pytest
from edgelab.funnel.canary import leaked_oracle, random_null, passive_benchmark, prefix_leak_test, CANARY_LEAK
from edgelab.funnel.signals import session_vwap_reclaim

def _series(seed=1, n=2000):
    rng = np.random.default_rng(seed)
    close = (10000 + np.cumsum(rng.integers(-3, 4, n))).astype(np.int32)
    td = np.repeat(np.arange(20250101, 20250101 + n // 100), 100).astype(np.int32)
    return close, td

def test_leaked_oracle_fails_prefix_test_and_vwap_passes():
    close, td = _series()
    assert prefix_leak_test(leaked_oracle, (close, td, 5), cut=1500) is False
    vol = np.ones(len(close), np.int64)
    assert prefix_leak_test(session_vwap_reclaim, (close, vol, td, 10, 5), cut=1500) is True

def test_random_null_is_deterministic_and_inside_sessions():
    _, td = _series()
    i1, d1 = random_null(len(td), td, 50, seed=3); i2, d2 = random_null(len(td), td, 50, seed=3)
    assert np.array_equal(i1, i2) and np.array_equal(d1, d2) and set(d1.tolist()) <= {-1, 1}

def test_passive_benchmark_one_long_per_session():
    _, td = _series()
    i, d = passive_benchmark(td)
    assert len(i) == len(np.unique(td)) and (d == 1).all()

def test_runner_requires_canaries(tmp_path):
    from edgelab.funnel.runner import FunnelRunner
    close, td = _series()
    cfg = [{"candidate_id": "x", "family_id": "F", "direction": "normal", "sl_ticks": 10, "tp_ticks": 10}]
    r = FunnelRunner(trade_dates=td, signal_idx=np.array([10]), signal_dir=np.array([1], np.int8), high=close + 1, low=close - 1,
                     bid_open=close - 1, ask_open=close + 1, configs=cfg, out_dir=tmp_path, backend="cpu")
    with pytest.raises(ValueError, match="missing canaries"):
        r.run_e1_e3(min_trades=1, require_canaries=True)
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_canary.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.funnel.canary`.

- [ ] **Step 3: Implementar**

```python
# edgelab/funnel/canary.py
"""Controles canario (Gençay 2026 E1/E5; XAlpha 2026): oráculo con fuga, nulo aleatorio, benchmark pasivo.
El oráculo es inexpresable por el proponente (usa el futuro) y se identifica SOLO por family_id reservado."""
import numpy as np

CANARY_LEAK = "__CANARY_LEAK__"
CANARY_NULL = "__CANARY_NULL__"
CANARY_BENCH = "__CANARY_BENCH__"
CANARIES = (CANARY_LEAK, CANARY_NULL, CANARY_BENCH)


def leaked_oracle(close, trade_date, horizon=5):
    c = np.asarray(close, dtype=np.int64); n = len(c)
    idx = np.arange(0, n - horizon - 1)
    fut = c[idx + horizon] - c[idx]
    keep = fut != 0
    return idx[keep], np.sign(fut[keep]).astype(np.int8)


def random_null(n_bars, trade_date, n_signals, seed):
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(n_bars - 1, size=min(n_signals, n_bars - 1), replace=False))
    return idx.astype(np.int64), rng.choice(np.array([-1, 1], np.int8), size=len(idx))


def passive_benchmark(trade_date):
    td = np.asarray(trade_date)
    first = np.flatnonzero(np.r_[True, td[1:] != td[:-1]])
    return first.astype(np.int64), np.ones(len(first), np.int8)


def prefix_leak_test(signal_fn, args, cut):
    """True = sin fuga: las señales calculadas sobre el prefijo [:cut] coinciden con las de la serie completa restringidas a < cut."""
    full_i, full_d = signal_fn(*args)
    pref_args = tuple(a[:cut] if isinstance(a, np.ndarray) and a.ndim == 1 and len(a) == len(args[0]) else a for a in args)
    pre_i, pre_d = signal_fn(*pref_args)
    m = full_i < cut
    return bool(np.array_equal(full_i[m], pre_i) and np.array_equal(full_d[m], pre_d))
```

En `runner.py`: importar `from .canary import CANARIES, CANARY_LEAK, CANARY_NULL, CANARY_BENCH`; firma `run_e1_e3(...,require_canaries=False)`; al inicio del método:

```python
        fams={c['family_id'] for c in self.cfg}
        if require_canaries and not set(CANARIES)<=fams:raise ValueError("missing canaries: "+",".join(sorted(set(CANARIES)-fams)))
```

Nota: las señales canario viven en arrays distintos a las de la familia; el runner actual recibe UN set de señales. Para esta tarea el contrato es por `family_id` en `configs`; la construcción de arrays combinados (concatenar señales canario con las de la familia y etiquetar por fila) se hace en `tools/run_funnel_arrays.py` con `--canaries` que llama a las tres funciones sobre `close_ticks.npy`/`trade_date.npy` y concatena, ordenando por índice. Al final del método, agregar al payload:

```python
        def _surv(f):return int(sum(1 for r in rows if r['family_id']==f and r['survives_e1_e2']))
        leak_flagged=bool(CANARY_LEAK in fams and _surv(CANARY_LEAK)>0)   # el oráculo DEBE "ganar": si no gana, el embudo no lo vio
        payload['canaries']={'leak_flagged':leak_flagged,'null_survivors':_surv(CANARY_NULL),'bench_survivors':_surv(CANARY_BENCH)}
        if require_canaries and not leak_flagged:payload['invalid']='LEAK_NOT_DETECTED'
```

(insertar antes de `rid=...`; `payload` debe construirse antes, así que mover la asignación de `rid`/ledger después de este bloque). El test de prefijo se ejecuta en `tools/run_funnel_arrays.py --canaries` sobre cada `signal_fn` y se escribe `prefix_leak_test` por familia en el payload como `leak_tests`.

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_canary.py tests/test_funnel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add edgelab/funnel/canary.py edgelab/funnel/runner.py tools/run_funnel_arrays.py tests/test_canary.py
git commit -m "feat(funnel): controles canario obligatorios (oráculo con fuga, nulo, benchmark) y test de prefijo"
```

---

### Task 10: Delay K8 y orden intra-barra K9 (mejora 10)

**Files:**
- Modify: `edgelab/funnel/screen.py` (`delay_bars`, `optimistic`), `edgelab/funnel/runner.py` (`robustness` por headline)
- Test: `tests/test_delay_order.py`

**Interfaces:**
- Produces: `cheap_screen(..., delay_bars=0, optimistic=False)`; `_cpu` y el kernel GPU reciben `delay` (entrada en `sig+1+delay`) y `opt` (si 1, se evalúa TP antes que SL en cada barra). Runner: para cada headline, `robustness: {"delay1_sign_flips": bool, "optimistic_changes_verdict": bool}`; cualquiera True marca `headline["killed_by"]` = `"K8"` o `"K9"`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_delay_order.py
import numpy as np
from edgelab.funnel.screen import cheap_screen

H = np.array([100, 100, 112, 100, 100, 100], np.int32); L = np.array([100, 99, 88, 100, 100, 100], np.int32)
BO = np.full(6, 99, np.int32); AO = np.full(6, 101, np.int32)

def test_pessimistic_hits_stop_optimistic_hits_target_in_ambiguous_bar():
    # long en 0, entra en barra 1 a 101; barra 2 toca 112 (TP 10 -> 111) y 88 (SL 10 -> 91): ambigua
    pes, _ = cheap_screen(np.array([0]), np.array([1], np.int8), H, L, BO, AO, np.array([10]), np.array([10]), max_hold_bars=3, backend="cpu", fees=0.0)
    opt, _ = cheap_screen(np.array([0]), np.array([1], np.int8), H, L, BO, AO, np.array([10]), np.array([10]), max_hold_bars=3, backend="cpu", fees=0.0, optimistic=True)
    assert pes[0, 0] == -10 and opt[0, 0] == 10

def test_delay_shifts_entry_bar():
    d0, _ = cheap_screen(np.array([0]), np.array([1], np.int8), H, L, BO, AO, np.array([10]), np.array([10]), max_hold_bars=3, backend="cpu", fees=0.0)
    d1, _ = cheap_screen(np.array([0]), np.array([1], np.int8), H, L, BO, AO, np.array([10]), np.array([10]), max_hold_bars=3, backend="cpu", fees=0.0, delay_bars=1)
    assert d0[0, 0] == -10 and d1[0, 0] == -10      # con delay 1 entra en barra 2 a 101; misma barra ambigua -> stop primero
    d2, _ = cheap_screen(np.array([0]), np.array([1], np.int8), H, L, BO, AO, np.array([10]), np.array([10]), max_hold_bars=3, backend="cpu", fees=0.0, delay_bars=2)
    assert d2[0, 0] == 0                              # entra en barra 3: nada toca, sale flat por max_hold
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_delay_order.py -q`
Expected: FAIL con `TypeError: unexpected keyword argument 'optimistic'`.

- [ ] **Step 3: Implementar en `screen.py`**

En `_cpu(sig,dirs,h,l,bid_open,ask_open,sls,tps,mults,max_hold,fees,delay,opt)`: `i=sig[k]+1+delay`; dentro del bucle por barra, si `opt==1` evaluar primero la condición de TP y después la de SL (invertir el orden de los dos `if`), si no, el orden actual. Al salir por `max_hold` sin tocar nada, `x=-fees` (ya existe). En el kernel GPU agregar parámetros `int delay,int opt` con la misma lógica (`i=(int)sig[k]+1+delay`; dos ramas por `opt`). `cheap_screen(...,fees=.5,backend="auto",delay_bars=0,optimistic=False)` propaga ambos; `iter_screen_batches` los acepta y propaga.

En `runner.py`, después de elegir `heads`, para cada headline:

```python
        for hd in heads:
            j=self.cfg.index(next(c for c in self.cfg if c['candidate_id']==hd['candidate_id']))
            base,_=cheap_screen(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl[j:j+1],tp[j:j+1],mult[j:j+1],fees=base_fees,backend=self.backend)
            d1,_=cheap_screen(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl[j:j+1],tp[j:j+1],mult[j:j+1],fees=base_fees,backend=self.backend,delay_bars=1)
            op,_=cheap_screen(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl[j:j+1],tp[j:j+1],mult[j:j+1],fees=base_fees,backend=self.backend,optimistic=True)
            m=lambda x:float(np.nanmean(x[np.isfinite(x)])) if np.isfinite(x).any() else 0.0
            flips=m(base)>0 and m(d1)<=0;opt_change=(m(base)>0)!=(m(op)>0)
            hd['robustness']={'delay1_sign_flips':bool(flips),'optimistic_changes_verdict':bool(opt_change)}
            if flips:hd['killed_by']='K8'
            elif opt_change:hd['killed_by']='K9'
```

(`base_fees` es la variable `base` de la Tarea 8; renombrar allí a `base_fees` para evitar colisión).

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_delay_order.py tests/test_funnel.py tests/test_runner_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add edgelab/funnel/screen.py edgelab/funnel/runner.py tests/test_delay_order.py
git commit -m "feat(funnel): kill rules K8 (delay 1 barra) y K9 (orden intra-barra) sobre cada headline"
```

---

### Task 11: Testing diferencial de motor (mejora 9)

**Files:**
- Create: `validation/engine_differential.py`
- Test: `tests/test_engine_differential.py`

**Interfaces:**
- Produces: `naive_replay(sig, dirs, h, l, bo, ao, sl, tp, mult, max_hold, fees, delay=0, optimistic=False) -> np.ndarray` (simulador independiente, Python puro, un trade por señal, sin vectorizar); `differential(sig, dirs, h, l, bo, ao, sls, tps, mults, max_hold) -> dict(max_abs_diff, n_cells, equal_at_zero_cost: bool)`.
- hftbacktest queda como seguimiento explícito: requiere datos MBO y no entra en este plan. Anotar en el docstring.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_engine_differential.py
import numpy as np
from validation.engine_differential import naive_replay, differential
from edgelab.funnel.screen import cheap_screen

def test_naive_matches_cheap_screen_at_zero_cost_on_random_paths():
    rng = np.random.default_rng(21)
    n = 3000
    close = 10000 + np.cumsum(rng.integers(-4, 5, n)); h = close + rng.integers(0, 4, n); l = close - rng.integers(0, 4, n)
    bo, ao = (close - 1).astype(np.int32), (close + 1).astype(np.int32)
    sig = np.sort(rng.choice(n - 100, 120, replace=False)); dirs = rng.choice(np.array([-1, 1], np.int8), 120)
    sls = np.array([5, 10, 20]); tps = np.array([5, 10, 20, 40]); 
    SL, TP = np.meshgrid(sls, tps); SL, TP = SL.ravel(), TP.ravel(); MU = np.ones(len(SL), np.int8)
    rep = differential(sig, dirs, h.astype(np.int32), l.astype(np.int32), bo, ao, SL, TP, MU, max_hold=50)
    assert rep["equal_at_zero_cost"] and rep["max_abs_diff"] == 0.0 and rep["n_cells"] == 12
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_engine_differential.py -q`
Expected: FAIL con `ModuleNotFoundError: validation.engine_differential`.

- [ ] **Step 3: Implementar**

```python
# validation/engine_differential.py
"""Testing diferencial de motor (Yin et al. 2026; Dossier D §2 y K12).
Un replay independiente, escrito sin mirar screen.py, debe coincidir celda a celda a costo cero.
hftbacktest (MBO) queda como segundo motor cuando haya datos de libro; no entra acá."""
import numpy as np
from edgelab.funnel.screen import cheap_screen


def naive_replay(sig, dirs, h, l, bo, ao, sl, tp, mult, max_hold, fees, delay=0, optimistic=False):
    out = np.full(len(sig), np.nan)
    n = len(h)
    for k, s in enumerate(sig):
        i = int(s) + 1 + delay
        if i >= n:
            continue
        d = int(dirs[k]) * int(mult)
        entry = int(ao[i]) if d == 1 else int(bo[i])
        stop = entry - d * int(sl); target = entry + d * int(tp)
        res = -fees
        for j in range(i, min(n, i + max_hold + 1)):
            hit_sl = (int(l[j]) <= stop) if d == 1 else (int(h[j]) >= stop)
            hit_tp = (int(h[j]) >= target + 1) if d == 1 else (int(l[j]) <= target - 1)
            if optimistic and hit_tp: res = tp - fees; break
            if hit_sl: res = -sl - fees; break
            if hit_tp: res = tp - fees; break
        out[k] = res
    return out


def differential(sig, dirs, h, l, bo, ao, sls, tps, mults, max_hold):
    fast, _ = cheap_screen(sig, dirs, h, l, bo, ao, sls, tps, mults, max_hold_bars=max_hold, fees=0.0, backend="cpu")
    slow = np.column_stack([naive_replay(sig, dirs, h, l, bo, ao, sls[q], tps[q], mults[q], max_hold, 0.0) for q in range(len(sls))])
    diff = np.nan_to_num(np.abs(fast - slow), nan=0.0)
    return {"max_abs_diff": float(diff.max()), "n_cells": int(len(sls)), "equal_at_zero_cost": bool(diff.max() == 0.0)}
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_engine_differential.py -q`
Expected: PASS. Si falla por una diferencia real, NO ajustar el replay naive para que coincida: es un hallazgo sobre `screen.py` y se registra antes de tocar nada.

- [ ] **Step 5: Commit**

```bash
git add validation/engine_differential.py tests/test_engine_differential.py
git commit -m "test(validation): replay independiente coincide con cheap_screen a costo cero (K12)"
```

---

### Task 12: Familia intraday momentum última media hora (mejora 12)

**Files:**
- Modify: `edgelab/funnel/signals.py` (nueva función)
- Create: `config/funnel/hypothesis_intraday_momentum.yaml`
- Test: `tests/test_funnel_signals.py` (agregar)

**Interfaces:**
- Produces: `intraday_momentum_last30(close, bar_sec_of_day, trade_date, session_close_sec, window_sec=1800) -> (idx, dirs)`: una señal por sesión en la primera barra con `bar_sec_of_day >= session_close_sec - window_sec`; dirección = signo de `close[i] - close[primera barra de la sesión]`; cero no genera señal. Causal (sólo usa barras ≤ i).

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_funnel_signals.py`:

```python
from edgelab.funnel.signals import intraday_momentum_last30

def test_intraday_momentum_last30_one_signal_per_session_prefix_and_mirror():
    c = np.array([100, 101, 103, 104, 105,  200, 198, 197, 196, 195], np.int32)
    sec = np.array([34200, 40000, 50000, 56000, 57000, 34200, 40000, 50000, 56000, 57000], np.int32)   # RTH 09:30-16:00 ET -> cierre 57600
    td = np.array([1, 1, 1, 1, 1, 2, 2, 2, 2, 2], np.int32)
    i, d = intraday_momentum_last30(c, sec, td, 57600)
    assert i.tolist() == [3, 8] and d.tolist() == [1, -1]
    mi, md = intraday_momentum_last30(-c, sec, td, 57600)
    assert np.array_equal(i, mi) and np.array_equal(d, -md)
    pi, pd = intraday_momentum_last30(c[:7], sec[:7], td[:7], 57600)
    assert pi.tolist() == [3] and pd.tolist() == [1]
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_funnel_signals.py -q`
Expected: FAIL con `ImportError: cannot import name 'intraday_momentum_last30'`.

- [ ] **Step 3: Implementar**

Agregar a `edgelab/funnel/signals.py`:

```python
@njit(cache=True)
def intraday_momentum_last30(close,bar_sec_of_day,trade_date,session_close_sec,window_sec=1800):
 """Market intraday momentum (Gao et al. 2018 JFE; Baltussen et al. 2021 JFE): el retorno del día hasta
 la última media hora predice la última media hora. Señal en la primera barra dentro de la ventana final."""
 idx=np.empty(len(close),np.int64);dirs=np.empty(len(close),np.int8);n=0;open_c=0;fired=False
 for i in range(len(close)):
  if i==0 or trade_date[i]!=trade_date[i-1]:open_c=close[i];fired=False
  if not fired and bar_sec_of_day[i]>=session_close_sec-window_sec:
   fired=True;dlt=close[i]-open_c
   if dlt>0:idx[n]=i;dirs[n]=1;n+=1
   elif dlt<0:idx[n]=i;dirs[n]=-1;n+=1
 return idx[:n],dirs[:n]
```

Crear `config/funnel/hypothesis_intraday_momentum.yaml`:

```yaml
schema_version: edgelab_hypothesis_v1
hypothesis_id: HYP-INTRADAY-MOMENTUM-LAST30-001
family_id: INTRADAY_MOMENTUM_LAST30
source_type: LITERATURE
asserts_edge: false
economic_story: Gamma hedging de market makers de opciones y rebalanceo de ETFs apalancados generan flujo direccional en la última media hora alineado con el retorno del día (Baltussen et al. 2021).
roles:
  location: {family: SESSION_LAST_WINDOW, params_coarse: [1800]}
  regime: {family: NONE, params_coarse: []}
  trigger: {family: SIGN_OF_DAY_RETURN, params_coarse: [ONE_BAR]}
  invalidate: {rule: HOLD_TO_SESSION_CLOSE}
n_free_params: 1
prediction: El efecto debe ser mayor en días de alta volatilidad realizada y en vencimientos de opciones; ausente en la primera hora.
refutation: t neto OOS < 2 por fold con costos del oráculo, o signo distinto en al menos un año OOS.
refs: [Gao-Han-Li-Zhou 2018 JFE 129:394-414, Baltussen-Da-Lammers-Martens 2021 JFE 142:377-403, McLean-Pontiff 2016 JF 71:5-32]
ablations: [shuffle_within_session, first_half_hour_instead_of_last, random_window_same_length]
data_requirements: [L1_ticks, bar_sec_of_day, session_close_sec]
forbidden: [continuous_period_search, post_hoc_grid_expansion]
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_funnel_signals.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add edgelab/funnel/signals.py config/funnel/hypothesis_intraday_momentum.yaml tests/test_funnel_signals.py
git commit -m "feat(signals): familia intraday momentum última media hora, preregistrada con predicción y refutación"
```

---

### Task 13: Priors de familias y archivo de scripts vectorbt (mejoras 11, 13, 16)

**Files:**
- Create: `config/funnel/families_prior.yaml`, `edgelab/funnel/admissibility.py`, `archive/validation_vectorbt/README.md`
- Move: `validation/vectorbt_*.py` → `archive/validation_vectorbt/`
- Test: `tests/test_admissibility.py`

**Interfaces:**
- Produces: `assert_family_admissible(family_id, available_data: set[str]) -> None` (lanza `FamilyRefuted(cite)` si `status: refuted`; lanza `DataMissing(req)` si `requires` no está en `available_data`; marca `folklore` sólo como advertencia devuelta por `family_prior(family_id) -> dict`).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_admissibility.py
import pytest
from edgelab.funnel.admissibility import assert_family_admissible, family_prior, FamilyRefuted, DataMissing

def test_refuted_family_is_blocked_with_citation():
    with pytest.raises(FamilyRefuted, match="Mesfin"):
        assert_family_admissible("ORB_5MIN_MNQ", {"L1_ticks"})

def test_ofi_requires_l2():
    with pytest.raises(DataMissing, match="L2"):
        assert_family_admissible("OFI_CONT_2014", {"L1_ticks"})
    assert_family_admissible("OFI_CONT_2014", {"L1_ticks", "L2_MBP10"})

def test_folklore_is_allowed_but_tagged():
    assert_family_admissible("VOLUME_PROFILE_POC", {"L1_ticks"})
    assert family_prior("VOLUME_PROFILE_POC")["status"] == "folklore"

def test_supported_family_has_refs():
    assert len(family_prior("INTRADAY_MOMENTUM_LAST30")["refs"]) >= 2
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_admissibility.py -q`
Expected: FAIL con `ModuleNotFoundError`.

- [ ] **Step 3: Implementar**

```yaml
# config/funnel/families_prior.yaml
# Dossier D, secciones 3 y "Familias de señales". status: supported | folklore | refuted. refuted entra al ledger como retirada desde el día cero.
INTRADAY_MOMENTUM_LAST30: {status: supported, refs: ["Gao et al. 2018 JFE", "Baltussen et al. 2021 JFE"], note: "decaimiento post-publicación reportado"}
OFI_CONT_2014: {status: supported, requires: [L2_MBP10], refs: ["Cont-Kukanov-Stoikov 2014 JFEc", "Cont-Cucuringu-Zhang 2023 QF"], note: "forecast en horizonte de segundos (Takahashi 2025)"}
VOLUME_PROFILE_POC: {status: folklore, refs: [], note: "sin evidencia revisada por pares"}
AUCTION_MARKET_THEORY: {status: folklore, refs: []}
FOOTPRINT_ABSORPTION: {status: folklore, refs: []}
HFT_ZONES: {status: folklore, refs: [], note: "cinco mediciones internas sin efecto (CLAUDE.md 2026-08-21)"}
BIGTRAP2_MAGNET: {status: refuted, refs: ["EdgeLab F2.7-F2.10 2026-08-13"]}
ORB_5MIN_MNQ: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
ASIA_RANGE_EXPANSION: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
ASIA_LIQUIDITY_GRAB: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
GAP_FILL: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
VOLUME_SPIKE: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
VOLUME_DRYUP: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
POST_NEWS_DRIFT: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
OU_INTRADAY_MGC: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.04004"]}
ML_OHLCV_5MIN: {status: refuted, refs: ["Mesfin 2026 arXiv:2605.17724"]}
```

```python
# edgelab/funnel/admissibility.py
"""EF0: admisibilidad de familias por prior de literatura (Dossier D)."""
from pathlib import Path
import yaml

_CFG = Path(__file__).resolve().parents[2] / "config" / "funnel" / "families_prior.yaml"


class FamilyRefuted(ValueError):
    pass


class DataMissing(ValueError):
    pass


def family_prior(family_id):
    data = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    return data.get(family_id, {"status": "unknown", "refs": []})


def assert_family_admissible(family_id, available_data):
    p = family_prior(family_id)
    if p["status"] == "refuted":
        raise FamilyRefuted(f"{family_id} refutada: {'; '.join(p['refs'])}")
    missing = [r for r in p.get("requires", []) if r not in set(available_data)]
    if missing:
        raise DataMissing(f"{family_id} requiere {missing}")
```

Mover los scripts: `git mv validation/vectorbt_es_10am_deepdive.py validation/vectorbt_es_optimization.py validation/vectorbt_es_validation.py validation/vectorbt_eurusd_deep.py validation/vectorbt_eurusd_opt.py validation/vectorbt_eurusd_portfolio.py validation/vectorbt_eurusd_tod.py archive/validation_vectorbt/` y crear `archive/validation_vectorbt/README.md` con: "Archivado 2026-10-05. vectorbt resuelve la ambigüedad intra-barra por supuesto, no por hecho (Dossier D §4). Ningún resultado de estos scripts alimenta decisiones; se conservan por procedencia."

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_admissibility.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add config/funnel/families_prior.yaml edgelab/funnel/admissibility.py tests/test_admissibility.py archive/validation_vectorbt validation
git commit -m "feat(funnel): priors de familias (refutadas con cita, folklore, requiere L2) y archivo de scripts vectorbt"
```

---

### Task 14: Kaggle batch con `dataset_sources` (mejora 15)

**Files:**
- Create: `edgelab/kaggle/batch.py`, `tools/kaggle_push_kernel.py`
- Test: `tests/test_kaggle_batch.py`

**Interfaces:**
- Produces: `kernel_metadata(slug, title, code_file, dataset_sources, enable_gpu, enable_tpu=False) -> dict` (siempre `enable_internet: False`, `kernel_type: script`, `is_private: True`, `language: python`); `write_kernel_dir(dir, metadata, script_text) -> Path`. El push real usa el CLI `kaggle kernels push -p <dir>` y el estado `kaggle kernels status <slug>`; ambos se invocan desde el tool, nunca desde tests.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_kaggle_batch.py
import json
from edgelab.kaggle.batch import kernel_metadata, write_kernel_dir

def test_metadata_is_private_offline_and_lists_sources(tmp_path):
    md = kernel_metadata("user/edgelab-ef2-001", "EF2 001", "kernel.py", ["user/edgelab-arrays"], enable_gpu=True)
    assert md["enable_internet"] is False and md["is_private"] is True and md["enable_gpu"] is True
    assert md["dataset_sources"] == ["user/edgelab-arrays"] and md["kernel_type"] == "script"
    d = write_kernel_dir(tmp_path / "k", md, "print('hi')")
    assert json.loads((d / "kernel-metadata.json").read_text())["id"] == "user/edgelab-ef2-001"
    assert (d / "kernel.py").read_text() == "print('hi')"
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_kaggle_batch.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.kaggle.batch`.

- [ ] **Step 3: Implementar**

```python
# edgelab/kaggle/batch.py
"""Kernels batch de Kaggle (Dossier D §5): kernel-metadata.json con dataset_sources; internet siempre apagado.
La credencial vive en %USERPROFILE%/.kaggle/kaggle.json y sólo la lee el CLI `kaggle`."""
import json
from pathlib import Path


def kernel_metadata(slug, title, code_file, dataset_sources, enable_gpu, enable_tpu=False):
    return {"id": slug, "title": title, "code_file": code_file, "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": bool(enable_gpu), "enable_tpu": bool(enable_tpu), "enable_internet": False,
            "dataset_sources": list(dataset_sources), "competition_sources": [], "kernel_sources": [], "model_sources": []}


def write_kernel_dir(directory, metadata, script_text):
    d = Path(directory); d.mkdir(parents=True, exist_ok=True)
    (d / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (d / metadata["code_file"]).write_text(script_text, encoding="utf-8")
    return d
```

```python
# tools/kaggle_push_kernel.py
#!/usr/bin/env python3
"""Sube un kernel batch y hace polling. Uso:
  python tools/kaggle_push_kernel.py --slug user/edgelab-ef2-001 --script kernel.py --dataset user/edgelab-arrays --gpu"""
import argparse, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.batch import kernel_metadata, write_kernel_dir

def main():
    p = argparse.ArgumentParser(); p.add_argument("--slug", required=True); p.add_argument("--script", required=True)
    p.add_argument("--dataset", action="append", required=True); p.add_argument("--gpu", action="store_true"); p.add_argument("--tpu", action="store_true")
    p.add_argument("--out", default="runs/kaggle"); p.add_argument("--poll", type=int, default=120); a = p.parse_args()
    md = kernel_metadata(a.slug, a.slug.split("/")[-1], "kernel.py", a.dataset, a.gpu, a.tpu)
    d = write_kernel_dir(Path(a.out) / a.slug.split("/")[-1], md, Path(a.script).read_text(encoding="utf-8"))
    subprocess.run(["kaggle", "kernels", "push", "-p", str(d)], check=True)
    while True:
        r = subprocess.run(["kaggle", "kernels", "status", a.slug], capture_output=True, text=True); print(r.stdout.strip(), flush=True)
        if any(s in r.stdout for s in ("complete", "error", "cancel")): break
        time.sleep(a.poll)
    subprocess.run(["kaggle", "kernels", "output", a.slug, "-p", str(d / "output")], check=True)

if __name__ == "__main__": main()
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_kaggle_batch.py -q`
Expected: PASS. Verificación manual posterior, sólo con el token puesto por el responsable: `kaggle datasets list --mine`.

- [ ] **Step 5: Commit**

```bash
git add edgelab/kaggle/batch.py tools/kaggle_push_kernel.py tests/test_kaggle_batch.py
git commit -m "feat(kaggle): kernels batch privados con dataset_sources e internet apagado"
```

---

### Task 15: Alpha-wealth con e-LOND (mejora 17)

**Files:**
- Create: `edgelab/sequential/__init__.py` (vacío), `edgelab/sequential/alpha_wealth.py`
- Test: `tests/test_alpha_wealth.py`

**Interfaces:**
- Produces: `HoldoutBudget(path, alpha=0.05)` persistido en JSON; `request_opening(candidate_id, e_value) -> bool` (e-LOND: `alpha_t = alpha * gamma_t * (1 + rejections_so_far)`, `gamma_t = 6/(pi^2 t^2)`; abre si `e_value >= 1/alpha_t`); `state() -> dict(t, rejections, history)`; `can_open() -> bool` (False si `alpha_t < 1e-12`, es decir presupuesto agotado en la práctica). Cada petición, abierta o no, incrementa `t` (cuenta como test).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_alpha_wealth.py
import math
from edgelab.sequential.alpha_wealth import HoldoutBudget

def test_threshold_equality_opens(tmp_path):
    b = HoldoutBudget(tmp_path / "aw.json", alpha=0.05)
    gamma1 = 6 / (math.pi ** 2)
    e_exact = 1 / (0.05 * gamma1 * 1)
    assert b.request_opening("c1", e_exact) is True
    assert b.state()["rejections"] == 1

def test_each_request_consumes_budget_and_rejections_recover(tmp_path):
    b = HoldoutBudget(tmp_path / "aw.json", alpha=0.05)
    assert b.request_opening("c1", 1.0) is False           # e=1: sin evidencia
    th_before = b.current_threshold()
    assert b.request_opening("c2", 1e9) is True             # descubrimiento
    assert b.current_threshold() < th_before * 2            # (1+R) sube la alpha_t pero gamma_t baja: el umbral no se dispara
    assert b.request_opening("c3", 2.0) is False

def test_state_persists(tmp_path):
    p = tmp_path / "aw.json"
    HoldoutBudget(p).request_opening("c1", 1e9)
    assert HoldoutBudget(p).state()["t"] == 1
```

- [ ] **Step 2: Correr para verificar que falla**

Run: `.venv\Scripts\python -m pytest tests/test_alpha_wealth.py -q`
Expected: FAIL con `ModuleNotFoundError: edgelab.sequential`.

- [ ] **Step 3: Implementar**

```python
# edgelab/sequential/alpha_wealth.py
"""Presupuesto de alpha para aperturas de holdout: e-LOND (Xu & Ramdas 2024; Dossier B §7).
Control de FDR online bajo dependencia arbitraria. Cada petición cuenta como test aunque no abra.
# ponytail: e-LOND con gamma_t = 6/(pi^2 t^2); si hiciera falta potencia, pasar a SAFFRON/ADDIS vía `online-fdr`.
"""
import json, math
from pathlib import Path


class HoldoutBudget:
    def __init__(self, path, alpha=0.05):
        self.path = Path(path); self.alpha = alpha
        self.s = json.loads(self.path.read_text()) if self.path.exists() else {"t": 0, "rejections": 0, "history": []}

    def _gamma(self, t):
        return 6.0 / (math.pi ** 2 * t ** 2)

    def current_threshold(self):
        t = self.s["t"] + 1
        alpha_t = self.alpha * self._gamma(t) * (1 + self.s["rejections"])
        return 1.0 / alpha_t

    def can_open(self):
        return self.current_threshold() < 1e12

    def request_opening(self, candidate_id, e_value):
        th = self.current_threshold()
        opened = bool(e_value >= th)
        self.s["t"] += 1
        if opened: self.s["rejections"] += 1
        self.s["history"].append({"t": self.s["t"], "candidate_id": candidate_id, "e_value": float(e_value), "threshold": th, "opened": opened})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.s, indent=2), encoding="utf-8")
        return opened

    def state(self):
        return dict(self.s)
```

- [ ] **Step 4: Correr para verificar que pasa**

Run: `.venv\Scripts\python -m pytest tests/test_alpha_wealth.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add edgelab/sequential tests/test_alpha_wealth.py
git commit -m "feat(sequential): presupuesto de alpha e-LOND para aperturas de holdout, persistido y con historial"
```

---

### Task 16: Suite completa y acta

**Files:**
- Create: `docs/research/MEJORAS_EMBUDO_ACTA_20261005.md`

- [ ] **Step 1: Correr toda la suite**

Run: `.venv\Scripts\python -m pytest tests -q`
Expected: todo PASS. Anotar el conteo.

- [ ] **Step 2: Escribir el acta**

Contenido mínimo: tabla mejora → commit → test que la cubre; lista de lo que NO se hizo (hftbacktest como segundo motor; ONC para N_eff; conexión del runner MGC real a las nuevas compuertas, que requiere `/data`); y la línea obligatoria "Aporte al referente: …".

- [ ] **Step 3: Commit**

```bash
git add docs/research/MEJORAS_EMBUDO_ACTA_20261005.md
git commit -m "docs(research): acta de las 17 mejoras del embudo con commits y tests"
```

---

## Self-review

**Cobertura:** las 17 mejoras tienen tarea (tabla al inicio). La mejora 9 queda parcial (replay independiente sí; hftbacktest no), dicho explícitamente en la Tarea 11 y en el acta.

**Placeholders:** ninguno; cada tarea tiene código y comando. La Tarea 7 condiciona una línea a verificar el retorno real de `grid()` en `run_mgc_ema_screen.py:45-50`, que no está en este contexto: la instrucción es leerlo antes de adaptar, no inventar.

**Consistencia de tipos:** `cheap_screen(..., fees, backend, delay_bars, optimistic)` se usa igual en Tareas 10 y 11; `run_e1_e3(min_trades, min_t, spa_alpha, cost_rt_ticks, require_canaries)` se acumula en Tareas 6, 8, 9 en ese orden; `base_fees` es el nombre único de la variable de costo en el runner (Tareas 8 y 10).

**Review Focus:** los cinco puntos tienen test: días cero (T4 `test_daily_pnl_keeps_zero_days`), familia no declarada (T6 `test_undeclared_family_is_its_own_gate`), `arch` ausente (T6 `test_runner_survives_without_arch`), canario por `family_id` (T9, los canarios se identifican sólo por constante reservada), igualdad en umbral (T15 `test_threshold_equality_opens`).
