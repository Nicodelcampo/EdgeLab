#!/usr/bin/env python3
"""Corre el embudo automático sobre una o más campañas hasta que terminan o quedan esperando datos del holdout (mismo código que
usa el ciclo del Debian; útil para correrlo desde una máquina de trabajo).

  python tools/embudo_correr.py config/autopilot/grillas/campanas/EXPZ-NQ.json [...] --raiz <estado>
         [--sellado '{"DK:USATECHIDXUSD": "...", "NQ": "..."}'] [--intervalo 300] [--conductor local] [--ventanas <libro>]
El libro de LORD++ es el único canónico (decisión 2026-10-24). Sólo conduce campañas que declaran `"conductor"` igual a
`--conductor` (por defecto `local`): una campaña con `"conductor": "debian"` la conduce el ciclo del Debian y correrla
también acá relanzaría sus kernels (auditoría 2026-10-24).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.libro_lord import LibroLord  # noqa: E402
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402
from edgelab.research import embudo as EMB, embudo_runners as ER  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("campanas", nargs="+"); ap.add_argument("--raiz", required=True);
    ap.add_argument("--sellado", default="{}"); ap.add_argument("--intervalo", type=int, default=300); ap.add_argument("--max-errores", type=int, default=5)
    ap.add_argument("--registro", default=str(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"))
    ap.add_argument("--conductor", default="local", choices=EMB.CONDUCTORES)
    ap.add_argument("--ventanas", default=None, help="libro de ventanas del holdout (por defecto el del repo)")
    a = ap.parse_args()
    lec, tk = ER.lectores_sellados(json.loads(a.sellado), Path(a.raiz))
    emb = EMB.Embudo(Path(a.raiz), dict(kaggle=ER.KaggleRunner(raiz=Path(a.raiz)), local=ER.LocalRunner(lec, tk, carpeta=Path(a.raiz) / "_local")),
                     registro=TrialRegistry(Path(a.registro)), libro=LibroLord(), ventanas=a.ventanas)   # libro único: RUTA_CANONICA
    specs = [json.loads(Path(c).read_text(encoding="utf-8")) for c in a.campanas]
    if (ajenas := [s["cid"] for s in specs if s.get("conductor") != a.conductor]):
        sys.exit(f"NO SE CONDUCE: {ajenas} no declaran \"conductor\": \"{a.conductor}\" (un solo conductor por campaña)")
    vivas = {s["cid"] for s in specs}; errores = {}
    while vivas:
        for s in specs:
            if s["cid"] not in vivas: continue
            try: st = emb.avanzar(s); errores[s["cid"]] = 0
            except Exception as e:                    # un corte de red no abandona la campaña: se reintenta en la vuelta siguiente
                errores[s["cid"]] = errores.get(s["cid"], 0) + 1
                print(time.strftime("%H:%M:%S"), s["cid"], f"ERROR {errores[s['cid']]}/{a.max_errores}", repr(e)[:400], flush=True)
                if errores[s["cid"]] >= a.max_errores: vivas.discard(s["cid"])
                continue
            print(time.strftime("%H:%M:%S"), s["cid"], st["etapa"], st.get("fase"), st.get("motivo", ""), flush=True)
            if st["etapa"] == "FIN" or (st["etapa"] == "CONTEO" and st.get("ultimo_conteo")): vivas.discard(s["cid"])
        if vivas: time.sleep(a.intervalo)


if __name__ == "__main__":
    main()
