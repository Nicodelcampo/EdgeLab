#!/usr/bin/env python3
"""Cola de corridas de SQX, un proyecto por vez (8 GB de RAM). Pre-registro: docs/research/sqx_lote2_20261116/PREREGISTRO.md.

  python tools/sqx_cola.py paso       # si no corre nada de la cola: registra el que terminó (estado) y lanza el siguiente
  python tools/sqx_cola.py comparar   # pares (real, nulo) terminados -> sqx/corridas/<real>/comparacion_nulo.json (edgelab/sqx_puente.py)

No lanza nada si StrategyQuantX.config no tiene -Xmx (el par del crudo murió por memoria el 15-nov). Reusa tools/sqx_corrida.py.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import mcp_cliente as MC  # noqa: E402
import sqx_corrida as SC  # noqa: E402

COLA = ROOT / "sqx/cola_lote2_20261116.json"


def _cola():
    return json.loads(COLA.read_text(encoding="utf-8"))


def paso():
    c = MC.Cliente("sqx"); cfg = c.llamar("read_file", {"path": "StrategyQuantX.config"}).get("content", "")
    if "-Xmx" not in cfg: print("BLOQUEADA: StrategyQuantX.config sin -Xmx (agregar 'option -Xmx5g' y reiniciar SQX)"); return
    for par in _cola()["pares"]:
        for cid in par:
            m = SC._cargar(cid)
            if m.get("estado") == "LANZADA":
                s = c.llamar("get_project_status", {"name": m["proyecto"]})
                if s.get("running"): print("corriendo", cid, s.get("strategiesGenerated")); return
                SC.estado(cid); print("terminó", cid)
            elif m.get("estado") != "TERMINADA":
                SC.lanzar(cid); print("lanzada", cid); return
    print("cola terminada")


def comparar():
    from edgelab import sqx_puente as P
    c = MC.Cliente("sqx")
    for real, nulo in _cola()["pares"]:
        mr, mn = SC._cargar(real), SC._cargar(nulo); f = ROOT / f"sqx/corridas/{real}/comparacion_nulo.json"
        if f.exists() or mr.get("estado") != "TERMINADA" or mn.get("estado") != "TERMINADA": continue
        res = P.comparar(P.t_por_estrategia(P.filas(c, mr["proyecto"])), P.t_por_estrategia(P.filas(c, mn["proyecto"])))
        res["generadas"] = dict(real=mr["ultimo_estado"].get("strategiesGenerated"), nulo=mn["ultimo_estado"].get("strategiesGenerated"))
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False)); print(real, {k: res[k] for k in ("umbral_max_nulo", "t_real", "candidatas")})


if __name__ == "__main__":
    {"paso": paso, "comparar": comparar}[sys.argv[1]]()
