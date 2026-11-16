#!/usr/bin/env python3
"""FRANKLIN en datos no vistos: apertura del holdout y forward (docs/research/reels_20261116/ACTA_HOLDOUT_FRANKLIN.md, cartera PREREGISTRO_TANDA5).

  python tools/franklin_seguimiento.py holdout <commit>          # apertura única: 2026-10-01 → 2026-11-13 (registra la apertura antes)
  python tools/franklin_seguimiento.py traer_holdout             # Franklin NQ+ES, filtro de T sobre las operaciones T del holdout
  python tools/franklin_seguimiento.py forward <AAAAMMDD> [commit]   # sesiones >= 2026-11-14
  python tools/franklin_seguimiento.py traer_forward <AAAAMMDD>  # e-procesos: Franklin, T filtrado, PREAPERTURA-ES con y sin veto de noche
Incrusta como tools/fundedsync_cadena.py::construir (módulos por nombre en sys.modules). Kernel: tools/kaggle_grilla/franklin_main.py.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
KS = "nicolasbuttaro/edgelab-franklin-seg"; OUT = ROOT / "docs/research/reels_20261116/seguimiento"
ACTA = "docs/research/reels_20261116/ACTA_HOLDOUT_FRANKLIN.md"
DATASETS = ["--dataset", "nicolasbuttaro/edgelab-sqx-m1", "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"]
P_DEV = 0.093                                         # ACTA_HOLDOUT_FRANKLIN.md: p de desarrollo declarada (2023–26, NQ+ES, base)
COTAS = (-6.0, 6.0)                                   # R por operación / diferencia por sesión (declaradas)


def _celda():
    return json.loads((ROOT / "docs/research/reels_20261116/FRANKLIN_MEJORAS.json").read_text())["al_holdout"].split("|")


def construir(env: dict) -> Path:
    pre = "import sys, types, os\nos.environ.update(" + repr({k: str(v) for k, v in env.items()}) + ")\n"
    mods = (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
            ("edgelab.research.ema_zones", "edgelab/research/ema_zones.py"), ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"),
            ("edgelab.research.m1_intradia", "edgelab/research/m1_intradia.py"), ("edgelab.research.estrategias_scrapeadas", "edgelab/research/estrategias_scrapeadas.py"),
            ("fundedsync_mecanismos", "tools/fundedsync_mecanismos.py"))
    for nom, ruta in mods:
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; _m.__file__ = '/kaggle/working/x/{ruta or nom}'; sys.modules[{nom!r}] = _m\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text(encoding='utf-8')!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
    pre += "sys.modules['m1_intradia'] = sys.modules['edgelab.research.m1_intradia']\n"
    k = ROOT / "data/franklin_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text(pre + (ROOT / "tools/kaggle_grilla/franklin_main.py").read_text(encoding="utf-8"), encoding="utf-8"); return k


def holdout(commit):
    from edgelab.research import holdout_ventanas as HV
    cid = "FRANKLIN::holdout_20261116"
    if (pr := HV.problemas("FRANKLIN", 20261001, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
    HV.registrar_apertura("FRANKLIN", cid, 20261001, n_fijo=0)
    acta = dict(acta=ACTA, commit=commit, familia="FRANKLIN", cid=cid)
    k = construir(dict(DESDE=20261001, HASTA=20261113, CELDA=json.dumps(_celda()), ACTA_JSON=json.dumps(acta)))
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS + "-h", "--title", "edgelab franklin seg h", "--script", str(k)] + DATASETS, cwd=ROOT, check=True)


def forward(hasta, commit=""):
    acta = dict(acta="docs/research/cartera_20261116/PREREGISTRO_TANDA5.md", commit=commit, familia="FRANKLIN", cid="FRANKLIN::forward")
    k = construir(dict(DESDE=20261114, HASTA=int(hasta), CELDA=json.dumps(_celda()), ACTA_JSON=json.dumps(acta)))
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", f"{KS}-fw{hasta}", "--title", f"edgelab franklin seg fw{hasta}", "--script", str(k)] + DATASETS,
                   cwd=ROOT, check=True)


def _bajar(slug, d):
    d.mkdir(parents=True, exist_ok=True)
    for f in ("FRANKLIN_OPS.csv", "SESGO_NQ.csv", "NOCHE.csv", "RESUMEN.json"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", slug, "--file", f, "--out", str(d / f)], cwd=ROOT, check=True)
    return pd.read_csv(d / "FRANKLIN_OPS.csv"), pd.read_csv(d / "SESGO_NQ.csv"), pd.read_csv(d / "NOCHE.csv")


def filtro_t(T, S):
    """Marca cada operación T (t en segundos UTC, side) con el sesgo de NQ en su minuto de entrada."""
    lt = pd.to_datetime(T.t, unit="s", utc=True).dt.tz_convert("America/New_York")
    k = pd.DataFrame(dict(fecha=lt.dt.strftime("%Y%m%d").astype(int).values, minuto=(lt.dt.hour * 60 + lt.dt.minute).values))
    s = k.merge(S, on=["fecha", "minuto"], how="left").sesgo.fillna(0).to_numpy()
    return T.assign(favor=(s == np.sign(T.side.to_numpy())))


def traer_holdout():
    import math
    F, S, _ = _bajar(KS + "-h", OUT / "holdout"); res = {}; p_dev = P_DEV
    por_ses = F.groupby("fecha").R.sum(); n = len(por_ses)
    t = por_ses.mean() / (por_ses.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan
    p_h = float(0.5 * math.erfc(t / math.sqrt(2))) if n > 2 else 1.0                       # normal (declarado en el acta)
    x = -2 * (math.log(max(p_h, 1e-300)) + math.log(p_dev)); fisher = float(math.exp(-x / 2) * (1 + x / 2))   # chi² con 4 gl
    ee = float(por_ses.std(ddof=1) / np.sqrt(n)) if n > 2 else np.nan
    lect = "CONFIRMADA" if (por_ses.mean() > 0 and fisher < 0.05) else ("EN_CONTRA" if por_ses.mean() < -ee else "NO_CONCLUYENTE")
    res["franklin"] = dict(n_ops=int(len(F)), sesiones=n, R_op=float(F.R.mean()) if len(F) else None, R_sesion=float(por_ses.mean()) if n else None,
                           por_inst={i: dict(n=int(len(g)), R=float(g.R.mean())) for i, g in F.groupby("inst")}, t=float(t), p_holdout=p_h, p_desarrollo=p_dev,
                           fisher=fisher, lectura=lect)
    T = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_HOLDOUT_OPS.csv"); T = T[T.modulo == "T"]
    T = filtro_t(T, S); a, r = T[T.favor], T[~T.favor]
    res["filtro_T"] = dict(n_favor=int(len(a)), neto_favor=float(a.neto.mean()) if len(a) else None, n_resto=int(len(r)), neto_resto=float(r.neto.mean()) if len(r) else None,
                           lectura="descriptivo (n chico; decide el forward)")
    (OUT / "RESULTADO_HOLDOUT.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


def _ep(xs):
    from edgelab.funnel.secuencial import EProceso
    E = EProceso(mu0=0.0, piso=COTAS[0], techo=COTAS[1]); n = 0
    for x in xs:
        if not COTAS[0] <= x <= COTAS[1]: return dict(n=n, e=float(E.e_valor), estado="LIMITE_VIOLADO")
        E.agregar(float(x)); n += 1
    return dict(n=n, e=float(E.e_valor), estado="EDGE" if E.e_valor >= 10 else "SIN_DECIDIR")


def traer_forward(hasta):
    d = OUT / f"fw{hasta}"; F, S, N = _bajar(f"{KS}-fw{hasta}", d); res = dict(hasta=int(hasta))
    res["franklin"] = dict(_ep(F.sort_values(["fecha", "inst"]).R.tolist()), R_total=float(F.R.sum()))
    tf = ROOT / f"docs/research/fundedsyncstack_20261115/cadena/forward/OPS_{hasta}.csv"
    if tf.exists():
        T = pd.read_csv(tf); T = filtro_t(T[T.modulo == "T"], S).sort_values("t"); g = T[T.favor]
        res["T_filtrado"] = dict(n=int(len(g)), neto_total=float(g.neto.sum()), neto_total_sin_filtro=float(T.neto.sum()))
    pf = ROOT / f"docs/research/cartera_20261116/forward/PREAPERTURA-ES__{hasta}.json"
    if pf.exists():
        o = json.loads(pf.read_text()).get("operaciones") or {}
        P = pd.DataFrame(dict(fecha=o.get("ses", []), neto=o.get("neto", []), riesgo=o.get("riesgo", [])))
        P = P[(P.fecha >= 20261114) & (P.riesgo > 0)].copy(); P["R"] = P.neto / P.riesgo
        P = P.merge(N[N.inst == "ES"][["fecha", "noche"]], on="fecha", how="left"); P["veto"] = P.noche == "alto"
        dif = P.groupby("fecha").apply(lambda g: g.R.sum() - g.R[~g.veto].sum()).tolist()     # lo que el veto evita (R vetadas)
        res["preapertura_es"] = dict(n=int(len(P)), vetadas=int(P.veto.sum()), R_sin_veto=float(P.R.sum()), R_con_veto=float(P.R[~P.veto].sum()),
                                     e_veto=_ep([-x for x in dif]))
    (d / "FORWARD.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    globals()[sys.argv[1]](*sys.argv[2:])
