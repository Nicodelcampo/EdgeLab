#!/usr/bin/env python3
"""Índice de FAMILIAS de investigación: un renglón por familia con su linaje, pruebas contadas, campañas, último desenlace del embudo
y entradas en el registro de factores. Se GENERA de lo que ya existe (LINAJES.jsonl, TRIAL_REGISTRY_GLOBAL.jsonl, campañas de
config/autopilot/grillas/campanas, MEDIDO.md de cada embudo, FACTORES.jsonl); no mueve ni renombra nada.
  python tools/familias.py            # imprime
  python tools/familias.py --write    # regenera docs/research/FAMILIAS.md
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; R = ROOT / "docs/research"
SALIDA = R / "FAMILIAS.md"


def _jsonl(f):
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def tabla() -> list:
    fam = defaultdict(lambda: dict(padres=[], registrada="", pruebas=0, campanas=[], desenlaces=[], carpetas=set(), factores=[]))
    for l in _jsonl(R / "LINAJES.jsonl"):
        f = fam[l["familia"]]; f["padres"] = l.get("padres") or []; f["registrada"] = l.get("registrada", "")
        for m in re.findall(r"docs/research/([\w\-]+)/", l.get("justificacion", "")): f["carpetas"].add(m)
    for l in _jsonl(R / "TRIAL_REGISTRY_GLOBAL.jsonl"):
        fam[l["family_id"]]["pruebas"] += int(l.get("n_trials") or 0)
    cid_fam = {}
    for c in sorted((ROOT / "config/autopilot/grillas/campanas").glob("*.json")):
        try: d = json.loads(c.read_text(encoding="utf-8"))
        except ValueError: continue
        if d.get("familia"): cid_fam[d.get("cid", c.stem)] = d["familia"]; fam[d["familia"]]["campanas"].append(d.get("cid", c.stem))
    for m in sorted(R.glob("**/embudo/*/MEDIDO.md")):
        f = cid_fam.get(m.parent.name)
        if not f: continue
        finales = re.findall(r"^- \*\*([A-Z_]+)\*\*", m.read_text(encoding="utf-8"), flags=re.M)
        if finales: fam[f]["desenlaces"].append(f"{m.parent.name}: {finales[-1]}")
        fam[f]["carpetas"].add(m.relative_to(R).parts[0])
    for e in _jsonl(R / "FACTORES.jsonl"):
        for p in e["evidencia"]:
            for k, f in fam.items():
                if any(p.startswith(f"docs/research/{c}/") for c in f["carpetas"]): f["factores"].append(f"{e['id']} ({e['estado']})")
    return [dict(familia=k, **{a: (sorted(v[a]) if isinstance(v[a], set) else v[a]) for a in v}) for k, v in sorted(fam.items())]


def markdown() -> str:
    T = tabla()
    L = ["# Familias de investigación — índice único", "",
         "Estado: VIGENTE (GENERADO con `python tools/familias.py --write`; no editar a mano).", "",
         f"{len(T)} familias. Para saber qué vale la pena de cada una: `docs/research/FACTORES_CON_VENTAJA.md`. Una familia sin desenlace",
         "no pasó por el embudo automático (fue una medición puntual: ver su carpeta).", "",
         "| Familia | Registrada | Padres | Pruebas contadas | Campañas | Último desenlace del embudo | Factores | Carpetas |", "|---|---|---|---|---|---|---|---|"]
    for f in T:
        des = "; ".join(sorted(set(f["desenlaces"]))[:4]) + (" …" if len(set(f["desenlaces"])) > 4 else "")
        L.append(f"| `{f['familia']}` | {f['registrada']} | {', '.join(f['padres']) or '—'} | {f['pruebas'] or '—'} | {len(f['campanas']) or '—'} | {des or '—'} | "
                 f"{'; '.join(sorted(set(f['factores']))) or '—'} | {', '.join('`' + c + '`' for c in f['carpetas'][:3]) or '—'} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv: SALIDA.write_text(markdown(), encoding="utf-8"); print("escrito", SALIDA.relative_to(ROOT))
    else: print(markdown())
