"""Búsqueda de regímenes OFFLINE sobre cubos de operaciones (2026-11-07, pedido de Nico: «infraestructura más rápida y eficiente para
encontrar regímenes que, aunque tengan pocos meses, tengan muchas operaciones y estabilidad entre días, lo que les da potencia»).

Un CUBO es la base de operaciones de una campaña (etapa `CUBO` del embudo: una corrida de grilla sobre DESC + réplica): por operación,
el nivel de cada perilla, la ejecución, la sesión y el R neto. Con eso, cualquier regla de selección de régimen se prueba en segundos,
sin volver a Kaggle:

  1. `series_diarias`: para cada celda evaluable (>= `min_ops` operaciones en todo el cubo), la suma diaria de R y de operaciones
     (matrices sesión × celda; las celdas son las de la grilla, con sus modos ge / eq_any / extremos).
  2. `walk_forward`: en cada mes H, puntúa con los W meses previos (sólo sesiones cerradas antes de H) y elige UNA celda por cubo
     (familia × instrumento); opera las k mejores en H. Puntaje = estabilidad entre días: t del R diario (unidad = la sesión, no la
     operación; las operaciones del mismo día están correlacionadas) con pisos de operaciones y de días en W.
  3. Controles con el mismo k y la misma deduplicación: AZAR (celdas elegibles sorteadas) y ESTÁTICA (mismo puntaje con TODO el
     histórico previo a H; en H-REG-1 la calidad estática le ganó a la racha: `docs/research/regimen_corto_20261106/`).
  4. Nulo: volteo de signo por SESIÓN (el mismo para todas las celdas y cubos de ese día, conserva la correlación cruzada) y se repite
     toda la selección. p = fracción de réplicas con Δ contra azar >= el observado.
Elegir entre miles de celdas por cubo infla cualquier puntaje: el nulo repite esa misma elección, así que la corrección va incluida.
"""
from __future__ import annotations

import base64
import io
import zlib
from dataclasses import dataclass

import numpy as np

from edgelab.research import grilla_masiva as GM


# ----------------------------------------------------------------------------------------------- cubo (codificación)
def codificar(cx) -> dict:
    """Base de operaciones de `grilla_generica.correr(modo="MARG")` → dict JSON (npz comprimido en base64)."""
    net = np.asarray(cx["net"], float); ok = np.isfinite(net)
    I = np.stack([np.asarray(ix)[ok] for ix in cx["indices"]], 1)
    buf = io.BytesIO()
    np.savez_compressed(buf, idx=I.astype(np.int16), ses=np.asarray(cx["ses"])[ok].astype(np.int32), net=net[ok].astype(np.float32))
    P = [(p.nombre, int(p.niveles), p.modo) for p in cx["perillas"]]
    return dict(perillas=P, n=int(ok.sum()), npz_b64=base64.b64encode(buf.getvalue()).decode())


@dataclass
class Cubo:
    nombre: str
    perillas: list            # [GM.Perilla]
    idx: np.ndarray           # (n_ops, n_ejes) int
    ses: np.ndarray           # (n_ops,) yyyymmdd
    net: np.ndarray           # (n_ops,) R neto


def decodificar(d: dict, nombre: str) -> Cubo:
    z = np.load(io.BytesIO(base64.b64decode(d["npz_b64"])))
    P = [GM.Perilla(n, k, m) for n, k, m in d["perillas"]]
    return Cubo(nombre, P, z["idx"].astype(np.int64), z["ses"].astype(np.int64), z["net"].astype(float))


# ----------------------------------------------------------------------------------------------- series diarias por celda
@dataclass
class Diario:
    nombre: str
    dias: np.ndarray          # (D,) sesiones ordenadas
    celdas: np.ndarray        # (E,) índice plano de la celda en la grilla acumulada
    S: np.ndarray             # (D, E) suma de R del día
    C: np.ndarray             # (D, E) operaciones del día
    forma: tuple


def series_diarias(cubo: Cubo, min_ops: int = 30) -> Diario:
    idx = [cubo.idx[:, j] for j in range(cubo.idx.shape[1])]
    _, _, Ctot = GM.tensor(cubo.perillas, idx, cubo.net)
    forma = Ctot.shape; ev = np.flatnonzero(Ctot.ravel() >= min_ops)
    dias = np.unique(cubo.ses); S = np.zeros((len(dias), len(ev)), np.float32); C = np.zeros_like(S)
    orden = np.argsort(cubo.ses, kind="stable"); ses_o = cubo.ses[orden]
    cortes = np.searchsorted(ses_o, dias, side="left").tolist() + [len(ses_o)]
    for d in range(len(dias)):
        o = orden[cortes[d]:cortes[d + 1]]
        Sd, _, Cd = GM.tensor(cubo.perillas, [ix[o] for ix in idx], cubo.net[o])
        S[d] = Sd.ravel()[ev]; C[d] = Cd.ravel()[ev]
    return Diario(cubo.nombre, dias, ev, S, C, forma)


def celda_de(diario: Diario, j: int) -> list:
    return [int(x) for x in np.unravel_index(int(diario.celdas[j]), diario.forma)]


# ----------------------------------------------------------------------------------------------- puntaje y walk-forward
def puntaje(S, C, filas, min_ops=20, min_dias=10, min_pos=0.0):
    """t del R diario (suma del día) en las filas dadas, sólo días con operaciones. NaN donde no es elegible."""
    s = S[filas]; c = C[filas]; act = c > 0
    nd = act.sum(0); n_ops = c.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(nd > 0, s.sum(0) / nd, np.nan)
        var = np.where(nd > 1, ((s - mu) ** 2 * act).sum(0) / (nd - 1), np.nan)
        t = mu / np.sqrt(var / nd)
        pos = np.where(nd > 0, ((s > 0) & act).sum(0) / nd, 0.0)
    ok = (n_ops >= min_ops) & (nd >= min_dias) & (pos >= min_pos) & np.isfinite(t)
    return np.where(ok, t, np.nan)


def _mes(d): return np.asarray(d) // 100


def meses_positivos(S, C, dias, meses_W, min_dias_mes=4):
    """Máscara de celdas con R > 0 y al menos `min_dias_mes` días con operaciones en CADA mes de W (pedido de Nico, 07/11)."""
    ok = np.ones(S.shape[1], bool); mm = _mes(dias)
    for m in meses_W:
        f = mm == m; s = S[f].sum(0); nd = (C[f] > 0).sum(0)
        ok &= (s > 0) & (nd >= min_dias_mes)
    return ok


def walk_forward(diarios, W=3, k=3, min_ops=20, min_dias=10, min_pos=0.0, B_azar=200, signo=None, seed=0,
                 cada_mes_pos=False, min_dias_mes=4) -> dict:
    """`diarios`: lista de Diario (uno por cubo). `signo`: dict sesión → ±1 (nulo). Devuelve por mes H: R/op elegida, azar y estática."""
    rng = np.random.default_rng(seed)
    meses = np.unique(np.concatenate([_mes(d.dias) for d in diarios]))
    Ss = []
    for d in diarios:
        if signo is None: Ss.append(d.S)
        else: Ss.append(d.S * np.array([signo.get(int(x), 1.0) for x in d.dias], np.float32)[:, None])
    filas_out = []
    for h in range(W, len(meses)):
        mH, mW = meses[h], meses[h - W:h]
        cand, estat, elegibles = [], [], []
        for d, S in zip(diarios, Ss):
            mm = _mes(d.dias); fW = np.flatnonzero(np.isin(mm, mW)); fH = np.flatnonzero(mm == mH); fP = np.flatnonzero(mm < mH)
            if not len(fW) or not len(fH): continue
            sc = puntaje(S, d.C, fW, min_ops, min_dias, min_pos)
            if cada_mes_pos: sc = np.where(meses_positivos(S, d.C, d.dias, mW, min_dias_mes), sc, np.nan)
            if not np.isfinite(sc).any(): continue
            sH, cH = S[fH].sum(0), d.C[fH].sum(0)
            j = int(np.nanargmax(sc)); cand.append((sc[j], sH[j], cH[j]))
            st = puntaje(S, d.C, fP, min_ops, min_dias, min_pos)
            if np.isfinite(st).any(): js = int(np.nanargmax(st)); estat.append((st[js], sH[js], cH[js]))
            el = np.flatnonzero(np.isfinite(sc)); elegibles.append((sH[el], cH[el]))
        if len(cand) < k: continue
        def _ro(lst):
            top = sorted(lst, key=lambda x: -x[0])[:k]; c = sum(x[2] for x in top)
            return sum(x[1] for x in top) / c if c > 0 else np.nan
        az = []
        for _ in range(B_azar):
            pick = rng.choice(len(elegibles), size=k, replace=False); s = c = 0.0
            for i in pick:
                sH, cH = elegibles[i]; j = rng.integers(len(sH)); s += sH[j]; c += cH[j]
            az.append(s / c if c > 0 else np.nan)
        filas_out.append(dict(mes=int(mH), elegida=_ro(cand), azar=float(np.nanmean(az)), estatica=_ro(estat) if len(estat) >= k else np.nan,
                              cubos=len(cand)))
    return dict(W=W, k=k, ventanas=filas_out, **_resumen(filas_out))


def _resumen(filas):
    def _t(x):
        x = np.asarray([v for v in x if np.isfinite(v)], float)
        return (float(x.mean()), float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else float("nan"), len(x))
    da = _t([f["elegida"] - f["azar"] for f in filas]); de = _t([f["elegida"] - f["estatica"] for f in filas])
    return dict(delta_azar=da[0], t_azar=da[1], delta_estatica=de[0], t_estatica=de[1], n_ventanas=da[2])


def nulo_signo(diarios, B=50, seed=0, **kw) -> dict:
    """Repite toda la selección con el signo de cada sesión volteado (mismo signo para todos los cubos ese día)."""
    obs = walk_forward(diarios, seed=seed, **kw)
    dias = np.unique(np.concatenate([d.dias for d in diarios])); rng = np.random.default_rng(seed + 1); nul = []
    for b in range(B):
        sg = dict(zip(dias.tolist(), rng.choice([-1.0, 1.0], size=len(dias)).tolist()))
        nul.append(walk_forward(diarios, signo=sg, seed=seed + 2 + b, B_azar=50, **kw)["delta_azar"])
    nul = np.asarray([x for x in nul if np.isfinite(x)])
    p = float((np.sum(nul >= obs["delta_azar"]) + 1) / (len(nul) + 1)) if len(nul) else float("nan")
    return dict(observado=obs, p_nulo=p, nulo_q05_q50_q95=np.quantile(nul, [.05, .5, .95]).tolist() if len(nul) else None)
