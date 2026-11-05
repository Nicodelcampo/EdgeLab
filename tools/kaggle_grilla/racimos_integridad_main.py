# Integridad target-free del sellado de U1-RACIMOS-GRILLA-NQ (canasta v3, ACTA_APERTURA_V3_20261102.md, "integridad por revisar").
# Sin P&L: cuenta, por sesión, ticks NQ sellados y racimos de la definición congelada (zona 9, racimo 1) en el sellado, y los
# mismos racimos por sesión en el almacén de desarrollo (jul-sep 2026), para ver si la falta de operaciones antes del 10-13 es
# dato/calentamiento o mercado.
import glob
import json
import os

import numpy as np
import pandas as pd


def main():
    from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS
    from edgelab.research import fuentes_ticks as F, u1_racimos_grilla as R
    ent = os.environ.get("ENTRADA", "/kaggle/input"); os.environ["SELLADO"] = "1"
    os.environ["PARAMS"] = json.dumps(dict(celdas=[[1, 0, 0, 9, 1, 0]])); os.environ["HASTA"] = "20261030"
    open("ACTA_HOLDOUT.json", "w").write(json.dumps(dict(acta=ACTA_REF))); os.environ["ACTA_HOLDOUT_RUTA"] = os.path.abspath("ACTA_HOLDOUT.json")
    r = sorted(glob.glob(f"{ent}/**/NQ_*ticks.parquet", recursive=True))
    ticks = {int(b.sesion.iloc[0]): int(len(b)) for b in F.bloques_nq_sellado(F.HOLDOUT_PRIMERA_SESION_INT, 20261030, r, os.environ["ACTA_HOLDOUT_RUTA"], 0.25)}
    Zs = R._racimos_sellados("NQ", ent); Zs = Zs[(Zs.zona == 9) & (Zs.racimo == 1)]
    sell = pd.Series(F._td(Zs.t_ns.to_numpy())).value_counts().sort_index()
    f = glob.glob(f"{ent}/**/ZONAS_AVZRG_NQ.parquet", recursive=True)
    Zd = pd.read_parquet(f[0], columns=["t_ns", "zona", "racimo"]); Zd = Zd[(Zd.zona == 9) & (Zd.racimo == 1)]
    ultimo = int(Zd.t_ns.max()); Zd = Zd[(Zd.t_ns >= pd.Timestamp("2026-07-01", tz="UTC").value) & (Zd.t_ns < HOLDOUT_APERTURA_UTC_NS)]
    dev = pd.Series(F._td(Zd.t_ns.to_numpy())).value_counts().sort_index()
    out = dict(ticks_sellado_por_sesion=ticks, racimos_sellado_por_sesion={int(k): int(v) for k, v in sell.items()},
               racimos_dev_por_sesion_jul_sep={int(k): int(v) for k, v in dev.items()},
               dev_media_por_sesion=float(dev.mean()) if len(dev) else 0.0, dev_sesiones_con_racimo=int(len(dev)),
               almacen_dev_ultimo_t_ns=ultimo, frontera_ns=int(HOLDOUT_APERTURA_UTC_NS))
    json.dump(out, open("RACIMOS_INTEGRIDAD.json", "w"), indent=1); print(json.dumps({k: v for k, v in out.items() if "por_sesion" not in k}))
    print("sellado", out["racimos_sellado_por_sesion"])


ACTA_REF = "docs/research/canasta_7_20261030/ACTA_APERTURA_V3_20261102.md"
main()
