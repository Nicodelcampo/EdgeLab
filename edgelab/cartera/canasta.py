"""Seguimiento y promoción POR CANASTA (2026-11-02, decisión de Nico: «agregá el seguimiento por canasta y la promoción»).

Por qué: cada estrategia sola tiene potencia de 0,04–0,17 y su promoción individual puede tardar años. La canasta (todas las fichas
de la cartera, riesgo igual) es una sola serie y junta potencia si las estrategias no están perfectamente correlacionadas.

Serie: por sesión, la media de (resultado de la sesión de cada ficha miembro / su desvío de desarrollo), en unidades de riesgo.
- Una ficha ENTRA a la canasta cuando la evalúan por primera vez, desde la sesión siguiente a la última ya contada
  (`canasta_desde`): nunca se reescribe una sesión que la canasta ya miró. Una ficha que no se puede evaluar (sin datos o sin
  almacén de zonas) no entra.
- Miembro en la sesión s: entró con `canasta_desde` <= s y está activa (o se retiró después de s). Sin operación esa sesión aporta 0.
- Sólo entran sesiones evaluadas por TODOS los miembros activos (hasta la menor `evaluada_hasta`) y con al menos una operación.
- Composición decidida antes de cada sesión (altas y retiros previos): el e-proceso sigue siendo válido mirando todos los días (Ville).
Cotas declaradas antes de mirar: `mult_cota` × el peor y el mejor valor de la MISMA serie armada con las operaciones de desarrollo
(`ops_desarrollo`) de las fichas. Se fijan la primera vez y sólo se ensanchan si entra una ficha nueva, con registro en la bitácora.
Efecto útil: la mediana de mu_util / sd de las fichas.
Promoción: e-proceso de edge >= 1/alfa_real con al menos `min_ops_real` sesiones → todas las fichas ACTIVAS en PAPEL pasan a REAL
("promovida por canasta"). Futilidad de la canasta: alerta, no retira (cada ficha conserva su propia regla de retiro).
REAL no habilita dinero: las cuentas reales las habilita una persona.
"""
from __future__ import annotations

import numpy as np

from edgelab.funnel.secuencial import MonitorCandidato


def _por_sesion(ops) -> dict:
    out = {}
    for s, x in ops: out[int(s)] = out.get(int(s), 0.0) + float(x)
    return out


def serie(fichas, desarrollo: bool = False) -> list:
    """[(ses, valor_en_riesgo)]. `desarrollo=True`: con `ops_desarrollo` (para las cotas), todas las fichas miembro siempre."""
    fs = [f for f in fichas if f.sd_desarrollo and f.sd_desarrollo > 0]
    if not fs: return []
    por = {f.id: _por_sesion(f.ops_desarrollo if desarrollo else f.ops) for f in fs}
    if desarrollo:
        sesiones = sorted({s for p in por.values() for s in p}); miembros = lambda s: fs
    else:
        fs = [f for f in fs if f.canasta_desde]
        act = [f for f in fs if f.estado == "ACTIVA"]
        tope = min((int(f.evaluada_hasta or 0) for f in act), default=0)
        sesiones = sorted({s for f in fs for s in por[f.id] if f.canasta_desde <= s <= tope})
        miembros = lambda s: [f for f in fs if int(f.canasta_desde) <= s and (f.estado == "ACTIVA" or s <= f.ultima_ses())]
    out = []
    for s in sesiones:
        m = miembros(s)
        if not m or not any(s in por[f.id] for f in m): continue
        out.append((s, float(np.mean([por[f.id].get(s, 0.0) / f.sd_desarrollo for f in m]))))
    return out


def cotas(fichas, mult: float) -> tuple:
    dev = [x for _, x in serie(fichas, desarrollo=True)]
    if not dev: raise ValueError("canasta sin operaciones de desarrollo para declarar las cotas")
    return (mult * min(min(dev), -1e-6), mult * max(max(dev), 1e-6))


def seguir(cartera, cfg: dict) -> dict:
    """Actualiza el estado de la canasta (guardado en la bitácora de la cartera) y promueve si corresponde."""
    c = cfg.get("canasta") or {}
    if not c.get("activa", False): return dict(activa=False)
    fichas = [f for f in cartera.fichas.values()]
    if not any(f.estado == "ACTIVA" for f in fichas): return dict(activa=True, estado="SIN_FICHAS")
    est = cartera.canasta = getattr(cartera, "canasta", None) or {}
    for f in fichas:                                                       # entrada: desde la sesión siguiente a la última contada
        if f.estado == "ACTIVA" and not f.canasta_desde and f.evaluada_hasta:
            f.canasta_desde = max(int(f.desde), int(est.get("ultima", 0)) + 1); cartera._log("ENTRA_CANASTA", f.id, desde=f.canasta_desde)
    lo, hi = cotas(fichas, float(c.get("mult_cota", 3.0)))
    if "cotas" not in est or lo < est["cotas"][0] or hi > est["cotas"][1]:
        nuevas = [min(lo, est.get("cotas", [lo, hi])[0]), max(hi, est.get("cotas", [lo, hi])[1])]
        cartera._log("COTAS_CANASTA", "canasta", antes=est.get("cotas"), despues=nuevas); est["cotas"] = nuevas
    mus = [f.mu_util / f.sd_desarrollo for f in fichas if f.sd_desarrollo]
    mu = float(np.median(mus)); r = cartera.reglas
    m = MonitorCandidato(piso=est["cotas"][0], techo=est["cotas"][1], mu_util=mu, alfa=r["alfa_real"], alfa_futilidad=r["alfa_futilidad"])
    xs = serie(fichas)
    try: st = m.agregar([x for _, x in xs]) if xs else m.estado()
    except ValueError as ex:
        est.update(estado="LIMITE_VIOLADO", motivo=str(ex)); cartera.guardar(); return dict(activa=True, **est)
    if xs: est["ultima"] = int(xs[-1][0])
    est.update(estado=st["estado"], n=st["n"], media=st["media"], e_edge=st["e_edge"], e_futilidad=st["e_futilidad"], mu_util=mu,
               miembros=sorted(f.id for f in fichas if f.estado == "ACTIVA" and f.canasta_desde))
    promovidas = []
    if st["estado"] == "EDGE_CONFIRMADO" and st["n"] >= r["min_ops_real"]:
        for f in fichas:
            if f.estado == "ACTIVA" and f.nivel == "PAPEL":
                ok, por = cartera.puede_promover(f.id)                      # 2026-11-02 (Nico): además R forward > 0 por ficha
                if ok: f.nivel = "REAL"; promovidas.append(f.id); cartera._log("PROMOCION_CANASTA", f.id, e=st["e_edge"], n=st["n"], r=por)
                else: cartera._log("PROMOCION_RETENIDA", f.id, e=st["e_edge"], n=st["n"], motivo=por)
    est["promovidas_hoy"] = promovidas
    cartera.guardar()
    return dict(activa=True, **est)
