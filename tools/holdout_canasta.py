#!/usr/bin/env python3
"""Holdout de la CANASTA de pistas de una familia que terminó PISTAS_VIVAS (decisión de Nico, 2026-10-26, auditoría del filtro:
`docs/research/auditoria_filtro_20261026/AUDITORIA_FILTRO_PISTAS.md`, propuesta 4).

  python tools/holdout_canasta.py acta    <raiz_embudo> <CID> --n-sesiones N      # congela la regla y reserva α ANTES de mirar
  python tools/holdout_canasta.py conteo  <raiz_embudo> <CID> --sellado '{...}'    # sólo cuántas sesiones hay (sin P&L)
  python tools/holdout_canasta.py decidir <raiz_embudo> <CID> --sellado '{...}'    # con >= N sesiones: un paso de LORD++ reservado

Regla congelada: las k celdas de la réplica de pistas (con los cortes del DESC), P&L neto medio por pista y sesión (canasta igual-
ponderada, `escalera.canasta_pistas`), sobre las primeras N sesiones del holdout desde la frontera única. Una apertura por familia
(`holdout_ventanas`); el acta reserva el paso de LORD++ de la familia (`LibroLord.reservar`) y la decisión lo resuelve. Datos del holdout
sólo en el Debian (carpeta sellada) con `--sellado` (mismo formato que `tools/embudo_correr.py`).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.libro_lord import LibroLord  # noqa: E402
from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT  # noqa: E402


def _estado(raiz: Path, cid: str) -> dict:
    return json.loads((raiz / cid / "estado.json").read_text(encoding="utf-8"))


def potencia_planeada(st: dict, n_sesiones: int, nivel: float) -> float:
    """Potencia del holdout de la canasta a N sesiones, con la media y el desvío por sesión de su réplica (planificación, no decisión)."""
    from edgelab.funnel.escalera import potencia
    can = (st.get("pistas_replica") or {}).get("canasta") or {}
    if not can.get("ic90") or not can.get("n_sesiones") or (can.get("media") or 0) <= 0: return 0.0
    sd = (can["ic90"][1] - can["ic90"][0]) / (2 * 1.6448536) * can["n_sesiones"] ** 0.5
    return float(potencia(can["media"], sd / max(n_sesiones, 1) ** 0.5, nivel))


def acta(raiz: Path, cid: str, n_sesiones: int, libro=None, ventanas=None, registro=None, ahora=time.time, forzar: bool = False) -> dict:
    from edgelab.research import holdout_ventanas as HV
    st = _estado(raiz, cid); spec = st["spec"]; fam = spec["familia"]
    if st.get("fase") != "PISTAS_VIVAS": raise SystemExit(f"{cid} está en {st.get('fase')}: sólo PISTAS_VIVAS va a holdout de canasta")
    destino = raiz / cid / "ACTA_HOLDOUT_CANASTA.json"
    if destino.exists(): raise SystemExit(f"ya hay acta: {destino}")
    libro_v = Path(ventanas) if ventanas else HV.LIBRO; id_ = f"{cid}-CANASTA"
    h_desde = max(HOLDOUT_PRIMERA_SESION_INT, int((spec.get("holdout") or {}).get("desde") or HOLDOUT_PRIMERA_SESION_INT))
    if (malos := HV.problemas(fam, h_desde, id_, libro_v)): raise SystemExit("; ".join(malos))
    pot = potencia_planeada(st, n_sesiones, (libro or LibroLord()).nivel(fam))
    if pot < 0.8 and not forzar:                                                # E8: no gastar la única apertura sin poder decidir
        raise SystemExit(f"potencia {pot:.2f} < 0,8 con N {n_sesiones} (con la media y el desvío de la réplica de la canasta): subir N o "
                         "ganar potencia antes; --forzar sólo con decisión humana registrada")
    lib = libro or LibroLord(); res = lib.reservar(fam, f"{id_}/holdout", f"acta canasta {cid}")
    a = dict(cid=id_, campana=cid, familia=fam, experimento=spec["experimento"], sensor=spec["sensor"], ejecucion=spec.get("ejecucion"),
             celdas=st["pistas_replica"]["celdas"], cortes=st["cortes"], regla="canasta igual-ponderada: P&L neto medio por pista y sesión",
             holdout_desde=h_desde, n_sesiones=int(n_sesiones), alfa=res["nivel"], reserva_lord=res, registrada=ahora(),
             potencia_planeada=pot, forzada=bool(forzar),
             decision=(f"primeras {n_sesiones} sesiones desde {h_desde}: CONFIRMADA si p (bootstrap por sesiones) <= α "
                       f"reservado ({res['nivel']:.5f}) y media > 0; REFUTADA si media <= 0; si no, SIN_POTENCIA"),
             origen="docs/research/auditoria_filtro_20261026/AUDITORIA_FILTRO_PISTAS.md (propuesta 4, aprobada por Nico)")
    destino.write_text(json.dumps(a, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    HV.registrar_apertura(fam, id_, h_desde, int(n_sesiones), libro_v)
    if registro is not None: registro.ensure(f"embudo/{cid}/holdout_canasta", fam, 1, f"apertura de holdout: canasta de pistas de {cid}")
    return a


def _canasta(raiz: Path, cid: str, sellado: dict, solo_conteo: bool):
    from edgelab.funnel.escalera import canasta_pistas
    from edgelab.research import embudo_runners as ER
    a = json.loads((raiz / cid / "ACTA_HOLDOUT_CANASTA.json").read_text(encoding="utf-8"))
    lec, tk = ER.lectores_sellados(sellado, raiz); run = ER.LocalRunner(lec, tk, carpeta=raiz / "_local")
    spec = dict(_estado(raiz, cid)["spec"])
    hasta = int(time.strftime("%Y%m%d", time.gmtime(time.time() - 86400)))
    if solo_conteo:                                                             # sin P&L: sólo las sesiones con datos de la ejecución
        ejec = spec.get("ejecucion") or spec["sensor"]
        n = len({int(b.sesion.iloc[0]) for b in lec[ejec](a["holdout_desde"], hasta, spec) if len(b)})
        return a, n, None
    h = run.lanzar(spec, "REP", dict(cortes=a["cortes"], celdas=a["celdas"]), [a["holdout_desde"], hasta]); res = run.traer(h)
    import pandas as pd
    o = pd.DataFrame(res.get("operaciones") or {})
    sesiones = sorted(o.ses.unique().tolist()) if len(o) else []
    usar = set(sesiones[: a["n_sesiones"]])
    o = o[o.ses.isin(usar)]
    return a, len(sesiones), canasta_pistas(o.to_dict("list"), len(a["celdas"]), n_boot=10000)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("acta", "conteo", "decidir")); ap.add_argument("raiz"); ap.add_argument("cid")
    ap.add_argument("--n-sesiones", type=int); ap.add_argument("--sellado", default="{}"); ap.add_argument("--forzar", action="store_true")
    a = ap.parse_args(); raiz = Path(a.raiz)
    if a.cmd == "acta":
        from edgelab.funnel.multiplicity import TrialRegistry
        out = acta(raiz, a.cid, a.n_sesiones, registro=TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"), forzar=a.forzar)
    elif a.cmd == "conteo":
        acta_, n, _ = _canasta(raiz, a.cid, json.loads(a.sellado), True); out = dict(sesiones=n, faltan=max(0, acta_["n_sesiones"] - n))
    else:
        acta_, n, can = _canasta(raiz, a.cid, json.loads(a.sellado), False)
        if n < acta_["n_sesiones"]: raise SystemExit(f"faltan {acta_['n_sesiones'] - n} sesiones: no se decide antes de N")
        dec = LibroLord().resolver(acta_["familia"], f"{acta_['cid']}/holdout", [("canasta", can["p"])])
        ver = "CONFIRMADA" if dec.get("rechazo") and can["media"] > 0 else ("REFUTADA" if can["media"] <= 0 else "SIN_POTENCIA")
        out = dict(veredicto=ver, canasta=can, lord=dec)
        (raiz / a.cid / "HOLDOUT_CANASTA_RESULTADO.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
