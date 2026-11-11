#!/usr/bin/env python3
"""Análisis EXPLORATORIO de LUXIMB-HVN sobre las tablas de DESARROLLO (docs/research/luximb_hvn_20261111/PREREGISTRO.md §5).
Nada de esto confirma: ordena qué congelar para la confirmación en USATECH 2023-01 → 2025-07 (sin mirar) y el forward.
  python tools/luximb_hvn_analisis.py [--defs D3_20_a0_z2,D3_20_a0_z0] [--top 25]
Lee docs/research/luximb_hvn_20261111/tablas/LXH_*.csv.gz y escribe EXPLORACION.md y EXPLORACION.json en la misma carpeta.

Qué reporta (por fuente NQ / USATECH y período DESC / REP, y juntos):
  M  mecanismo sin P&L: frecuencia del patrón de la captura (se extiende ≥ e·rango más allá de B y DESPUÉS toca A) según el nodo de
     volumen más allá (hvn alto / bajo), con su control (la misma cuenta en impulsos sin condición de zonas, definición z0).
  E0 entrada al confirmar: R bruto y neto (fricción de edgelab/costos.py sobre el riesgo de cada operación), estabilidad en 5
     sub-bloques, p por inversión de signo por sesión, y la fricción mediana en R (la guarda K: ≤ 0,08).
  EXT entrada en la vuelta: lo mismo, sin filtro y con filtro de HVN (umbral × ventana), y «sin HVN» (hvn < 1).
  Nulo de la búsqueda: cuál sería el mejor t por azar con tantas celdas (inversión de signo por sesión de TODA la búsqueda).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.costos import friccion_rt_puntos  # noqa: E402
from edgelab.research import banco_eventos as BE  # noqa: E402
from edgelab.research import luximb_hvn as H  # noqa: E402

DIR = ROOT / "docs/research/luximb_hvn_20261111"
FIN_DESC = 20260331
FRIC = {"NQ": friccion_rt_puntos("NQ"), "USATECHIDXUSD": friccion_rt_puntos("NQ")}      # USATECH: referencia con los costos de NQ
UMBRALES_HVN = (1.5, 2.0, 3.0)
E_PATRON = (0.1, 0.25)


def cargar() -> pd.DataFrame:
    partes = []
    for f in sorted((DIR / "tablas").glob("LXH_*.csv.gz")):
        m = re.match(r"LXH_(.+)_(\d{8})_(\d{8})", f.name.replace(".csv.gz", ""))
        T = pd.read_csv(f); T["fuente"] = m.group(1); partes.append(T)
    if not partes: raise SystemExit("sin tablas en docs/research/luximb_hvn_20261111/tablas (python tools/luximb_hvn.py traer ...)")
    T = pd.concat(partes, ignore_index=True).copy(); T["periodo"] = np.where(T.ses <= FIN_DESC, "DESC", "REP")
    T["inst"] = T.fuente; T["fecha"] = T.ses; T["placebo"] = 0
    return T


def resumen(y, T) -> dict:
    """Barato para todas las celdas (n, media, t por sesión); la estabilidad con permutaciones sólo para las de arriba (`estable`)."""
    y = np.asarray(y, float); m = np.isfinite(y)
    if m.sum() < 20: return dict(n=int(m.sum()))
    s = pd.Series(y[m]).groupby(T.ses.to_numpy()[m]).sum().to_numpy()               # t con las sesiones como unidad
    return dict(n=int(m.sum()), sesiones=int(len(s)), media=float(y[m].mean()), t=float(s.sum() / np.sqrt((s ** 2).sum())) if (s ** 2).sum() > 0 else 0.0)


def estable(y, T) -> dict:
    y = np.asarray(y, float); m = np.isfinite(y); S = T[m]
    e = BE.estabilidad(y[m], S.ses.to_numpy(), BE._sesiones(S), n_perm=2000)
    return dict(bloques=e.get("bloques_pos"), p=e.get("p_media"))


def neto(T, ej):
    fr = T.fuente.map(FRIC).to_numpy(float); k = T[f"k_{ej}"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return T[f"r_{ej}"].to_numpy(float) - fr / k, fr / k


def filtros_hvn(T):
    out = {"todos": np.ones(len(T), bool)}
    for L in H.LOOKBACKS:
        h = T[f"hvn_{L}"].to_numpy(float)
        for u in UMBRALES_HVN: out[f"hvn{L}>={u}"] = h >= u
        out[f"hvn{L}<1"] = h < 1
    return out


def mecanismo(T, defs):
    out = {}
    for dfn in defs:
        S = T[T[dfn].astype(bool)]
        if not len(S): continue
        for e in E_PATRON:
            pat = ((S.ext_antes_A >= e) & (S.toca_A == 1)).astype(float).to_numpy()   # se extendió ≥ e y después tocó A
            ext = (S.ext_antes_A >= e).to_numpy()
            for fn, m in filtros_hvn(S).items():
                cond = pat[ext & m].mean() if (ext & m).sum() >= 20 else None             # P(toca A | se extendió ≥ e, filtro)
                out[f"{dfn}|e{e}|{fn}"] = dict(n_ext=int((ext & m).sum()), p_toca_A_tras_extender=cond, p_patron=float(pat[m].mean()) if m.sum() else None)
    return out


def nulo_busqueda(sumas: list, n_perm=300, seed=17) -> dict:
    """Máximo t por azar repitiendo TODA la búsqueda: cada sesión invierte el signo de todos sus eventos en todas las celdas a la
    vez (conserva la correlación entre celdas). `sumas`: lista de Series (sesión -> suma de R neto) por celda."""
    if not sumas: return {}
    M = pd.concat(sumas, axis=1).fillna(0.0).to_numpy().T                    # celdas × sesiones
    den = np.sqrt((M ** 2).sum(1)); den[den == 0] = np.inf; rng = np.random.default_rng(seed)
    mx = np.array([np.max((M @ rng.choice([-1.0, 1.0], M.shape[1])) / den) for _ in range(n_perm)])
    return dict(celdas=int(M.shape[0]), t_max_p50=float(np.median(mx)), t_max_p90=float(np.percentile(mx, 90)), t_max_p95=float(np.percentile(mx, 95)))


def tablas_pnl(T, defs, top):
    filas = []; sumas = []
    for dfn in defs:
        S = T[T[dfn].astype(bool)].reset_index(drop=True)
        if not len(S): continue
        fh = filtros_hvn(S)
        for x in H.E0:
            ej = H.nombre_e0(x); y, cr = neto(S, ej)
            filas.append(dict(defn=dfn, ejec=ej, filtro="todos", fric_r_med=float(np.nanmedian(cr)), r_bruto=float(np.nanmean(S[f"r_{ej}"])), **resumen(y, S)))
            sumas.append(pd.Series(np.nan_to_num(y)).groupby(S.ses.to_numpy()).sum())
        for x in H.EXT:
            ej = H.nombre_ext(x); y, cr = neto(S, ej)
            for fn, m in fh.items():
                yy = np.where(m, y, np.nan)
                filas.append(dict(defn=dfn, ejec=ej, filtro=fn, fric_r_med=float(np.nanmedian(np.where(m, cr, np.nan))) if np.isfinite(np.where(m, cr, np.nan)).any() else None,
                                  r_bruto=float(np.nanmean(np.where(m, S[f"r_{ej}"], np.nan))) if np.isfinite(yy).any() else None, **resumen(yy, S)))
                if np.isfinite(yy).sum() >= 30: sumas.append(pd.Series(np.nan_to_num(yy)).groupby(S.ses.to_numpy()).sum())
    P = pd.DataFrame(filas); P.attrs["nulo"] = nulo_busqueda(sumas)
    if "t" not in P: return P, P.head(0).assign(bloques=None, p=None)
    top = P[P.n >= 30].sort_values("t", ascending=False).head(top).copy()
    est = []
    for r in top.itertuples():
        S = T[T[r.defn].astype(bool)].reset_index(drop=True); y, _ = neto(S, r.ejec)
        if r.filtro != "todos": y = np.where(filtros_hvn(S)[r.filtro], y, np.nan)
        est.append(estable(y, S))
    top["bloques"] = [e["bloques"] for e in est]; top["p"] = [e["p"] for e in est]
    return P, top


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--defs", default=None); ap.add_argument("--top", type=int, default=25); a = ap.parse_args()
    T = cargar()
    defs = a.defs.split(",") if a.defs else [H.VISOR, H.VISOR.replace("_z2", "_z0"), "D3_20_a0_z3", "D3_20_a0_z4", "D2_20_a0_z2", "D4_20_a0_z2", "D3_40_a0_z2"]
    res = dict(eventos=int(len(T)), por_fuente_periodo={f"{f}/{p}": int(len(g)) for (f, p), g in T.groupby(["fuente", "periodo"])}, cortes={})
    md = ["# LUXIMB-HVN — exploración sobre desarrollo (NO confirma nada)", "",
          "Estado: EXPLORATORIO (generado por `tools/luximb_hvn_analisis.py`). Datos ya mirados por el linaje LUX-IMB; la confirmación es",
          "en USATECH 2023-01 → 2025-07 (sin mirar) y en forward, con lo que se congele de acá (PREREGISTRO.md §5–6).", ""]
    for (f, p), S in [(("todos", "todos"), T)] + list(T.groupby(["fuente", "periodo"])):
        S = S.reset_index(drop=True); clave = f"{f}/{p}"
        P, top = tablas_pnl(S, defs, a.top); mec = mecanismo(S, defs)
        res["cortes"][clave] = dict(mecanismo=mec, celdas=int(len(P)), nulo_busqueda=P.attrs.get("nulo"), top=top.to_dict("records"))
        P.to_csv(DIR / f"EXPLORACION_{f}_{p}.csv", index=False)
        nu = P.attrs.get("nulo") or {}
        md += [f"## {clave} — {len(S)} eventos, {len(P)} celdas", "",
               f"Nulo de la búsqueda completa (inversión de signo por sesión, {nu.get('celdas')} celdas evaluables): el MEJOR t por azar tiene "
               f"mediana {nu.get('t_max_p50', float('nan')):.2f} y percentil 95 {nu.get('t_max_p95', float('nan')):.2f}. Una fila por debajo de eso no se distingue del azar.", "", "| definición | ejecución | filtro | n | R bruto | R neto | bloques + | p | fricción R | t |", "|---|---|---|---|---|---|---|---|---|---|"]
        md += [f"| {r.defn} | {r.ejec} | {r.filtro} | {r.n} | {r.r_bruto:+.3f} | {r.media:+.3f} | {r.bloques} | {r.p:.3f} | {r.fric_r_med:.3f} | {r.t:+.2f} |" for r in top.itertuples()]
        md += ["", "Mecanismo (visor): P(toca A | se extendió ≥ e) según el nodo de volumen más allá de B", "", "| clave | n extendidos | P(toca A tras extender) |", "|---|---|---|"]
        md += [f"| {k} | {v['n_ext']} | {v['p_toca_A_tras_extender'] if v['p_toca_A_tras_extender'] is None else round(v['p_toca_A_tras_extender'], 3)} |"
               for k, v in mec.items() if k.startswith(H.VISOR) or k.startswith(H.VISOR.replace('_z2', '_z0'))]
        md += [""]
    md += ["Lectura obligatoria: con miles de celdas el mejor t por azar ronda 4–4,5; ninguna fila de arriba es un hallazgo hasta",
           "congelarla y probarla en datos no mirados. Fricción R > 0,08 = la celda no es elegible (K de la guía de errores)."]
    (DIR / "EXPLORACION.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (DIR / "EXPLORACION.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print("escrito", (DIR / "EXPLORACION.md").relative_to(ROOT))


if __name__ == "__main__":
    main()
