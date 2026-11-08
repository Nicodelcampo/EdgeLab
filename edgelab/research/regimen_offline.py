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


# ----------------------------------------------------------------------------------------------- varias definiciones a la vez
VARIANTES = {   # 2026-11-07 (Nico: «más días o más estabilidad entre días podrían reemplazar a los 3 meses»); se corrigen juntas
    "A_3M_CADA_MES": dict(W=3, min_ops=30, min_dias=20, min_pos=0.50, cada_mes_pos=True, min_dias_mes=4),
    "B_2M_ESTABLE": dict(W=2, min_ops=30, min_dias=20, min_pos=0.55, cada_mes_pos=True, min_dias_mes=6),
    "C_1M_MUY_ESTABLE": dict(W=1, min_ops=25, min_dias=12, min_pos=0.60),
    "D_3M_SIN_CADA_MES": dict(W=3, min_ops=30, min_dias=20, min_pos=0.50),
}


def nulo_signo_multi(diarios, variantes=None, k=3, B=50, seed=0) -> dict:
    """Todas las variantes contra el MISMO nulo de signo por sesión, corregido por haberlas probado juntas: en cada réplica se toma el
    máximo Δ contra azar entre las variantes, y el p de cada variante es la fracción de réplicas cuyo máximo lo iguala o supera."""
    variantes = variantes or VARIANTES
    obs = {n: walk_forward(diarios, k=k, seed=seed, **v) for n, v in variantes.items()}
    dias = np.unique(np.concatenate([d.dias for d in diarios])); rng = np.random.default_rng(seed + 1); maxi = []
    for b in range(B):
        sg = dict(zip(dias.tolist(), rng.choice([-1.0, 1.0], size=len(dias)).tolist()))
        vals = [walk_forward(diarios, k=k, signo=sg, seed=seed + 2 + b, B_azar=50, **v)["delta_azar"] for v in variantes.values()]
        vals = [x for x in vals if np.isfinite(x)]
        if vals: maxi.append(max(vals))
    maxi = np.asarray(maxi)
    out = {}
    for n, o in obs.items():
        p = float((np.sum(maxi >= o["delta_azar"]) + 1) / (len(maxi) + 1)) if len(maxi) and np.isfinite(o["delta_azar"]) else float("nan")
        out[n] = dict(observado={kk: vv for kk, vv in o.items() if kk != "ventanas"}, ventanas=o["ventanas"], p_familia=p)
    return dict(variantes=out, nulo_max_q50_q95=np.quantile(maxi, [.5, .95]).tolist() if len(maxi) else None, B=len(maxi))


# ----------------------------------------------------------------------------------------------- versión en flujo (memoria acotada)
def _cubo_mensual(cubo: Cubo, min_ops: int, G: np.ndarray, dias_glob: np.ndarray):
    """Recorre el cubo mes a mes sin armar la matriz diaria completa. Para cada mes con operaciones devuelve (mes, suma con signo
    (B+1, E), suma de cuadrados (E,), días activos (E,), días positivos con signo (B+1, E), operaciones (E,)). G: signos (B+1, días
    globales); la fila 0 es el observado (todo +1)."""
    idx = [cubo.idx[:, j] for j in range(cubo.idx.shape[1])]
    _, _, Ctot = GM.tensor(cubo.perillas, idx, cubo.net); ev = np.flatnonzero(Ctot.ravel() >= min_ops)
    orden = np.argsort(cubo.ses, kind="stable"); ses_o = cubo.ses[orden]; dias = np.unique(ses_o)
    cortes = np.searchsorted(ses_o, dias, side="left").tolist() + [len(ses_o)]
    gcol = np.searchsorted(dias_glob, dias); meses = _mes(dias)
    for m in np.unique(meses):
        fd = np.flatnonzero(meses == m); S = np.zeros((len(fd), len(ev)), np.float32); C = np.zeros_like(S)   # float32 como el original
        for r, d in enumerate(fd):
            o = orden[cortes[d]:cortes[d + 1]]
            Sd, _, Cd = GM.tensor(cubo.perillas, [ix[o] for ix in idx], cubo.net[o]); S[r] = Sd.ravel()[ev]; C[r] = Cd.ravel()[ev]
        g = G[:, gcol[fd]].astype(np.float32); act = C > 0
        npos = (g > 0).astype(np.float32) @ ((S > 0) & act).astype(np.float32) + (g < 0).astype(np.float32) @ ((S < 0) & act).astype(np.float32)
        yield int(m), g @ S, (S.astype(np.float64) ** 2).sum(0), act.sum(0).astype(np.float64), npos, C.sum(0).astype(np.float64)


def _puntaje_agr(s, sq, nd, npos, ops, min_ops, min_dias, min_pos):
    """`puntaje` a partir de sumas: s, npos (B+1, E); sq, nd, ops (E,). Mismo t del R diario sobre días activos."""
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(nd > 0, s / nd, np.nan)
        var = np.where(nd > 1, (sq - nd * mu ** 2) / (nd - 1), np.nan)
        t = mu / np.sqrt(var / nd)
        pos = np.where(nd > 0, npos / np.maximum(nd, 1), 0.0)
    ok = (ops >= min_ops) & (nd >= min_dias) & (pos >= min_pos) & np.isfinite(t)
    return np.where(ok, t, np.nan)


def buscar_streaming(fuentes, variantes=None, k=3, B=50, seed=0, min_ops_serie=30, B_azar_obs=200, B_azar_nulo=50, max_eleg=256,
                     detalle=False, punto_control=None, log=None):
    """`nulo_signo_multi` en flujo: un cubo por vez y un mes por vez, con el observado y las B réplicas del nulo juntos. `fuentes`:
    lista de (nombre, función que devuelve el Cubo). Elegida y estática son idénticas a `walk_forward` (mismo puntaje y mismos
    signos: la misma semilla que `nulo_signo_multi`); el azar sortea dentro de una muestra uniforme de hasta `max_eleg` celdas
    elegibles por cubo (sigue siendo uniforme). Memoria: la de un mes de un cubo."""
    variantes = variantes or VARIANTES; nv = list(variantes)
    sesiones = []
    for nombre, f in fuentes:
        pd_ = (punto_control / f"{nombre}_sesiones.npy") if punto_control else None
        if pd_ is not None and pd_.exists(): sesiones.append(np.load(pd_)); continue
        x = np.unique(f().ses); sesiones.append(x)
        if pd_ is not None: punto_control.mkdir(parents=True, exist_ok=True); np.save(pd_, x)
    dias_glob = np.unique(np.concatenate(sesiones)); meses_glob = np.unique(_mes(dias_glob))
    rng = np.random.default_rng(seed + 1)
    G = np.ones((B + 1, len(dias_glob)))
    for b in range(B): G[b + 1] = rng.choice([-1.0, 1.0], size=len(dias_glob))
    reg = {(v, h): dict(cand=[], estat=[], eleg=[]) for v in nv for h in range(len(meses_glob))}   # por cubo, arrays (B+1,)
    import hashlib, pickle, time as _t, zlib as _z
    huella = hashlib.sha256(repr((sorted(variantes.items()), k, B, seed, min_ops_serie, max_eleg, len(dias_glob))).encode()).hexdigest()[:12]
    for nc, (nombre, f) in enumerate(fuentes):
        pc = (punto_control / f"{nombre}_{huella}.pkl") if punto_control else None
        if pc is not None and pc.exists():                       # 2026-11-08: un reinicio del contenedor no pierde los cubos hechos
            for key, R in pickle.loads(pc.read_bytes()).items():
                for c in ("cand", "estat", "eleg"): reg[key][c] += R[c]
            continue
        t0 = _t.time(); rs = np.random.default_rng([seed + 7, _z.crc32(nombre.encode())])   # independiente del orden de los cubos
        propio = {key: dict(cand=[], estat=[], eleg=[]) for key in reg}
        cubo = f(); ventana = []; acum = None
        for m, s, sq, nd, npos, ops in _cubo_mensual(cubo, min_ops_serie, G, dias_glob):
            h = int(np.searchsorted(meses_glob, m))
            for v in nv:
                p = variantes[v]; W = p["W"]
                win = [x for x in ventana if x[0] in set(meses_glob[max(0, h - W):h].tolist())]
                if not win or h < W: continue
                ws = sum(x[1] for x in win); wsq = sum(x[2] for x in win); wnd = sum(x[3] for x in win)
                wnp = sum(x[4] for x in win); wop = sum(x[5] for x in win)
                sc = _puntaje_agr(ws, wsq, wnd, wnp, wop, p["min_ops"], p["min_dias"], p.get("min_pos", 0.0))
                if p.get("cada_mes_pos"):
                    okm = np.ones_like(sc, bool)
                    for mw in meses_glob[h - W:h]:
                        x = next((y for y in win if y[0] == mw), None)
                        okm &= (x[1] > 0) & (x[3] >= p.get("min_dias_mes", 4)) if x is not None else False
                    sc = np.where(okm, sc, np.nan)
                st = (_puntaje_agr(acum[0], acum[1], acum[2], acum[3], acum[4], p["min_ops"], p["min_dias"], p.get("min_pos", 0.0))
                      if acum is not None else np.full_like(sc, np.nan))
                R = propio[(v, h)]
                for b in range(B + 1):
                    fila = sc[b]
                    if not np.isfinite(fila).any(): R["cand"].append(None); R["estat"].append(None); R["eleg"].append(None); continue
                    j = int(np.nanargmax(fila)); cand = (fila[j], s[b, j], ops[j])
                    fs = st[b]; est = None
                    if np.isfinite(fs).any(): js = int(np.nanargmax(fs)); est = (fs[js], s[b, js], ops[js])
                    el = np.flatnonzero(np.isfinite(fila))
                    if len(el) > max_eleg: el = rs.choice(el, size=max_eleg, replace=False)
                    R["cand"].append((b, cand)); R["estat"].append((b, est)); R["eleg"].append((b, s[b, el], ops[el]))
            ventana = (ventana + [(m, s, sq, nd, npos, ops)])[-3:]
            acum = (s, sq, nd, npos, ops) if acum is None else tuple(a + x for a, x in zip(acum, (s, sq, nd, npos, ops)))
        del cubo
        for key, R in propio.items():
            for c in ("cand", "estat", "eleg"): reg[key][c] += R[c]
        if pc is not None: pc.write_bytes(pickle.dumps(propio))
        if log: log(f"cubo {nc + 1}/{len(fuentes)} {nombre} {_t.time() - t0:.0f}s")
    obs, maxi = {}, []
    filas_b = {v: {b: [] for b in range(B + 1)} for v in nv}
    for (v, h), R in sorted(reg.items(), key=lambda x: x[0][1]):
        for b in range(B + 1):
            cand = [c[1] for c in R["cand"] if c is not None and c[0] == b]
            if len(cand) < k: continue
            est = [e[1] for e in R["estat"] if e is not None and e[0] == b and e[1] is not None]
            eleg = [(e[1], e[2]) for e in R["eleg"] if e is not None and e[0] == b]
            def _ro(lst):
                top = sorted(lst, key=lambda x: -x[0])[:k]; c = sum(x[2] for x in top)
                return sum(x[1] for x in top) / c if c > 0 else np.nan
            ra = np.random.default_rng(seed + 2 + b + 1000 * h); az = []
            for _ in range(B_azar_obs if b == 0 else B_azar_nulo):
                pick = ra.choice(len(eleg), size=k, replace=False); ss = cc = 0.0
                for i in pick:
                    sH, cH = eleg[i]; j = ra.integers(len(sH)); ss += sH[j]; cc += cH[j]
                az.append(ss / cc if cc > 0 else np.nan)
            filas_b[v][b].append(dict(mes=int(meses_glob[h]), elegida=_ro(cand), azar=float(np.nanmean(az)),
                                      estatica=_ro(est) if len(est) >= k else np.nan, cubos=len(cand)))
    for b in range(1, B + 1):
        vals = [_resumen(filas_b[v][b])["delta_azar"] for v in nv]; vals = [x for x in vals if np.isfinite(x)]
        if vals: maxi.append(max(vals))
    maxi = np.asarray(maxi); out = {}
    for v in nv:
        o = _resumen(filas_b[v][0])
        p = float((np.sum(maxi >= o["delta_azar"]) + 1) / (len(maxi) + 1)) if len(maxi) and np.isfinite(o["delta_azar"]) else float("nan")
        out[v] = dict(observado=dict(W=variantes[v]["W"], k=k, **o), ventanas=filas_b[v][0], p_familia=p)
    res = dict(variantes=out, nulo_max_q50_q95=np.quantile(maxi, [.5, .95]).tolist() if len(maxi) else None, B=len(maxi),
               cubos=len(fuentes), dias=len(dias_glob))
    if detalle: res["filas"] = filas_b; res["signos"] = {b: dict(zip(dias_glob.tolist(), G[b].tolist())) for b in range(B + 1)}
    return res
