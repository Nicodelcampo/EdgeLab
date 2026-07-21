"""Configuración PORTABLE de EdgeLab — punto ÚNICO de verdad para rutas.

Precedencia (gana el primero): config/local.toml  >  variables EDGELAB_*  >
config/default.toml  >  defaults derivados de la raíz del repo.

Resuelve rutas; NO crea directorios al importar (el código que los use los crea
on-demand con ensure_dir). Validado con pydantic. Las fuentes externas del
ecosistema son opcionales (None si no se configura su root) y de SOLO LECTURA.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Raíz del repo derivada de la ubicación de ESTE archivo (portable, sin hardcode).
ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

# clave lógica -> variable de entorno
_ENV = {
    "root": "EDGELAB_ROOT",
    "data_dir": "EDGELAB_DATA_ROOT",
    "artifacts_dir": "EDGELAB_ARTIFACTS_ROOT",
    "runs_dir": "EDGELAB_RUNS_ROOT",
    "cache_dir": "EDGELAB_CACHE_ROOT",
    "manifests_dir": "EDGELAB_MANIFESTS_ROOT",
    "parity_dir": "EDGELAB_PARITY_ROOT",
    "feature_zone_store_dir": "EDGELAB_FEATURE_ZONE_STORE_ROOT",
    "nt8_export_root": "EDGELAB_NT8_EXPORT_ROOT",
    "cerebro_root": "EDGELAB_CEREBRO_ROOT",
    "vectorbt_ecosystem_root": "EDGELAB_VECTORBT_ROOT",
    "nq_raw_dir": "EDGELAB_NQ_RAW_ROOT",
    "eurusd_ticks_raw": "EDGELAB_EURUSD_TICKS_RAW",
}


class EdgeLabPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: Path
    data_dir: Path
    artifacts_dir: Path
    runs_dir: Path
    cache_dir: Path
    manifests_dir: Path
    parity_dir: Path
    feature_zone_store_dir: Path
    # roots/archivos externos (machine-specific): opcionales, None si no se configuran
    nt8_export_root: Optional[Path] = None
    cerebro_root: Optional[Path] = None
    vectorbt_ecosystem_root: Optional[Path] = None
    nq_raw_dir: Optional[Path] = None
    eurusd_ticks_raw: Optional[Path] = None


def _load_toml(path: Optional[Path]) -> dict:
    if path is None or not Path(path).exists():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("paths", data)  # acepta [paths] o claves top-level


def _pick(key: str, local: dict, env: dict, default: dict):
    """Precedencia: local.toml > EDGELAB_* env > default.toml. None si nada aplica."""
    if local.get(key) not in (None, ""):
        return local[key]
    ev = _ENV.get(key)
    if ev and env.get(ev) not in (None, ""):
        return env[ev]
    if default.get(key) not in (None, ""):
        return default[key]
    return None


def resolve_settings(env: Optional[dict] = None, default_toml: Optional[Path] = None,
                     local_toml: Optional[Path] = None) -> EdgeLabPaths:
    """Resuelve las rutas aplicando la precedencia. `default_toml`/`local_toml`
    por defecto apuntan a config/. Rutas inexistentes se tratan como vacío."""
    env = os.environ if env is None else env
    default = _load_toml(default_toml if default_toml is not None else CONFIG_DIR / "default.toml")
    local = _load_toml(local_toml if local_toml is not None else CONFIG_DIR / "local.toml")

    root = Path(_pick("root", local, env, default) or ROOT)

    def _dir(key: str, fallback: str) -> Path:      # dir interno, default root-relativo
        v = _pick(key, local, env, default)
        return Path(v) if v else (root / fallback)

    def _ext(key: str) -> Optional[Path]:           # externo opcional
        v = _pick(key, local, env, default)
        return Path(v) if v else None

    return EdgeLabPaths(
        root=root,
        data_dir=_dir("data_dir", "data"),
        artifacts_dir=_dir("artifacts_dir", "artifacts"),
        runs_dir=_dir("runs_dir", "runs"),
        cache_dir=_dir("cache_dir", "cache"),
        manifests_dir=_dir("manifests_dir", "manifests"),
        parity_dir=_dir("parity_dir", "parity"),
        feature_zone_store_dir=_dir("feature_zone_store_dir", "feature_zone_store"),
        nt8_export_root=_ext("nt8_export_root"),
        cerebro_root=_ext("cerebro_root"),
        vectorbt_ecosystem_root=_ext("vectorbt_ecosystem_root"),
        nq_raw_dir=_ext("nq_raw_dir"),
        eurusd_ticks_raw=_ext("eurusd_ticks_raw"),
    )


def ensure_dir(path: Path) -> Path:
    """Crea el directorio on-demand (NO se llama al importar el módulo)."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return Path(path)


SETTINGS = resolve_settings()

# =========================================================================
# API de compatibilidad: mismos nombres de antes, ahora RESUELTOS (no hardcode)
# =========================================================================
ROOT = SETTINGS.root
DATA_DIR = SETTINGS.data_dir
RUNS_DIR = SETTINGS.runs_dir
ARTIFACTS_DIR = SETTINGS.artifacts_dir
CACHE_DIR = SETTINGS.cache_dir
MANIFESTS_DIR = SETTINGS.manifests_dir
PARITY_DIR = SETTINGS.parity_dir
FEATURE_ZONE_STORE_DIR = SETTINGS.feature_zone_store_dir
NT8_EXPORT_ROOT = SETTINGS.nt8_export_root
CEREBRO_ROOT = SETTINGS.cerebro_root

# --- fuentes del ecosistema (read-only) — opcionales; None si no se configura el root ---
_VBT = SETTINGS.vectorbt_ecosystem_root
ES_TICKS = (_VBT / "ES_ticks.parquet") if _VBT else None            # 148.8M ticks, bid/ask
ES_M1 = (_VBT / "data" / "es_m1_candles.parquet") if _VBT else None  # velas M1, indice ns

# --- fuentes crudas NQ (exports por contrato, NT8, orden cronologico) ---
NQ_RAW_DIR = SETTINGS.nq_raw_dir
NQ_CONTRACTS = ["NQ 09-25.Last.txt", "NQ 12-25.Last.txt", "NQ 03-26.Last.txt",
                "NQ 06-26.Last.txt", "NQ 09-26.Last.txt"]

# --- artefactos propios (ROOT-relativos, portables) ---
NQ_TICKS_CLEAN = DATA_DIR / "nq_ticks_clean.parquet"
NQ_M1_CLEAN = DATA_DIR / "nq_m1_clean.parquet"
EURUSD_TICKS_RAW = SETTINGS.eurusd_ticks_raw
EURUSD_TICKS = DATA_DIR / "eurusd_ticks.parquet"

# --- VENTANAS ENVENENADAS de ES_ticks.parquet (hallazgo EXP-044) ---
# En las semanas de roll la cinta entrelaza DOS contratos (~55 pts aparte,
# mismo ms): 670k saltos >5pt en mar-16..20 y 478k en jun-11..15. Toda señal
# tick-level generada ahi es artefactual. Se excluyen mecanicamente via
# poison_mask(); el fix real requiere re-export por contrato (como el NQ).
ES_POISON_WINDOWS = [("2026-03-15", "2026-03-21"),
                     ("2026-06-11", "2026-06-16")]


def poison_mask(times_ms, windows=None):
    """bool[]: True si el timestamp cae en una ventana envenenada."""
    import numpy as np
    import pandas as pd
    if windows is None:
        windows = ES_POISON_WINDOWS
    t = np.asarray(times_ms, dtype=np.int64)
    out = np.zeros(len(t), dtype=bool)
    for a, b in windows:
        a_ms = int(pd.Timestamp(a).value // 10**6)
        b_ms = int(pd.Timestamp(b).value // 10**6)
        out |= (t >= a_ms) & (t < b_ms)
    return out
