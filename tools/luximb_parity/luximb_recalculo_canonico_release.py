#!/usr/bin/env python3
"""Recálculo del candidato LUX-IMB (regla del visor, congelada el 2026-10-21) sobre el release canónico de Kaggle con costos canónicos.

Pre-registro: docs/research/luximb_parity_20261020/PREREGISTRO_RECALCULO_CANONICO_RELEASE_20261024.md
- Datos: SOLO `data/NQ_ticks.parquet` de `nicolasbuttaro/edgelab-liquid-ticks-20261014` (liquid_tick_v1 v4), verificado por sha256
  contra `release_manifest.json`. El release no tiene holdout; igual se aborta si alguna sesión es >= 2026-10-01.
- Un bundle por contrato con la ventana de trade_date que el release le asigna (estadísticas de row group), con el constructor
  de siempre (`build_luximb_nq_m1_bundle.py`).
- Operaciones: `escalera_candidatos_20261022.lux_trades` (la misma regla y la misma contabilidad que la escalera del 22/10).
- Costos: sólo `edgelab.costos` (fricción NQ base y adverso). Escalera: `edgelab.funnel.escalera`, sin parámetros nuevos.

  python tools/luximb_parity/luximb_recalculo_canonico_release.py <release_dir> <scratch_dir> <out.json>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools")); sys.path.insert(0, str(HERE))
from edgelab import costos  # noqa: E402
from edgelab.funnel import escalera as E  # noqa: E402
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402
from escalera_candidatos_20261022 import PUBLICADO_LUX, a_r, lux_trades  # noqa: E402

HOLDOUT_TD = 20261001
FRIC, FRIC_ADV = costos.friccion_rt_puntos("NQ"), costos.friccion_rt_puntos("NQ", "adverso")
ESCALERA_1022 = REPO / "docs/research/auditoria_embudo_20261022/ESCALERA_CANDIDATOS_REALES.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""): h.update(b)
    return h.hexdigest()


def ventanas(pq_path: Path) -> dict:
    pf = pq.ParquetFile(pq_path); md = pf.metadata
    ci = {md.row_group(0).column(i).path_in_schema: i for i in range(md.row_group(0).num_columns)}
    out = {}
    for rg in range(md.num_row_groups):
        g = md.row_group(rg); td, ct = g.column(ci["trade_date"]).statistics, g.column(ci["contract"]).statistics
        if str(ct.min) != str(ct.max): raise SystemExit(f"row group {rg} mezcla contratos")
        w = out.setdefault(str(ct.min), [td.min, td.max]); w[0] = min(w[0], td.min); w[1] = max(w[1], td.max)
    return out


def main():
    rel, scratch, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); scratch.mkdir(parents=True, exist_ok=True)
    man = json.load(open(rel / "release_manifest.json", encoding="utf-8")); a = man["assets"]["NQ"]; nq = rel / a["file"]
    sha = sha256(nq)
    if sha != a["sha256"]: raise SystemExit(f"sha256 de {nq.name} no coincide con el manifiesto")
    if a["last_trade_date"] >= HOLDOUT_TD: raise SystemExit("el release declara sesiones del holdout")
    win = ventanas(nq)
    if max(w[1] for w in win.values()) >= HOLDOUT_TD: raise SystemExit("hay sesiones del holdout en el archivo")
    per, todas = {}, []
    for contrato, (d0, d1) in win.items():
        c = contrato.split(" ")[1]; bdir = scratch / "bundles"; bp = bdir / f"NQ_{c}_M1_LUXIMB.json"
        if not bp.exists():
            subprocess.run([sys.executable, "-X", "utf8", str(HERE / "build_luximb_nq_m1_bundle.py"), str(nq), contrato, str(d0), str(d1), str(bdir), "0.25"],
                           check=True, cwd=REPO)
        ops = lux_trades(bp, scratch); [o.update(periodo=c) for o in ops]; todas += ops
        n_pub, pts_pub = PUBLICADO_LUX.get(c, (None, None))
        per[c] = dict(ventana_trade_date=[d0, d1], n=len(ops), pts_contab_campania=round(sum(o["pts_pub"] for o in ops), 1),
                      neto_canonico_pts=round(sum(o["bruto"] - FRIC for o in ops), 1),
                      neto_canonico_pts_por_op=round(float(np.mean([o["bruto"] - FRIC for o in ops])), 3) if ops else None,
                      tp=sum(o["why"] == "TP" for o in ops), sl=sum(o["why"] == "SL" for o in ops), tiempo=sum(o["why"] == "tiempo" for o in ops),
                      publicado_1020=dict(n=n_pub, pts=pts_pub))
        print("LUX", c, per[c], flush=True)
    x = a_r(todas, FRIC); xa = a_r(todas, FRIC_ADV); ses = [o["sesion"] for o in todas]
    pts = np.array([o["bruto"] - FRIC for o in todas]); pts_adv = np.array([o["bruto"] - FRIC_ADV for o in todas])
    d = E.resumen_sesiones(x, ses); dp = E.resumen_sesiones(pts, ses)
    g = TrialRegistry(REPO / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl")
    fam = sum(r["n_trials"] for r in g._rows() if r["family_id"] == "LUXIMB_FADE_VISOR")
    prog = sum(r["n_trials"] for r in g._rows() if str(r["family_id"]).startswith("LUXIMB"))
    eco = E.economia(x, xa, ses, periodos=[o["periodo"] for o in todas])
    v = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=fam, efecto_util=0.0, economico=eco)
    v_prog = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=prog, efecto_util=0.0, economico=eco)
    prev = json.load(open(ESCALERA_1022, encoding="utf-8"))["lux_imb"]
    res = dict(regla="LUX-IMB fade, TP 1,0·D / SL 0,2·D, entrada cierre -1 tick, tope 240 min (congelada, luximb_holdout_regla_visor.py sha256 3c44bc32...)",
               estado_datos="PROVISIONAL (release CANDIDATE_NOT_RESEARCH_APPROVED)",
               datos=dict(dataset="nicolasbuttaro/edgelab-liquid-ticks-20261014", release_id=man.get("release_id"), archivo=a["file"], sha256=sha,
                          sesiones_manifiesto=a["sessions"], rango=[a["first_trade_date"], a["last_trade_date"]]),
               costos=costos.desglose("NQ"), friccion_base_pts=FRIC, friccion_adversa_pts=FRIC_ADV,
               por_periodo=per, n_ops=len(todas), n_sesiones=len(set(ses)),
               media_pts_contab_campania=float(np.mean([o["pts_pub"] for o in todas])),
               media_pts_neto_canonico=float(pts.mean()), media_pts_neto_adverso=float(pts_adv.mean()),
               pts_neto_canonico_sesiones=dp, n_pruebas_familia=fam, n_pruebas_programa_luximb=prog,
               veredicto_familia=v.to_dict(), veredicto_programa=v_prog.to_dict(),
               comparacion_escalera_1022=dict(n_ops=prev["veredicto_familia"]["numeros"]["descubrimiento"]["n_ops"],
                                              media_pts_canonica=prev["media_pts_canonica"], estado=prev["veredicto_familia"]["estado"],
                                              datos="bundles locales (viewer/nt8_bridge/bundles), no versionados"))
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(dict(n=len(todas), pts_canon=round(float(pts.mean()), 3), estado=v.estado if hasattr(v, "estado") else v.to_dict()["estado"],
                          motivos=v.to_dict()["motivos"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
