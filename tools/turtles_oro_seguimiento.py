#!/usr/bin/env python3
"""TURTLES-ORO (base congelada) en datos no vistos: holdout (ACTA_HOLDOUT.md, una apertura) y forward bajo demanda.

  python tools/turtles_oro_seguimiento.py holdout <commit>              # apertura única 2026-10-01 → 2026-11-13 (registra la apertura antes)
  python tools/turtles_oro_seguimiento.py traer_holdout
  python tools/turtles_oro_seguimiento.py forward <AAAAMMDD> [commit]   # sesiones >= 2026-11-14
  python tools/turtles_oro_seguimiento.py traer_forward <AAAAMMDD>
Mismo esquema que tools/som_seguimiento.py (reusa construir/_push/_bajar/traer_*); kernel tools/kaggle_grilla/turtles_oro_main.py.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import som_seguimiento as SS  # noqa: E402  (reutilizado: armado del kernel, push, descarga, lecturas)

KS = "nicolasbuttaro/edgelab-turtles-oro-seg"; OUT = ROOT / "docs/research/turtles_oro_20261117/seguimiento"
ACTA = "docs/research/turtles_oro_20261117/ACTA_HOLDOUT.md"; P_DEV = 0.32; FAMILIA = "TURTLES-ORO"
MODULOS = (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
           ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"), ("edgelab.research.sqx_catalogo", "edgelab/research/sqx_catalogo.py"))


def _fr():
    from edgelab.research.embudo_runners import friccion
    return friccion("GC")[0]


def construir(env: dict) -> Path:
    pre = "import sys, types, os\nos.environ.update(" + repr({k: str(v) for k, v in env.items()}) + ")\n"
    for nom, ruta in MODULOS:
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; _m.__package__ = {nom.rsplit('.', 1)[0] if ruta else nom!r}; _m.__file__ = '/kaggle/working/x/{ruta or nom}'; sys.modules[{nom!r}] = _m\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text(encoding='utf-8')!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
    k = ROOT / "data/turtles_oro_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text(pre + (ROOT / "tools/kaggle_grilla/turtles_oro_main.py").read_text(encoding="utf-8"), encoding="utf-8"); return k


def holdout(commit):
    from edgelab.research import holdout_ventanas as HV
    cid = f"{FAMILIA}::holdout_20261117"
    if (pr := HV.problemas(FAMILIA, 20261001, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
    HV.registrar_apertura(FAMILIA, cid, 20261001, n_fijo=0)
    acta = dict(acta=ACTA, commit=commit, familia=FAMILIA, cid=cid)
    SS._push(KS + "-h", "edgelab turtles oro seg h", construir(dict(DESDE=20261001, HASTA=20261113, FR=_fr(), ACTA_JSON=json.dumps(acta))))


def forward(hasta, commit=""):
    acta = dict(acta=ACTA, commit=commit, familia=FAMILIA, cid=f"{FAMILIA}::forward")
    SS._push(f"{KS}-fw{hasta}", f"edgelab turtles oro seg fw{hasta}", construir(dict(DESDE=20261114, HASTA=int(hasta), FR=_fr(), ACTA_JSON=json.dumps(acta))))


def _bajar(slug, d):
    import subprocess, pandas as pd
    d.mkdir(parents=True, exist_ok=True)
    for f in ("TURTLES_OPS.csv", "RESUMEN.json"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", slug, "--file", f, "--out", str(d / f)], cwd=ROOT, check=True)
    F = pd.read_csv(d / "TURTLES_OPS.csv"); return F[F.motivo != "FIN"]          # la abierta al cierre de la ventana no se cuenta


def traer_holdout():
    import math, numpy as np
    F = _bajar(KS + "-h", OUT / "holdout"); x = F.R.to_numpy(float); n = len(x)
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 2 else float("nan")
    p_h = float(0.5 * math.erfc(t / math.sqrt(2))) if n > 2 else 1.0
    q = -2 * (math.log(max(p_h, 1e-300)) + math.log(P_DEV)); fisher = float(math.exp(-q / 2) * (1 + q / 2))
    ee = float(x.std(ddof=1) / np.sqrt(n)) if n > 2 else float("nan")
    lect = "CONFIRMADA" if (n and x.mean() > 0 and fisher < 0.05) else ("EN_CONTRA" if n > 2 and x.mean() < -ee else "NO_CONCLUYENTE")
    res = dict(n=n, R=float(x.mean()) if n else None, R_total=float(x.sum()), t=t, p_holdout=p_h, p_desarrollo=P_DEV, fisher=fisher, lectura=lect,
               ops=F[["fecha", "lado", "entrada", "salida_px", "motivo", "R"]].to_dict("records"))
    (OUT / "RESULTADO_HOLDOUT.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


def traer_forward(hasta):
    from edgelab.funnel.secuencial import EProceso
    d = OUT / f"fw{hasta}"; F = _bajar(f"{KS}-fw{hasta}", d); E = EProceso(mu0=0.0, piso=-6.0, techo=6.0); n = 0; estado = "SIN_DECIDIR"
    for x in F.sort_values("fecha").R:
        if not -6 <= x <= 6: estado = "LIMITE_VIOLADO"; break
        E.agregar(float(x)); n += 1
    if estado != "LIMITE_VIOLADO" and E.e_valor >= 10: estado = "EDGE"
    res = dict(hasta=int(hasta), n=n, R_total=float(F.R.sum()), e=float(E.e_valor), estado=estado)
    (d / "FORWARD.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    globals()[sys.argv[1]](*sys.argv[2:])
