#!/usr/bin/env python3
"""Seguimiento secuencial de U1-B (acta: docs/research/areas_expansion_20261022/u1/ACTA_SEGUIMIENTO_U1B.md).

  python tools/u1b_seguimiento.py fase-b --hasta 20261020           # corre la Fase B (holdout) localmente -> serie por operación
  python tools/u1b_seguimiento.py mirar fase_a.parquet [fase_b.parquet ...]   # e-proceso sobre la serie acumulada, en orden

Las cotas y los α se leen SÓLO del acta (bloque JSON de la adenda, committeado antes de mirar); el script no acepta otros.
Cada mirada se agrega a u1/SEGUIMIENTO_U1B.jsonl (append-only): mirar seguido es válido (Ville) y queda trazado.
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
DIR = ROOT / "docs/research/areas_expansion_20261022/u1"
ACTA = DIR / "ACTA_SEGUIMIENTO_U1B.md"
CELDA = [0, 2, 1, 2, 2, 2, 3, 3, 3, 0]
SELLADO = r"E:\DatosNT8\tick_history_HOLDOUT_SELLADO\NQ_12-26_ticks.parquet"


def parametros():
    """El último bloque JSON del acta con 'piso' manda; el acta debe estar committeada sin cambios (como exige la guarda)."""
    if subprocess.run(["git", "status", "--porcelain", "--", str(ACTA)], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        raise SystemExit("el acta tiene cambios sin commitear: las cotas valen sólo si quedaron registradas antes de mirar")
    bloques = [json.loads(b) for b in re.findall(r"```json\s*(\{.*?\})\s*```", ACTA.read_text(encoding="utf-8"), re.S)]
    p = [b for b in bloques if "piso" in b]
    if not p: raise SystemExit("el acta no tiene la adenda de cotas: correr la Fase 0 y registrarla antes de la Fase A")
    return p[-1]


def mirar(series):
    import pandas as pd
    from edgelab.funnel.secuencial import MonitorCandidato
    prm = parametros()
    ops = pd.concat([(pd.read_csv(s) if str(s).endswith(".csv") else pd.read_parquet(s)).assign(fuente=Path(s).name) for s in series]).query("celda == 0").sort_values("t", kind="stable")
    m = MonitorCandidato(piso=prm["piso"], techo=prm["techo"], mu_util=prm["mu_util"], alfa=prm["alfa"], alfa_futilidad=prm["alfa_futilidad"])
    est = None
    for x in ops.neto.to_numpy():
        est = m.agregar(float(x))
        if est["estado"] != "SIN_DECIDIR": break                     # decisión tomada: se detiene (el e-proceso lo permite)
    est = est or m.estado()
    fila = dict(ts=time.time(), series=[str(Path(s).name) for s in series], sesiones=int(ops.ses.nunique()), hasta_ses=int(ops.ses.max()) if len(ops) else None,
                commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(), **est)
    with (DIR / "SEGUIMIENTO_U1B.jsonl").open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(fila, default=float) + "\n")
    print(json.dumps(fila, indent=1, default=float))


def fase_b(hasta, salida):
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, u1_indaga as U
    cortes = json.loads((DIR / "ELEGIBLES_USATECH.json").read_text())["cortes_nq"]
    ctx = GG.contexto_m1(F.bloques_nq_sellado(20261001, hasta, SELLADO, str(ACTA)), 0.25)
    res, cx = GG.correr(U, ctx, modo="REP", friccion=F.FUENTES["NQ"][2], extra_adverso=F.FUENTES["NQ"][3], cortes=cortes, celdas=[CELDA], log=print)
    GG.operaciones_de(cx, [CELDA]).to_csv(salida, index=False, lineterminator="\n")
    json.dump(dict(res, fuente="NQ_HOLDOUT", desde=20261001, hasta=hasta), open(Path(salida).with_suffix(".json"), "w"), indent=1, default=float)
    print("serie ->", salida)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("fase-b"); b.add_argument("--hasta", type=int, required=True); b.add_argument("--salida", default=str(DIR / "fase_b_operaciones.csv"))
    m = sp.add_parser("mirar"); m.add_argument("series", nargs="+")
    a = ap.parse_args()
    fase_b(a.hasta, a.salida) if a.cmd == "fase-b" else mirar(a.series)
