#!/usr/bin/env python3
"""Banco de eventos: muchos experimentos sobre una tabla de eventos, con exploración libre en la mitad A y pocas pruebas congeladas
en la mitad B. Documento: docs/research/BANCO_DE_EVENTOS.md. Módulo: edgelab/research/banco_eventos.py.

  python tools/banco_eventos.py generadores                 # qué kernels producen tablas con el contrato del banco
  python tools/banco_eventos.py plantilla > spec.json       # especificación vacía para completar
  python tools/banco_eventos.py validar   <spec.json>        # contrato de la especificación y de la tabla
  python tools/banco_eventos.py preflight <spec.json>        # validar + muestra por mitad + estratos + calibración contra permutaciones
  python tools/banco_eventos.py correr    <spec.json>        # preflight → registra → explora A → congela → prueba B → RECOMENDACIONES
  python tools/banco_eventos.py usos                         # libro de usos de la mitad B (una vez por familia y ventana)
Las especificaciones viven en docs/research/banco_eventos/specs/; los resultados en docs/research/banco_eventos/<nombre>/.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import banco_eventos as BE  # noqa: E402


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); return
    if a[0] == "generadores": print(json.dumps(BE.GENERADORES, indent=1, ensure_ascii=False)); return
    if a[0] == "plantilla": print(json.dumps(BE.PLANTILLA, indent=1, ensure_ascii=False)); return
    if a[0] == "usos":
        f = BE.DIR / "USOS.jsonl"; print(f.read_text(encoding="utf-8") if f.exists() else "(sin usos)"); return
    spec = BE.especificacion(a[1])
    try: T = BE.leer_tabla(spec)
    except FileNotFoundError:
        e = BE.validar(spec); print(f"la tabla {spec['tabla']} todavía no existe (¿el generador no corrió?). Especificación: "
                                    + ("OK" if not e else "; ".join(e))); sys.exit(1)
    if a[0] == "validar":
        e = BE.validar(spec, T); print("OK" if not e else "\n".join(e)); sys.exit(1 if e else 0)
    p = BE.preflight(spec, T); print(json.dumps(p, indent=1, ensure_ascii=False, default=float))
    if a[0] == "preflight": sys.exit(0 if p["ok"] else 1)
    if a[0] == "correr":
        if not p["ok"]: sys.exit("preflight en rojo: no se corre")
        out = BE.correr(spec, T)
        print(json.dumps(dict(nominadas=out["nominadas"], celdas_exploradas=out["celdas_exploradas"], pruebas_en_b=out["pruebas_en_b"]),
                         ensure_ascii=False))
        print("escrito", (BE.DIR / spec["nombre"]).relative_to(ROOT))


if __name__ == "__main__":
    main()
