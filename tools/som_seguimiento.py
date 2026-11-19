#!/usr/bin/env python3
"""SessionOpenMomentum (celda sin_finde) en datos no vistos: holdout (ACTA_HOLDOUT_SOM.md) y forward bajo demanda.

  python tools/som_seguimiento.py holdout <commit>        # apertura única 2026-10-01 → 2026-11-13 (registra la apertura antes)
  python tools/som_seguimiento.py traer_holdout
  python tools/som_seguimiento.py forward <AAAAMMDD> [commit]   # sesiones >= 2026-11-14
  python tools/som_seguimiento.py traer_forward <AAAAMMDD>
Incrusta módulos como tools/franklin_seguimiento.py::construir; kernel tools/kaggle_grilla/som_main.py.
"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
KS = "nicolasbuttaro/edgelab-som-seg"; OUT = ROOT / "docs/research/quantlab_mt5_eas_20261116/seguimiento"
ACTA = "docs/research/quantlab_mt5_eas_20261116/ACTA_HOLDOUT_SOM.md"; P_DEV = 0.039
DATASETS = ["--dataset", "nicolasbuttaro/edgelab-sqx-m1", "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"]
PKG = "edgelab.research.quantlab_mt5"


def construir(env: dict) -> Path:
    pre = "import sys, types, os\nos.environ.update(" + repr({k: str(v) for k, v in env.items()}) + ")\n"
    for nom, ruta in (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
                      ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"), (PKG, None),
                      (PKG + ".contracts", "edgelab/research/quantlab_mt5/contracts.py"), (PKG + ".indicators", "edgelab/research/quantlab_mt5/indicators.py"),
                      (PKG + ".session_open_momentum", "edgelab/research/quantlab_mt5/session_open_momentum.py")):
        pkg = nom.rsplit(".", 1)[0] if nom.startswith(PKG + ".") else nom
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; _m.__package__ = {pkg!r}; _m.__file__ = '/kaggle/working/x/{ruta or nom}'; sys.modules[{nom!r}] = _m\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text(encoding='utf-8')!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
    k = ROOT / "data/som_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text(pre + (ROOT / "tools/kaggle_grilla/som_main.py").read_text(encoding="utf-8"), encoding="utf-8"); return k


def _push(slug, titulo, k):
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", slug, "--title", titulo, "--script", str(k)] + DATASETS, cwd=ROOT, check=True)


def holdout(commit):
    from edgelab.research import holdout_ventanas as HV
    cid = "SOM::holdout_20261116"
    if (pr := HV.problemas("SOM", 20261001, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
    HV.registrar_apertura("SOM", cid, 20261001, n_fijo=0)
    _push(KS + "-h", "edgelab som seg h", construir(dict(DESDE=20261001, HASTA=20261113, ACTA_JSON=json.dumps(dict(acta=ACTA, commit=commit, familia="SOM", cid=cid)))))


def forward(hasta, commit=""):
    acta = dict(acta="docs/research/quantlab_mt5_eas_20261116/ACTA_HOLDOUT_SOM.md", commit=commit, familia="SOM", cid="SOM::forward")
    _push(f"{KS}-fw{hasta}", f"edgelab som seg fw{hasta}", construir(dict(DESDE=20261114, HASTA=int(hasta), ACTA_JSON=json.dumps(acta))))


def _bajar(slug, d):
    d.mkdir(parents=True, exist_ok=True)
    for f in ("SOM_OPS.csv", "RESUMEN.json"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", slug, "--file", f, "--out", str(d / f)], cwd=ROOT, check=True)
    return pd.read_csv(d / "SOM_OPS.csv")


def traer_holdout():
    F = _bajar(KS + "-h", OUT / "holdout"); x = F.R.to_numpy(float); n = len(x)
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else float("nan")
    p_h = float(0.5 * math.erfc(t / math.sqrt(2))) if n > 2 else 1.0
    q = -2 * (math.log(max(p_h, 1e-300)) + math.log(P_DEV)); fisher = float(math.exp(-q / 2) * (1 + q / 2))
    ee = float(x.std(ddof=1) / np.sqrt(n)) if n > 2 else float("nan")
    lect = "CONFIRMADA" if (x.mean() > 0 and fisher < 0.05) else ("EN_CONTRA" if n and x.mean() < -ee else "NO_CONCLUYENTE")
    res = dict(n=n, R=float(x.mean()) if n else None, acierto=float((x > 0).mean()) if n else None, t=t, p_holdout=p_h, p_desarrollo=P_DEV, fisher=fisher,
               lectura=lect, salidas=F.exit_name.value_counts().to_dict())
    (OUT / "RESULTADO_HOLDOUT.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


def traer_forward(hasta):
    from edgelab.funnel.secuencial import EProceso
    d = OUT / f"fw{hasta}"; F = _bajar(f"{KS}-fw{hasta}", d); E = EProceso(mu0=0.0, piso=-6.0, techo=6.0); n = 0; estado = "SIN_DECIDIR"
    for x in F.sort_values("entry_time_utc").R:
        if not -6 <= x <= 6: estado = "LIMITE_VIOLADO"; break
        E.agregar(float(x)); n += 1
    if estado != "LIMITE_VIOLADO" and E.e_valor >= 10: estado = "EDGE"
    res = dict(hasta=int(hasta), n=n, R_total=float(F.R.sum()), e=float(E.e_valor), estado=estado)
    (d / "FORWARD.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    globals()[sys.argv[1]](*sys.argv[2:])
