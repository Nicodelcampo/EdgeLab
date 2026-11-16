#!/usr/bin/env python3
"""Seguimiento forward de la cartera v2 con e-proceso (pre-registro docs/research/cartera_20261116/PREREGISTRO_FORWARD_V2.md).

  python tools/cartera_v2_forward.py lanzar [--hasta AAAAMMDD]   # las 8 reglas sobre el sellado 10-01 → HASTA (contexto desde el 1-oct)
  python tools/cartera_v2_forward.py traer  [--hasta AAAAMMDD]   # baja, aplica v2 y v3 a las sesiones >= 2026-11-14 -> FORWARD.json y FORWARD_V3.json

v2 (CARTERA_V2_OPERATIVA.json): comisión mínima (A1), PREAPERTURA-NQ ×0,5 (A2), no operar si fricción canónica / riesgo > 0,08 (M1),
micros fijos por regla (M3). Unidad: «R de cartera» = USD / 200. Reusa el KaggleRunner sellado (cartera_nov) y secuencial.EProceso.
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from cartera_nov import DIR, SELLADO, universo  # noqa: E402

FW = DIR / "forward"; DESDE_FW = 20261114; USD_R = 200.0
ACTA = "docs/research/cartera_20261116/PREREGISTRO_FORWARD_V2.md"
COTAS_OP, COTAS_SES = (-6.0, 30.0), (-15.0, 40.0)      # declaradas antes de mirar (R de cartera por operación / por sesión)
ALFA = 0.10


VERSIONES = {"v2": ("CARTERA_V2_OPERATIVA.json", "FORWARD.json"), "v3": ("CARTERA_V3_OPERATIVA.json", "FORWARD_V3.json")}   # v3: PREREGISTRO_TANDA4 C1


def _v2(ver="v2"):
    return {r["regla"]: r for r in json.loads((DIR / VERSIONES[ver][0]).read_text(encoding="utf-8"))["reglas"]}


SEGUIMIENTO = ("PREAPERTURA-ES",)                                    # PREREGISTRO_TANDA5 T5b: sólo se baja (lo lee franklin_seguimiento)


def _todas():
    return {c: r for v in VERSIONES for c, r in _v2(v).items()}


def lanzar(hasta, commit):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado=SELLADO, raiz=None); U = {r["cid"]: r for r in universo()}
    FW.mkdir(parents=True, exist_ok=True); hf = FW / f"handles_{hasta}.json"; hs = json.loads(hf.read_text()) if hf.exists() else {}
    for c in list(_todas()) + list(SEGUIMIENTO):
        if c in hs: continue
        r = U[c]; sp = dict(r["spec"], cid=f"FW-{c}-{hasta}"[:30], cuenta_kaggle="nicolasbuttaro")
        params = dict(cortes=r["cortes"], celdas=[r["celda"]], tope=r["tope"], operaciones=True,
                      acta=dict(tipo="forward_v2", acta=ACTA, commit=commit, cid=c, acta_regla=r["acta"]))
        try: hs[c] = run.lanzar(sp, "ANALIZAR_REGLA", params, [20261001, int(hasta)])
        except Exception as ex: print("no se lanzó", c, str(ex)[-200:]); continue
        hf.write_text(json.dumps(hs, indent=1)); print("lanzada", c, hs[c], flush=True)


def _r_v2(c, o, en_R, ver="v2"):
    """Operaciones forward de una regla con la versión aplicada: [(ses, R de cartera)] y cuántas saltea M1."""
    from edgelab import costos as C
    from edgelab.holdout import sesion_excluida
    v = _v2(ver)[c]; m = v["ejecuta"]; usd_pt = C.tick_value_usd(m) / C.tick_size(m)
    dfr = C.friccion_rt_puntos(m, criterio="max") - C.friccion_rt_puntos(m, criterio="min"); out, salt = [], 0
    for s, n, rg in zip(o.get("ses", []), o.get("neto", []), o.get("riesgo", [])):
        if s < DESDE_FW or rg is None or not np.isfinite(n) or rg <= 0: continue
        if any(sesion_excluida(i, s) for i in {v["senal"].replace("DK:", ""), m[1:]}): continue
        if rg < v["no_operar_si_stop_menor_a_pts"]: salt += 1; continue                  # M1
        R = (n if en_R else n / rg) + dfr / rg                                            # A1
        out.append((int(s), R * rg * usd_pt * v["micros"] / USD_R))                       # M3 (+ A2 en los micros)
    return out, salt


def _eproceso(xs, cotas):
    from edgelab.funnel.secuencial import EProceso
    E = EProceso(mu0=0.0, piso=cotas[0], techo=cotas[1]); n = 0
    for x in xs:
        if not cotas[0] <= x <= cotas[1]: return dict(n=n, e=float(E.e_valor), estado="LIMITE_VIOLADO")
        E.agregar(float(x)); n += 1
    return dict(n=n, e=float(E.e_valor), estado="EDGE" if E.e_valor >= 1 / ALFA else "SIN_DECIDIR")


def traer(hasta):
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(dataset_sellado=SELLADO, raiz=None); hs = json.loads((FW / f"handles_{hasta}.json").read_text()); U = {r["cid"]: r for r in universo()}
    falta, ops_por = [], {}
    for c in list(_todas()) + list(SEGUIMIENTO):
        f = FW / f"{c}__{hasta}.json"
        if not f.exists():
            if c not in hs: falta.append((c, "sin_lanzar")); continue
            e = run.estado(hs[c])
            if e != "complete": falta.append((c, e)); continue
            f.write_text(json.dumps(run.traer(hs[c]), indent=1, default=float))
        ops_por[c] = json.loads(f.read_text()).get("operaciones") or {}
    if falta: print("faltan", falta); return
    for ver, (_, salida) in VERSIONES.items():
        por_regla, ses_tot = {}, {}
        for c in _v2(ver):
            ops, salt = _r_v2(c, ops_por[c], U[c]["spec"].get("estadistico") == "R", ver)
            por_regla[c] = dict(n=len(ops), salteadas_M1=salt, R_total=float(sum(x for _, x in ops)), e=_eproceso([x for _, x in ops], COTAS_OP))
            for s, x in ops: ses_tot[s] = ses_tot.get(s, 0.0) + x
        ses = sorted(ses_tot); xs = [ses_tot[s] for s in ses]
        out = dict(version=ver, hasta=int(hasta), desde=DESDE_FW, actualizado=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), por_regla=por_regla,
                   cartera=dict(sesiones_con_ops=len(ses), R_total=float(sum(xs)), usd=float(sum(xs) * USD_R), e=_eproceso(xs, COTAS_SES)),
                   usd_por_sesion={str(s_): float(x * USD_R) for s_, x in zip(ses, xs)})                  # vista conjunta con la cartera B
        (DIR / salida).write_text(json.dumps(out, indent=1, default=float))
        with (FW / "historial.jsonl").open("a", encoding="utf-8") as fh: fh.write(json.dumps(dict(version=ver, hasta=int(hasta), cartera=out["cartera"]), default=float) + "\n")
        print(ver, json.dumps(out["cartera"], indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("lanzar", "traer")); ap.add_argument("--hasta", default=time.strftime("%Y%m%d"))
    ap.add_argument("--commit", default=""); a = ap.parse_args()
    lanzar(a.hasta, a.commit) if a.cmd == "lanzar" else traer(a.hasta)
