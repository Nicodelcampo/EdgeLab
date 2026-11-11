"""Analizador genérico de tablas de eventos (2026-11-11, AUTOMATIZACION_PROCESOS_20261111 F1–F4, C1).

`explorar(mod, T)`: la búsqueda completa sobre una tabla de DESARROLLO (definición × ejecución × filtro) por fuente y período, en R
neto con la fricción de `edgelab/costos.py`, con la guarda de fricción (≤ 0,08 R), el control declarado, la estabilidad de las de
arriba y el NULO DE LA BÚSQUEDA (mejor t por azar con todas las celdas, invirtiendo el signo de cada sesión en todas a la vez).
Nada de lo que sale de acá confirma: ordena qué congelar.

`congelar(...)` escribe las hipótesis elegidas (≤ K_MAX) con su hash ANTES de generar la tabla de confirmación; `confirmar(...)` las
prueba UNA vez sobre esa tabla: R neto por sesión, p por inversión de signo, 5 sub-bloques, BH q 0,10 sobre las k, MDE y un
veredicto por regla fija (CONFIRMADA / EN_CONTRA / NO_CONCLUYENTE / SIN_POTENCIA). El informe se genera del JSON, sin texto libre
en el veredicto.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.costos import friccion_rt_puntos
from edgelab.research import banco_eventos as BE
from edgelab.research import tablas as TB

FRICCION_MAX_R = 0.08
K_MAX = 10
Q_BH = 0.10


def fisher(ps) -> float:
    """Combinación de Fisher (cola chi² de 2k grados de libertad en forma cerrada; sin scipy)."""
    import math
    ps = [min(max(float(p), 1e-12), 1.0) for p in ps]; h = -sum(math.log(p) for p in ps)
    return float(math.exp(-h) * sum(h ** i / math.factorial(i) for i in range(len(ps))))


def neto(mod, T: pd.DataFrame, ej: str):
    """R neto y fricción en R de la ejecución `ej` (nombre de ejecucion.nombre) para cada fila."""
    fr = np.array([friccion_rt_puntos(TB.fuente_costo(mod, f)) for f in T.fuente], float) if "fuente" in T else np.nan
    k = T[f"k_{ej}"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return T[f"r_{ej}"].to_numpy(float) - fr / k, fr / k


def _ses_sum(y, ses) -> pd.Series:
    m = np.isfinite(y)
    return pd.Series(y[m]).groupby(np.asarray(ses)[m]).sum()


def _t(s: pd.Series) -> float:
    d = float((s ** 2).sum()); return float(s.sum() / np.sqrt(d)) if d > 0 else 0.0


def celdas(mod, T: pd.DataFrame):
    """Itera (definición, ejecución, filtro, máscara de filas, R neto, fricción en R)."""
    from edgelab.research.ejecucion import nombre
    defs = list(getattr(mod, "DEFINICIONES", []) or []) or [None]
    fil = {"todos": None, **(getattr(mod, "FILTROS", {}) or {})}
    for dfn in defs:
        m0 = T[dfn].astype(bool).to_numpy() if dfn else np.ones(len(T), bool)
        for s in mod.EJECUCIONES:
            ej = nombre(s); y, cr = neto(mod, T, ej)
            for fn, f in fil.items():
                m = m0 & (TB.filtro(T, f) if f else True)
                yield dfn, ej, fn, m, np.where(m, y, np.nan), cr


def nulo_busqueda(sumas, n_perm=300, seed=17) -> dict:
    if not sumas: return {}
    M = pd.concat(sumas, axis=1).fillna(0.0).to_numpy().T
    den = np.sqrt((M ** 2).sum(1)); den[den == 0] = np.inf; rng = np.random.default_rng(seed)
    mx = np.array([np.max((M @ rng.choice([-1.0, 1.0], M.shape[1])) / den) for _ in range(n_perm)])
    return dict(celdas=int(M.shape[0]), t_max_p50=float(np.median(mx)), t_max_p95=float(np.percentile(mx, 95)))


def explorar(mod, T: pd.DataFrame, top: int = 25, n_min: int = 30) -> dict:
    """Búsqueda completa por corte (todos, y cada fuente × período). Devuelve dict serializable."""
    mod = TB.cargar(mod); T = T.copy(); T["periodo"] = TB.periodo(mod, T.ses)
    if "fuente" not in T: T["fuente"] = "?"
    cortes = [("todos", T)] + [(f"{f}/{p}", g) for (f, p), g in T.groupby(["fuente", "periodo"])]
    out = dict(modulo=mod.__name__, eventos=int(len(T)), cortes={})
    for clave, S in cortes:
        S = S.reset_index(drop=True); filas, sumas = [], []
        for dfn, ej, fn, m, y, cr in celdas(mod, S):
            n = int(np.isfinite(y).sum())
            if n < 20: continue
            s = _ses_sum(y, S.ses.to_numpy()); r = S[f"r_{ej}"].to_numpy(float)
            filas.append(dict(defn=dfn, ejec=ej, filtro=fn, n=n, sesiones=int(len(s)), r_bruto=float(np.nanmean(np.where(m, r, np.nan))),
                              r_neto=float(np.nanmean(y)), t=_t(s), fric_r=float(np.nanmedian(np.where(m, cr, np.nan)))))
            if n >= n_min: sumas.append(s)
        P = pd.DataFrame(filas)
        if not len(P): out["cortes"][clave] = dict(celdas=0); continue
        nu = nulo_busqueda(sumas)
        P["elegible"] = (P.n >= n_min) & (P.fric_r <= FRICCION_MAX_R)
        arriba = P[P.elegible].sort_values("t", ascending=False).head(top).copy()
        est = []
        for r in arriba.itertuples():
            S2 = S if r.defn is None else S
            y = next(yy for d, e, f, _, yy, _ in celdas(mod, S2) if d == r.defn and e == r.ejec and f == r.filtro)
            m = np.isfinite(y); e = BE.estabilidad(y[m], S2.ses.to_numpy()[m], BE._sesiones(S2[m].assign(inst=S2.fuente[m], fecha=S2.ses[m])), n_perm=2000)
            est.append((e.get("bloques_pos"), e.get("p_media")))
        arriba["bloques"] = [x[0] for x in est]; arriba["p"] = [x[1] for x in est]
        arriba["sobre_nulo_p95"] = arriba.t > nu.get("t_max_p95", np.inf)
        ctrl = []
        for dfn, cdef in (getattr(mod, "CONTROL", {}) or {}).items():                  # real − control con la misma ejecución
            for ej in P.ejec.unique():
                a = P[(P.defn == dfn) & (P.ejec == ej) & (P.filtro == "todos")]; b = P[(P.defn == cdef) & (P.ejec == ej) & (P.filtro == "todos")]
                if len(a) and len(b): ctrl.append(dict(defn=dfn, control=cdef, ejec=ej, real=float(a.r_neto.iloc[0]), ctrl=float(b.r_neto.iloc[0]),
                                                       diferencia=float(a.r_neto.iloc[0] - b.r_neto.iloc[0])))
        out["cortes"][clave] = dict(eventos=int(len(S)), celdas=int(len(P)), nulo_busqueda=nu, arriba=arriba.to_dict("records"),
                                    control=ctrl, todas=P.to_dict("records"))
    return out


def informe_exploracion(res: dict) -> str:
    md = [f"# Exploración — {res['modulo']} (NO confirma nada)", "",
          "Generado por `edgelab/research/analizar_tabla.py`. Una celda por debajo del percentil 95 del nulo de la búsqueda no se distingue",
          f"del azar; las de fricción > {FRICCION_MAX_R} R no son elegibles. Lo que se congele se prueba en datos no mirados (`congelar`).", ""]
    for clave, c in res["cortes"].items():
        nu = c.get("nulo_busqueda") or {}
        md += [f"## {clave} — {c.get('eventos', 0)} eventos, {c.get('celdas', 0)} celdas", "",
               f"Nulo de la búsqueda: mejor t por azar mediana {nu.get('t_max_p50', float('nan')):.2f}, p95 {nu.get('t_max_p95', float('nan')):.2f}.", "",
               "| definición | ejecución | filtro | n | R bruto | R neto | t | bloques + | p | fricción R | ¿sobre el nulo? |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        md += [f"| {r['defn']} | {r['ejec']} | {r['filtro']} | {r['n']} | {r['r_bruto']:+.3f} | {r['r_neto']:+.3f} | {r['t']:+.2f} | {r['bloques']} | "
               f"{r['p']:.3f} | {r['fric_r']:.3f} | {'sí' if r['sobre_nulo_p95'] else 'no'} |" for r in c.get("arriba", [])]
        if c.get("control"):
            mejores = sorted(c["control"], key=lambda x: -x["diferencia"])[:5]
            md += ["", "Real − control (misma ejecución, R neto): " + "; ".join(f"{x['defn']} vs {x['control']} {x['ejec']}: {x['diferencia']:+.3f}" for x in mejores)]
        md += [""]
    return "\n".join(md) + "\n"


# ----------------------------------------------------------------------------------------------- congelar y confirmar
def congelar(mod, hipotesis: list, familia: str, carpeta: Path, ventana_confirmacion: dict, registro=None) -> Path:
    """Escribe CONGELADAS_<ts>.json con las hipótesis (defn, ejec, filtro; signo siempre > 0 en R neto), su hash, la ventana de
    confirmación declarada y registra k pruebas en el contador global. Falla si k > K_MAX o una hipótesis no existe en el módulo."""
    from edgelab.research.ejecucion import nombre
    mod = TB.cargar(mod); ejs = {nombre(s) for s in mod.EJECUCIONES}; defs = set(getattr(mod, "DEFINICIONES", []) or []) | {None}
    fil = {"todos"} | set(getattr(mod, "FILTROS", {}) or {})
    if not 0 < len(hipotesis) <= K_MAX: raise ValueError(f"entre 1 y {K_MAX} hipótesis")
    for h in hipotesis:
        if h.get("ejec") not in ejs or h.get("defn") not in defs or h.get("filtro", "todos") not in fil: raise ValueError(f"hipótesis inválida: {h}")
    cuerpo = dict(modulo=mod.__name__, familia=familia, hipotesis=hipotesis, ventana_confirmacion=ventana_confirmacion,
                  ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    h = hashlib.sha256(json.dumps(cuerpo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    p = Path(carpeta) / f"CONGELADAS_{cuerpo['ts'][:10].replace('-', '')}_{h[:8]}.json"
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(dict(cuerpo, sha256=h), indent=1, ensure_ascii=False), encoding="utf-8")
    if registro is not None: registro.ensure(f"{familia.lower()}/confirmacion_{h[:8]}", familia, len(hipotesis), f"congeladas en {p.name}")
    return p


def verificar_congeladas(p: Path) -> dict:
    d = json.loads(Path(p).read_text(encoding="utf-8")); h = d.pop("sha256")
    if hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != h: raise ValueError(f"{p}: el contenido no coincide con su hash")
    return dict(d, sha256=h)


def confirmar(mod, T: pd.DataFrame, congeladas: Path, alfa_mde: float = 0.10) -> dict:
    """Prueba UNA vez las hipótesis congeladas sobre la tabla de confirmación. Veredicto por regla:
    CONFIRMADA = nominada por BH (q 0,10) y ≥ 4/5 sub-bloques positivos; EN_CONTRA = R neto ≤ 0 con potencia (MDE80 ≤ |efecto de
    desarrollo| si se declaró, si no ≤ 0,1 R); SIN_POTENCIA = n < 30 sesiones o MDE80 > 0,1 R; NO_CONCLUYENTE = el resto."""
    mod = TB.cargar(mod); C = verificar_congeladas(congeladas); filas = []
    for h in C["hipotesis"]:
        y = next(yy for d, e, f, _, yy, _ in celdas(mod, T) if d == h.get("defn") and e == h["ejec"] and f == h.get("filtro", "todos"))
        m = np.isfinite(y); S = T[m]; s = _ses_sum(y, T.ses.to_numpy())
        if m.sum() < 10:
            filas.append(dict(h, n=int(m.sum()), p=1.0, veredicto="SIN_POTENCIA")); continue
        e = BE.estabilidad(y[m], S.ses.to_numpy(), BE._sesiones(S.assign(inst=S.get("fuente", "?"), fecha=S.ses)), n_perm=4000)
        se = float(s.std(ddof=1) * np.sqrt(len(s)) / max(m.sum(), 1)) if len(s) > 1 else np.inf    # error de la media por sesión
        filas.append(dict(h, n=int(m.sum()), sesiones=int(len(s)), r_neto=float(y[m].mean()), p=float(e.get("p_media") or 1.0),
                          bloques=e.get("bloques_pos"), mde80=float(2.49 * se)))
    nom = BE.bh([f["p"] for f in filas], Q_BH)
    for f, nb in zip(filas, nom):
        f["nominada_bh"] = bool(nb)
        if "veredicto" in f: continue
        umbral = abs(f.get("efecto_desarrollo") or 0.1)
        if f["sesiones"] < 30 or f["mde80"] > umbral: f["veredicto"] = "SIN_POTENCIA" if f["r_neto"] > 0 or not np.isfinite(f["mde80"]) else "EN_CONTRA_SIN_POTENCIA"
        elif nb and (f["bloques"] or 0) >= 4 and f["r_neto"] > 0: f["veredicto"] = "CONFIRMADA"
        elif f["r_neto"] <= 0: f["veredicto"] = "EN_CONTRA"
        else: f["veredicto"] = "NO_CONCLUYENTE"
    return dict(congeladas=str(congeladas), sha256=C["sha256"], hipotesis=filas, q_bh=Q_BH)


def informe_confirmacion(res: dict) -> str:
    md = [f"# Confirmación — {Path(res['congeladas']).name}", "", f"Hash de las congeladas: `{res['sha256']}`. BH q {res['q_bh']}. "
          "Veredicto por regla fija (`analizar_tabla.confirmar`).", "",
          "| definición | ejecución | filtro | n | sesiones | R neto | p | bloques + | MDE80 | BH | veredicto |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in res["hipotesis"]:
        md.append(f"| {f.get('defn')} | {f['ejec']} | {f.get('filtro', 'todos')} | {f['n']} | {f.get('sesiones', '—')} | {f.get('r_neto', float('nan')):+.3f} | "
                  f"{f['p']:.3f} | {f.get('bloques', '—')} | {f.get('mde80', float('nan')):.3f} | {'sí' if f.get('nominada_bh') else 'no'} | **{f['veredicto']}** |")
    return "\n".join(md) + "\n"
