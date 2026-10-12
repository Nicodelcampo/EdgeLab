#!/usr/bin/env python3
"""Genera candidatas (borradores) a partir de la evidencia propia, la literatura y los resultados vivos; las ordena por valor esperado de información.
  python tools/autopilot_generate.py draft [--runtime PATH] [--ledger PATH]    # escribe docs/research/autopilot/drafts/*.md + REPORT.md + candidates_proposed.json
  python tools/autopilot_generate.py promote --candidates /etc/edgelab/candidates.json CID [CID ...]   # SOLO con el borrador committeado: pasa los guards y agrega el RunSpec
La promoción la hace un humano (o un revisor) tras leer el borrador: el autopilot no se auto-aprueba candidatas."""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import guard
from edgelab.autopilot.generate import draft_prereg, generate, load_json, research_gaps, to_runspec
from edgelab.autopilot.ledger import RunLedger
from edgelab.autopilot.spec import RunSpec

D = ROOT / "docs/research/autopilot"


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("draft"); d.add_argument("--runtime"); d.add_argument("--ledger"); d.add_argument("--out", help="directorio de salida (por defecto docs/research/autopilot del repo)")
    p = sp.add_parser("promote"); p.add_argument("--candidates", required=True); p.add_argument("cids", nargs="+")
    a = ap.parse_args(); lits = load_json("config/autopilot/literature_leads.json")
    if a.cmd == "draft":
        global D
        if a.out: D = Path(a.out)
        outcomes = RunLedger(Path(a.ledger)).outcomes() if a.ledger else []
        cs = generate(outcomes, runtime=Path(a.runtime) if a.runtime else None); (D / "drafts").mkdir(parents=True, exist_ok=True)
        rep = ["# Candidatas generadas por el autopilot", "", "| # | id | puntuación | estudio | pruebas | dueño | por qué |", "|---|---|---:|---|---:|---|---|"]
        props, gaps = [], []
        for i, c in enumerate(cs, 1):
            (D / "drafts" / f"{c.cid}.md").write_text(draft_prereg(c, lits), encoding="utf-8"); rs = to_runspec(c)
            if rs: props.append(rs)
            gaps.append(research_gaps(c)); rep.append(f"| {i} | {c.cid} | {c.score:.4f} | {'listo' if c.template else 'NEEDS_SCRIPT'} | {c.n_trials} | {c.owner} | {c.why[:140]} |")
        (D / "REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
        (D / "candidates_proposed.json").write_text(json.dumps(props, indent=1), encoding="utf-8"); (D / "research_directives.json").write_text(json.dumps(gaps, indent=1), encoding="utf-8")
        print(f"{len(cs)} candidatas, {len(props)} con estudio listo → {D}")
    else:
        proposed = {r["run_id"]: r for r in json.loads((D / "candidates_proposed.json").read_text())}; path = Path(a.candidates)
        cur = json.loads(path.read_text()) if path.exists() else []; have = {c["run_id"] for c in cur}
        for cid in a.cids:
            r = proposed.get(cid.lower())
            if not r: print(f"{cid}: sin estudio listo (NEEDS_SCRIPT)"); continue
            errs = guard.all_checks(RunSpec.from_dict(r), allow_internet={r["script"]} if r["internet"] else set())
            if errs: print(f"{cid}: NO se promueve: {errs}"); continue
            if r["run_id"] not in have: cur.append(r)
            print(f"{cid}: promovida")
        path.write_text(json.dumps(cur, indent=1))
if __name__ == "__main__":
    main()
