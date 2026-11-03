#!/usr/bin/env python3
"""Nominación forzada al holdout (relanzamiento_causal_20261102/PREREGISTRO_NOMINACION_FORZADA.md, decisión de Nico): por familia del
relanzamiento causal que termina sin candidata, la pista de réplica con n >= 30, media de réplica > 0 y media de DESC > 0 de mayor cota
inferior del IC90 (desempate: media). Escribe su ACTA_HOLDOUT.json (N fijo 150, sin tope, paso de LORD++ reservado ANTES de mirar).
  python tools/nominacion_forzada.py            # sólo informa
  python tools/nominacion_forzada.py --actas    # además reserva LORD++ y escribe las actas de las elegidas
  python tools/nominacion_forzada.py --raiz docs/research/relanzamiento_R_20261102/embudo --cota-min 0 --solo TORI-NQ-R CONF-CVR-CFD-NQ-R \
      --pre docs/research/PREREGISTRO_NOMINACION_FORZADA_R_20261103.md --actas
      # 2026-11-03 (Nico): la misma regla sobre las campañas en R, con la cota inferior del IC90 de réplica > 0
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
RAIZ = ROOT / "docs/research/relanzamiento_causal_20261102/embudo"
PRE = "docs/research/relanzamiento_causal_20261102/PREREGISTRO_NOMINACION_FORZADA.md"
N_MIN, N_FIJO = 30, 150


COTA_MIN = None


def elegir(st):
    if st.get("etapa") != "FIN": return None, "sin terminar"
    pistas = (st.get("desc") or {}).get("pistas") or []
    if any(p.get("nominada_replica") for p in pistas): return None, "el embudo ya nominó"
    ok = []
    for p in pistas:
        r = p.get("replica_pistas") or {}; ic = r.get("ic90") or [None, None]; md = p.get("media_neta", p.get("media"))
        if (r.get("n") or 0) >= N_MIN and (r.get("media") or 0) > 0 and (md is None or md > 0) and ic[0] is not None \
                and (COTA_MIN is None or ic[0] > COTA_MIN):
            ok.append((ic[0], r["media"], p))
    if not ok: return None, f"ninguna pista cumple (n >= {N_MIN}, réplica > 0, DESC > 0)"
    ok.sort(key=lambda t: (t[0], t[1]), reverse=True); return ok[0][2], "elegida"


def main(actas, solo=None):
    from edgelab.funnel.libro_lord import LibroLord
    out = []
    for f in sorted(RAIZ.glob("*/estado.json")):
        st = json.loads(f.read_text()); cid = f.parent.name
        if solo and cid not in solo: continue
        p, motivo = elegir(st)
        fila = dict(cid=cid, etapa=st.get("etapa"), fase=st.get("fase"), motivo=motivo)
        if p:
            r = p["replica_pistas"]; fila.update(celda=p["celda"], media_desc=p.get("media_neta", p.get("media")), n_rep=r["n"], media_rep=r["media"], ic90_rep=r["ic90"])
            acta_f = f.parent / "ACTA_HOLDOUT.json"
            if actas and not acta_f.exists():
                fam = st["spec"]["familia"]; res = LibroLord().reservar(fam, f"{cid}/holdout_forzada", f"nominación forzada {cid} (Nico 2026-11-02)")
                acta = dict(cid=cid, familia=fam, experimento=st["spec"]["experimento"], sensor=st["spec"]["sensor"], ejecucion=st["spec"].get("ejecucion"),
                            cortes=st.get("cortes"), holdout_desde=20261001, n_fijo=N_FIJO, alfa=res["nivel"], registrada=time.time(), reserva_lord=res,
                            regla=dict(celda=p["celda"], tope=None), nominacion="FORZADA (excepción humana, sin confirmación en réplica)", preregistro=PRE,
                            decision=f"primeras {N_FIJO} operaciones desde 20261001: el paso RESERVADO de LORD++ de la familia (α={res['nivel']:.5f}); "
                                     "CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA")
                acta_f.write_text(json.dumps(acta, indent=1, ensure_ascii=False)); fila["acta"] = str(acta_f.relative_to(ROOT))
        out.append(fila)
    (RAIZ.parent / "NOMINACION_FORZADA.json").write_text(json.dumps(out, indent=1, default=float)); return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--actas", action="store_true"); ap.add_argument("--raiz"); ap.add_argument("--pre")
    ap.add_argument("--cota-min", type=float); ap.add_argument("--solo", nargs="*"); a = ap.parse_args()
    if a.raiz: RAIZ = ROOT / a.raiz
    if a.pre: PRE = a.pre
    COTA_MIN = a.cota_min
    for r in main(a.actas, a.solo): print(r)
