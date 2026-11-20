#!/usr/bin/env python3
"""A20 NQ en el holdout terminal (desde la sesión CME del 2026-10-01), apertura pedida por Nico el 2026-11-20.
Adenda: docs/research/filtros_contexto_20261120/ADENDA_HOLDOUT_TERMINAL_A20.md. Calcula SÓLO si la apertura está registrada en
HOLDOUT_VENTANAS.jsonl. Reusa el kernel de NETO-PISTAS (`neto_pistas._ops/_cfg/_nombre`, fundedsyncstack); lee el M1 de NT8 sin el corte de
la frontera sólo después de verificar el registro.

  python tools/a20_terminal.py registrar   # registra la apertura (plan de potencia + autorización humana)
  python tools/a20_terminal.py calcular    # paridad del calentamiento, operaciones del terminal, lectura
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/filtros_contexto_20261120"
ADENDA = DIR / "ADENDA_HOLDOUT_TERMINAL_A20.md"
FAM, CID = "FUNDEDSYNC", "FUNDEDSYNC::holdout_terminal_A20_NQ"
DESDE, HASTA = 20261001, 20261116


def registrar():
    from edgelab.research import holdout_ventanas as HV
    p = HV.plan_potencia("fijo", 0.093, 2.36, n=30, fuente_efecto="mitad del +0,186 de 2022-01 → 2026-09 (NQ, elegido mirando la curva)")
    p["problemas_levantados_por_humano"] = p.pop("problemas") + HV.problemas(FAM, DESDE, CID)
    p.update(problemas=[], autorizacion="Nico 2026-11-20: «Luego de eso abrí el último holdout en el caso de que no haya nada que cambiar o "
             "probar en cuanto a filtros» (FILTROS-CONTEXTO = SIN_FILTRO; K27 y «una apertura por familia» levantadas para esta apertura; "
             "A20 nunca se calculó en el terminal)", hasta=HASTA, regla="A20_7_2_2.5_1.5", adenda=str(ADENDA.relative_to(ROOT)))
    libro = HV.LIBRO
    row = dict(tipo="apertura", familia=FAM, cid=CID, desde=DESDE, n_fijo=30, ts=__import__("time").time(),
               plan={k: v for k, v in p.items() if k != "problemas"})
    if any(r.get("cid") == CID for r in HV.leer(libro)): print("ya registrada"); return
    HV._exigir_alfa_reservado(FAM, p)
    with libro.open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False, indent=1))


def _m1_sin_corte(inst):
    """M1 de NT8 en hora de NY SIN el corte de la frontera: sólo se llama después de verificar la apertura registrada."""
    D = pd.read_parquet(ROOT / f"data/m1nt8/{inst}_M1_nonadj_utc.parquet")
    t = pd.DatetimeIndex(D.index if "datetime" not in D else D["datetime"]).astype("datetime64[ns]")
    ny = t.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    return pd.DataFrame(dict(o=D.open.to_numpy(float), h=D.high.to_numpy(float), l=D.low.to_numpy(float), c=D.close.to_numpy(float),
                             v=D.volume.to_numpy(float)), index=ny)


def calcular():
    from edgelab.research import holdout_ventanas as HV
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import sesion_excluida
    from m1_largo import _kernel_fs
    from neto_pistas import _ops, _cfg, _nombre, FABRICA
    if not any(r.get("cid") == CID for r in HV.leer(HV.LIBRO)): raise SystemExit("sin apertura registrada: no se calcula")
    D = _m1_sin_corte("NQ"); D = D[(D.index >= "2026-01-01")]
    ms = F.build_multi_series(F.load_m1_data(_kernel_fs(0.0)["a_utc"](D), end="2026-11-17"), tz_input="UTC")
    fab = _nombre("A20", FABRICA["A20"]); o = _ops(F, "A20", ms, D, _cfg("A20", FABRICA["A20"]))
    o["s"] = pd.to_datetime(o.ses).dt.strftime("%Y%m%d").astype(int)
    # paridad del calentamiento contra RZ_OPS (operaciones ya conocidas)
    rz = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); rz = rz[(rz.inst == "NQ") & (rz.variante == fab)]
    rz["s"] = pd.to_datetime(rz.ses).dt.strftime("%Y%m%d").astype(int); rz = rz[(rz.s >= 20260301) & (rz.s < DESDE)]
    w = o[(o.s >= 20260301) & (o.s < DESDE)]
    k1 = set(zip(pd.to_datetime(w.t).astype(str), w.side)); k2 = set(zip(pd.to_datetime(rz.t).astype(str), rz.side))
    m = w.merge(rz, on=["s", "side"], suffixes=("", "_rz")); m = m[pd.to_datetime(m.t) == pd.to_datetime(m.t_rz)]
    paridad = dict(calentamiento=len(w), rz=len(rz), entradas_iguales=len(k1 & k2), pnl_igual=int(np.isclose(m.pnl_pts, m.pnl_pts_rz).sum()))
    paridad["ok"] = bool(len(k1 & k2) >= 0.95 * max(len(k1), len(k2)) and paridad["pnl_igual"] >= 0.95 * len(k1 & k2))
    fr = float(friccion("NQ")[0])
    H = o[(o.s >= DESDE) & (o.s <= HASTA) & (o.riesgo > 0)].copy(); H = H[~H.s.map(lambda s: sesion_excluida("NQ", s))]
    H["R"] = (H.pnl_pts - fr) / H.riesgo; H = H.sort_values("t")
    s = H.groupby("s").R.sum(); rng = np.random.default_rng(20261120)
    bs = np.array([s.to_numpy()[rng.integers(0, len(s), len(s))].sum() for _ in range(10000)]) / len(H)
    p = float(((bs - H.R.mean()) >= H.R.mean()).mean()) if len(H) else 1.0                  # bootstrap centrado, una cola
    sd = float(H.R.std()) if len(H) > 1 else float("nan")
    res = dict(cid=CID, regla=fab, friccion=fr, paridad=paridad, n=int(len(H)), sesiones_con_op=int(H.s.nunique()), R_media=float(H.R.mean()),
               R_total=float(H.R.sum()), p_una_cola=p, sd=sd, mde80=float(2.49 * sd / np.sqrt(len(H))) if len(H) > 1 else None,
               aciertos=float((H.R > 0).mean()), por_semana={str(k): dict(n=int(len(g)), R=float(g.R.sum()))
                                                                for k, g in H.groupby(pd.to_datetime(H.ses).dt.to_period("W"))},
               por_mes={str(k): float(g.R.sum()) for k, g in H.groupby(pd.to_datetime(H.ses).dt.to_period("M"))})
    res["lectura"] = ("SIN_LECTURA_PARIDAD" if not paridad["ok"] else "CONFIRMA" if p < 0.05 and res["R_media"] > 0 else
                      "NO_CONCLUYENTE" if res["R_media"] > 0 else "EN_CONTRA_SIN_POTENCIA")
    H[["ses", "t", "side", "pnl_pts", "riesgo", "mae_pts", "R"]].to_csv(DIR / "A20_TERMINAL_OPS.csv", index=False)
    (DIR / "A20_TERMINAL.json").write_text(json.dumps(res, indent=1, ensure_ascii=False)); print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    {"registrar": registrar, "calcular": calcular}[sys.argv[1]]()
