#!/usr/bin/env python3
"""Ciclo diario de la cartera viva (docs/CARTERA_VIVA.md). Lo corre el Debian después del cierre de CME (timer
`deploy/debian/edgelab-cartera.timer`); también sirve a mano.

  python tools/cartera_diaria.py ciclo  --config config/cartera/cartera.json [--hasta 20261102]
  python tools/cartera_diaria.py estado --config config/cartera/cartera.json
  python tools/cartera_diaria.py cortes --config config/cartera/cartera.json --instrumento NQ      # congela los cortes de régimen (desarrollo)
  python tools/cartera_diaria.py alta   --config ... --estado <estado.json> --celda '[...]' --tope '["pts",50]' --preregistro <md>
                                        --desde 20261102 --perdida-max 50 --ganancia-max 200 --mu-util 2 --sd 15 [--confirmada]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.cartera import ciclo as CI, papel as PA, regimen as RG  # noqa: E402
from edgelab.cartera.ficha import Cartera, Ficha  # noqa: E402


def _lectores(cfg, cart):
    pre = {f.cid: str(ROOT / f.preregistro) for f in cart.fichas.values()}
    lec, ticks = {}, {}
    for nombre, d in (cfg.get("datos") or {}).items():
        lec[nombre], ticks[nombre] = PA.lector_mixto(nombre, d["desarrollo"], d.get("sellado"), pre)
    return lec, ticks


def _diarios(cfg, lec, ticks, hasta):
    from edgelab.research import grilla_generica as GG
    out = {}
    for inst in (cfg.get("cortes_regimen") or {}):
        if inst not in lec: continue
        ctx = GG.contexto_m1(lec[inst](PA._menos_dias(hasta, cfg.get("dias_regimen", 140)), hasta, dict(cid="__regimen__")), ticks[inst])
        out[inst] = RG.diario_desde_m1(ctx)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("ciclo", "estado", "cortes", "alta")); ap.add_argument("--config", required=True)
    ap.add_argument("--hasta", type=int); ap.add_argument("--instrumento"); ap.add_argument("--estado"); ap.add_argument("--celda")
    ap.add_argument("--tope"); ap.add_argument("--preregistro"); ap.add_argument("--desde", type=int); ap.add_argument("--perdida-max", type=float)
    ap.add_argument("--ganancia-max", type=float); ap.add_argument("--margen-hueco", type=float, default=0.0); ap.add_argument("--mu-util", type=float)
    ap.add_argument("--sd", type=float); ap.add_argument("--confirmada", action="store_true"); ap.add_argument("--id")
    a = ap.parse_args(); cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    cart = Cartera(Path(cfg["cartera"]), reglas=cfg.get("reglas"), libro_ventanas=cfg.get("libro_ventanas"))
    if a.cmd == "estado":
        for f in cart.fichas.values(): print(f.id, f.nivel, f.estado, len(f.ops), round(sum(x for _, x in f.ops), 2), f.motivo or "")
        return
    if a.cmd == "alta":
        from edgelab.costos import friccion_rt_puntos
        st = json.loads(Path(a.estado).read_text(encoding="utf-8")); sp = st["spec"]; inst = sp.get("ejecucion") or sp["sensor"]
        f = Ficha(id=a.id or sp["cid"], familia=sp["familia"], cid=sp["cid"], instrumento=inst,
                  regla=dict(spec=dict(experimento=sp["experimento"], sensor=sp["sensor"], ejecucion=inst, familia=sp["familia"],
                                       datasets_extra=sp.get("datasets_extra", [])), celda=json.loads(a.celda), cortes=st.get("cortes") or {},
                             tope=json.loads(a.tope) if a.tope else None),
                  preregistro=a.preregistro, perdida_max_pts=a.perdida_max, ganancia_max_pts=a.ganancia_max, margen_hueco_pts=a.margen_hueco,
                  friccion_pts=friccion_rt_puntos(inst), mu_util=a.mu_util, sd_desarrollo=a.sd, desde=a.desde, confirmada_por_embudo=a.confirmada)
        print(json.dumps(dict(id=cart.alta(f, ROOT).id, nivel=f.nivel), ensure_ascii=False)); return
    lec, ticks = _lectores(cfg, cart)
    hasta = a.hasta or CI.sesion_cerrada()
    if a.cmd == "cortes":
        d = _diarios(dict(cfg, cortes_regimen={a.instrumento: None}, dias_regimen=400), lec, ticks, 20260331)[a.instrumento]
        print(json.dumps(RG.congelar_cortes(RG.rasgos_diarios(d), 20260331))); return
    from edgelab.research.embudo_runners import LocalRunner
    runner = LocalRunner(lec, ticks, acta_requerida=False, carpeta=Path(cfg["salida"]) / "_runs")
    fills = [json.loads(l) for l in Path(cfg["fills"]).read_text(encoding="utf-8").splitlines() if l.strip()] if cfg.get("fills") and Path(cfg["fills"]).exists() else None
    plan = CI.correr(cfg, hasta, _diarios(cfg, lec, ticks, hasta), runner=runner, fills=fills, repo=ROOT)
    print(json.dumps(dict(hasta=hasta, modo_seguro=plan.get("modo_seguro"), retiros=len(plan.get("retiros_hoy", [])),
                          p0=sum(x["prioridad"] == "P0" for x in plan.get("cola_investigacion", []))), ensure_ascii=False))


if __name__ == "__main__":
    main()
