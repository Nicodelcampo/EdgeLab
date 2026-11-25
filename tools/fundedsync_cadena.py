#!/usr/bin/env python3
"""FUNDEDSYNCSTACK por la cadena (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_CADENA.md).
  python tools/fundedsync_cadena.py lanzar      # kernel en Kaggle (M1 Nasdaq 2012 → 2026-09, costos NQ, nulo intradía ×20)
  python tools/fundedsync_cadena.py traer       # RESULTADO.json y operaciones a docs/research/fundedsyncstack_20261115/cadena/
Incrusta el paquete como tools/m1_intradia.py::_incrustar (módulos por nombre en sys.modules, en orden de dependencias).
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KS = "nicolasbuttaro/edgelab-fundedsync-cadena"; OUT = ROOT / "docs/research/fundedsyncstack_20261115/cadena"
PKG = "edgelab.research.fundedsyncstack"
ORDEN = ("contracts", "base_series", "modulos_a1_a20_f_s", "modulos_p_c_v_o", "modulos_r_z_e_q", "modulos_w_n_t", "motor_cartera", "paridad_vendedor", "__init__")


def construir() -> Path:
    pre = "import sys, types\n"
    for nom, ruta in (("edgelab", None), ("edgelab.research", None), ("edgelab.holdout", "edgelab/holdout.py"),
                      ("edgelab.research.ema_zones", "edgelab/research/ema_zones.py"), ("edgelab.research.fuentes_ticks", "edgelab/research/fuentes_ticks.py"),
                      ("m1_intradia", "edgelab/research/m1_intradia.py")):
        pre += f"_m = types.ModuleType({nom!r}); _m.__path__ = []; sys.modules[{nom!r}] = _m\n"
        if ruta: pre += f"exec(compile({(ROOT / ruta).read_text(encoding="utf-8")!r}, {ruta!r}, 'exec'), _m.__dict__)\n"
        if "." in nom: pre += f"setattr(sys.modules[{nom.rsplit('.', 1)[0]!r}], {nom.rsplit('.', 1)[1]!r}, _m)\n"
    pre += f"_p = types.ModuleType({PKG!r}); _p.__path__ = []; _p.__package__ = {PKG!r}; sys.modules[{PKG!r}] = _p; sys.modules['edgelab.research'].fundedsyncstack = _p\n"
    for m in ORDEN:
        src = (ROOT / f"edgelab/research/fundedsyncstack/{m}.py").read_text(encoding="utf-8")
        if m == "__init__":
            pre += f"_p.__dict__['__name__'] = {PKG!r}\nexec(compile({src!r}, '{PKG}/__init__.py', 'exec'), _p.__dict__)\n"
        else:
            pre += (f"_s = types.ModuleType('{PKG}.{m}'); _s.__package__ = {PKG!r}; _s.__dict__['__file__'] = '/kaggle/src/{PKG.replace(".", "/")}/{m}.py'; sys.modules['{PKG}.{m}'] = _s\n"
                    f"exec(compile({src!r}, '{PKG}/{m}.py', 'exec'), _s.__dict__); setattr(_p, {m!r}, _s)\n")
    k = ROOT / "data/fundedsync_kernel.py"; k.parent.mkdir(exist_ok=True)
    k.write_text(pre + (ROOT / "tools/kaggle_grilla/fundedsync_main.py").read_text(encoding="utf-8"), encoding="utf-8"); return k


def lanzar():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from edgelab.research.puerta_kernel import validar_script_kernel

    k = construir(); print("kernel", k.stat().st_size, "bytes")
    errs = validar_script_kernel(k.read_text(encoding="utf-8"), require_canonical=True)
    if errs:
        raise SystemExit("puerta_kernel bloqueo push en fundedsync_cadena: " + "; ".join(errs))
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS, "--title", "edgelab fundedsync cadena", "--script", str(k),
                    "--dataset", "nicolasbuttaro/edgelab-sqx-m1"], cwd=ROOT, check=True)


def holdout(commit):
    """Apertura única (ACTA_HOLDOUT.md): registra la ventana y lanza T, Z y R sobre desarrollo + USATECH sellado."""
    import json, os
    sys.path.insert(0, str(ROOT)); from edgelab.research import holdout_ventanas as HV
    cid = "FUNDEDSYNC::holdout_TZR_20261116"
    if os.environ.get("REINTENTO_SIN_MIRAR") != "1":                 # 2026-11-16: el 1.er intento devolvió 0 operaciones (corte por defecto en 10-01)
        if (pr := HV.problemas("FUNDEDSYNC", 20261001, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
        HV.registrar_apertura("FUNDEDSYNC", cid, 20261001, n_fijo=0)
    acta = dict(acta="docs/research/fundedsyncstack_20261115/ACTA_HOLDOUT.md", commit=commit, familia="FUNDEDSYNC", cid=cid)
    k = construir(); txt = k.read_text(encoding="utf-8")
    k.write_text("import os\nos.environ.update(SELLADO='1', HASTA='20261113', FIN='2026-11-14', ACTA_JSON=" + repr(json.dumps(acta)) + ")\n" + txt, encoding="utf-8")
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", KS + "-h", "--title", "edgelab fundedsync cadena h", "--script", str(k),
                    "--dataset", "nicolasbuttaro/edgelab-sqx-m1", "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"], cwd=ROOT, check=True)


def forward(hasta, commit=""):
    """Forward diario de la canasta T+Z+R (PREREGISTRO_TANDA2 L2): desarrollo + USATECH sellado hasta HASTA; sólo sesiones >= 2026-11-14."""
    import json, datetime as dt
    fin = (dt.date(int(hasta[:4]), int(hasta[4:6]), int(hasta[6:])) + dt.timedelta(days=1)).isoformat()
    acta = dict(acta="docs/research/fundedsyncstack_20261115/PREREGISTRO_TANDA2.md", commit=commit, familia="FUNDEDSYNC", cid="FUNDEDSYNC::forward_TZR")
    k = construir(); txt = k.read_text(encoding="utf-8")
    k.write_text("import os\nos.environ.update(SELLADO='1', HASTA=" + repr(hasta) + ", FIN=" + repr(fin) + ", FW_DESDE='2026-11-14', FW_ZBANDA='1', ACTA_JSON=" + repr(json.dumps(acta)) + ")\n" + txt, encoding="utf-8")
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "push", "--slug", f"{KS}-fw{hasta}", "--title", f"edgelab fundedsync cadena fw{hasta}", "--script", str(k),
                    "--dataset", "nicolasbuttaro/edgelab-sqx-m1", "--dataset", "nicolasbuttaro/edgelab-holdout-sellado"], cwd=ROOT, check=True)


def traer_forward(hasta):
    """Baja el forward y actualiza los e-procesos de T, Z, R (Z y R con stop de catástrofe 0,5 × ATR20 vía MAE) y de la canasta."""
    import json
    import pandas as pd
    sys.path.insert(0, str(ROOT)); from edgelab.funnel.secuencial import EProceso
    d = OUT / "forward"; d.mkdir(parents=True, exist_ok=True); f = d / f"OPS_{hasta}.csv"
    subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", f"{KS}-fw{hasta}", "--file", "FUNDEDSYNC_HOLDOUT_OPS.csv", "--out", str(f)], cwd=ROOT, check=True)
    o = pd.read_csv(f, parse_dates=["dia"]); fr = 1.5455
    o = o[~o.modulo.astype(str).str.startswith("ZB_")]                    # Z-banda es otra serie (regimen_forward); la cartera B no cambia
    stop = 0.5 * o.atr20; corta = o.modulo.isin(["Z", "R"]) & (o.mae_pts >= stop)
    o["neto_v"] = o.neto.where(~corta, -stop - fr)
    res = {}
    for k, g in list(o.groupby("modulo")) + [("CANASTA", o)]:
        E = EProceso(mu0=0.0, piso=-400.0, techo=1200.0); serie = g.groupby("dia").neto_v.sum() if k == "CANASTA" else g.sort_values("t").neto_v
        for x in serie: E.agregar(float(min(max(x, -400.0), 1200.0)))
        res[k] = dict(n=int(len(serie)), neto_total=float(serie.sum()), e=float(E.e_valor), estado="EDGE" if E.e_valor >= 10 else "SIN_DECIDIR")
    (d / "FORWARD_TZR.json").write_text(json.dumps(dict(hasta=hasta, resultado=res), indent=1)); print(json.dumps(res, indent=1))


def cartera_b(hasta):
    """PREREGISTRO_CARTERA_B.md: la canasta en USD a 1 MNQ por regla, drawdown, distancia a la cuenta de referencia y vista conjunta con la v2."""
    import json
    import numpy as np, pandas as pd
    fic = json.loads((OUT.parent / "CARTERA_B_OPERATIVA.json").read_text(encoding="utf-8")); cu = fic["cuenta_referencia"]; al = fic["alertas"]
    o = pd.read_csv(OUT / f"forward/OPS_{hasta}.csv", parse_dates=["dia"]); fr = 1.5455
    o = o[~o.modulo.astype(str).str.startswith("ZB_")]
    stop = 0.5 * o.atr20; corta = o.modulo.isin(["Z", "R"]) & (o.mae_pts >= stop); o["usd"] = o.neto.where(~corta, -stop - fr) * fic["usd_por_punto"]
    d = o.groupby(o.dia.dt.strftime("%Y%m%d").astype(int)).usd.sum().sort_index(); ac = d.cumsum(); dd = float((ac - np.maximum.accumulate(np.r_[0.0, ac.values])[1:]).min()) if len(d) else 0.0
    res = dict(hasta=int(hasta), sesiones=int(len(d)), usd_total=float(d.sum()), por_regla={k: float(g.usd.sum()) for k, g in o.groupby("modulo")},
               dd_max=dd, distancia_limite=float(cu["dd"] + min(0.0, ac.min() if len(ac) else 0.0)), falta_objetivo=float(cu["objetivo"] - (ac.iloc[-1] if len(ac) else 0.0)),
               usd_por_sesion={str(k): float(v) for k, v in d.items()})
    v2f = OUT.parents[1] / "cartera_20261116/FORWARD.json"
    if v2f.exists():
        a = pd.Series(json.loads(v2f.read_text(encoding="utf-8")).get("usd_por_sesion", {}), dtype=float); a.index = a.index.astype(int)
        ix = sorted(set(a.index) | set(d.index)); x, y = a.reindex(ix, fill_value=0.0), d.reindex(ix, fill_value=0.0)
        res["conjunta_v2"] = dict(sesiones=len(ix), correlacion=float(np.corrcoef(x, y)[0, 1]) if len(ix) >= 3 and x.std() > 0 and y.std() > 0 else None,
                                  dias_ambas_bajo_300=int(((x < -300) & (y < -300)).sum()), peor_dia_suma=float((x + y).min()) if len(ix) else None)
    c = res.get("conjunta_v2", {})
    res["alertas"] = [m for m, ok in (("drawdown forward mayor al de desarrollo", dd < -al["dd_forward_mayor_a"]),
                                      ("cerca del límite de la cuenta", res["distancia_limite"] < al["distancia_limite_menor_a"]),
                                      ("correlación con la v2 ≥ 0,3", (c.get("correlacion") or 0) >= al["correlacion_v2_max"] and c.get("sesiones", 0) >= 20)) if ok]
    (OUT / "forward/CARTERA_B.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps({k: v for k, v in res.items() if k != "usd_por_sesion"}, indent=1, default=float))


def traer_holdout():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("RESULTADO_HOLDOUT.json", "FUNDEDSYNC_HOLDOUT_OPS.csv"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", KS + "-h", "--file", f, "--out", str(OUT / f)], cwd=ROOT, check=True)


def traer():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("RESULTADO.json", "FUNDEDSYNC_OPS.csv.gz"):
        subprocess.run([sys.executable, "tools/kaggle_kernel.py", "output", "--slug", KS, "--file", f, "--out", str(OUT / f)], cwd=ROOT, check=True)


if __name__ == "__main__":
    globals()[sys.argv[1]](*sys.argv[2:])
