"""API de features para fuerza bruta / vectorbt (F8).

EdgeLab consume el store por identidad y materializa features alineadas as-of a
cualquier serie de barras, SIN importar ningún módulo de kernel (los kernels solo
producen y publican; el consumo lee zonas verificadas). Todo point-in-time: en la
barra t solo se ven zonas con `created_ms <= t` (cero look-ahead).

- `get_zones_df(...)`      -> DataFrame de zonas del store (por identidad/estado).
- `resolve_config_id(...)` -> config_id canónico desde (indicador, params, bars).
- `materialize_features(zones_df, index_ms, price, features=[...])` -> columnas
  as-of alineadas a la serie de barras.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import store
from . import identity

DEFAULT_FEATURES = ("inside_zone", "distance_to_nearest_zone",
                    "active_zone_count", "zone_age", "nearest_zone_side")


def resolve_config_id(indicator, params=None, bar_key="time_1", chart_tz="UTC"):
    """config_id canónico de una configuración (mismo que usa el store)."""
    kid = identity.kernel_id(indicator)
    return identity.config_id(indicator, params or {}, bar_key, chart_tz, kid)


def get_zone_rows(root, *, indicator=None, config_id=None, contract=None,
                  instrument=None, bar_key=None, state=None, integrity_state=None,
                  parity_state=None, created_after_ms=None, created_before_ms=None,
                  params=None, chart_tz="UTC"):
    """Filas crudas de zonas del store (dicts), por identidad/estado. Si se dan
    `params` (y no `config_id`), resuelve el config_id canónico."""
    if config_id is None and params is not None and indicator is not None:
        config_id = resolve_config_id(indicator, params, bar_key or "time_1", chart_tz)
    return store.get_zones(
        root, indicator=indicator, config_id=config_id, contract=contract,
        instrument=instrument, bar_key=bar_key, state=state,
        integrity_state=integrity_state, parity_state=parity_state,
        created_after_ms=created_after_ms, created_before_ms=created_before_ms)


def get_zones_df(root, **kw):
    """Igual que get_zone_rows pero como DataFrame (para consumo/vectorbt). El
    digest de integridad se verifica sobre las filas crudas (get_zone_rows +
    store.zone_rows_digest == zone_digest del manifest), no sobre el DataFrame."""
    rows = get_zone_rows(root, **kw)
    cols = list(store._ZONE_COLS)
    if not rows:
        return pd.DataFrame({c: pd.Series(dtype="object") for c in cols})
    return pd.DataFrame(rows, columns=cols)


def materialize_features(zones_df, index_ms, price=None, features=DEFAULT_FEATURES,
                         tick_size=None):
    """Alinea zonas a una serie de barras (as-of, sin look-ahead).

    zones_df: DataFrame con created_ms, ended_ms, top, bottom, side.
    index_ms: array de timestamps de barra (ms), creciente.
    price: array del mismo largo (p.ej. close) — requerido por las features que
           dependen de precio (inside/distance/nearest_side/zone_age del cercano).
    Devuelve un DataFrame indexado por index_ms con las columnas pedidas.

    Zona ACTIVA en t: created_ms <= t AND (ended_ms es NaN OR ended_ms > t).
    """
    index_ms = np.asarray(index_ms, dtype=np.int64)
    n = len(index_ms)
    price = None if price is None else np.asarray(price, dtype=np.float64)
    need_price = any(f in features for f in
                     ("inside_zone", "distance_to_nearest_zone",
                      "nearest_zone_side", "zone_age"))
    if need_price and price is None:
        raise ValueError("estas features requieren `price` alineado a index_ms: "
                         + ", ".join(f for f in features if f != "active_zone_count"))

    z = zones_df
    cm = z["created_ms"].to_numpy(dtype=np.float64) if len(z) else np.empty(0)
    em = z["ended_ms"].to_numpy(dtype=np.float64) if len(z) else np.empty(0)
    em = np.where(np.isnan(em), np.inf, em)      # None/NaN = sigue activa
    top = z["top"].to_numpy(dtype=np.float64) if len(z) else np.empty(0)
    bot = z["bottom"].to_numpy(dtype=np.float64) if len(z) else np.empty(0)
    side = z["side"].to_numpy() if len(z) else np.empty(0, dtype=object)

    out = {f: np.zeros(n, dtype=np.float64) for f in features if f != "nearest_zone_side"}
    if "nearest_zone_side" in features:
        side_out = np.array([None] * n, dtype=object)
    if "inside_zone" in out:
        out["inside_zone"][:] = 0.0
    for f in ("distance_to_nearest_zone", "zone_age"):
        if f in out:
            out[f][:] = np.nan

    for i in range(n):
        t = index_ms[i]
        active = (cm <= t) & (em > t)
        if "active_zone_count" in out:
            out["active_zone_count"][i] = int(active.sum())
        if not need_price or not active.any():
            continue
        p = price[i]
        at, ab, asd, acm = top[active], bot[active], side[active], cm[active]
        inside = (p >= ab) & (p <= at)
        # distancia: 0 si adentro, si no la menor separación a un borde
        d = np.where(inside, 0.0, np.minimum(np.abs(p - at), np.abs(p - ab)))
        k = int(np.argmin(d))
        if "inside_zone" in out:
            out["inside_zone"][i] = 1.0 if inside.any() else 0.0
        if "distance_to_nearest_zone" in out:
            out["distance_to_nearest_zone"][i] = float(d[k])
        if "zone_age" in out:
            out["zone_age"][i] = float(t - acm[k])
        if "nearest_zone_side" in features:
            side_out[i] = asd[k]

    data = {}
    for f in features:
        if f == "nearest_zone_side":
            data[f] = side_out
        else:
            data[f] = out[f]
    df = pd.DataFrame(data, index=pd.Index(index_ms, name="bar_ms"))
    if "active_zone_count" in df:
        df["active_zone_count"] = df["active_zone_count"].astype(np.int64)
    if "inside_zone" in df:
        df["inside_zone"] = df["inside_zone"].astype(bool)
    return df
