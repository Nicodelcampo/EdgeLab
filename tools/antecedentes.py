#!/usr/bin/env python3
"""Ficha de antecedentes de una idea y presupuesto de datos de su linaje, en una página (AUTOMATIZACION_PROCESOS_20261111 R1/R2).
Reemplaza la docena de búsquedas a mano del diseño: familias parecidas y su último desenlace, factores (sobre todo NO_REPETIR),
documentos, código reutilizable, ventanas del holdout ya consumidas y datos que el linaje todavía no miró.

  python tools/antecedentes.py "expansiones luxalgo OG VI 25% inicial"            # ficha
  python tools/antecedentes.py "..." --familia LUXIMB_HVN                          # + presupuesto de datos de esa familia y su linaje
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
R = ROOT / "docs/research"
VACIAS = {"de", "la", "el", "los", "las", "en", "con", "por", "para", "que", "una", "uno", "sin", "del", "más", "mas", "y", "o", "a"}
# Ventanas de datos estándar del repo (fuentes_ticks y catálogo). «limpia» = nadie del linaje la nombra en sus documentos.
VENTANAS = [("DESC", "2025-08 → 2026-03", ("20250805", "2025-08", "DESC")), ("REP", "2026-04 → 2026-09", ("20260401", "2026-04", "réplica", "REP")),
            ("SPOT 2023–2025", "Dukascopy 2023-01 → 2025-07 (CFD; futuros no hay)", ("2023", "20230103", "2024")),
            ("HOLDOUT", "desde la sesión CME del 2026-10-01 (una apertura por familia)", ())]


def palabras(q: str) -> list:
    return [w for w in re.findall(r"[a-záéíóúñ0-9]+", q.lower()) if len(w) >= 2 and w not in VACIAS]


def _puntaje(texto: str, ws) -> int:
    """Coincidencias por palabra entera; las palabras largas por raíz (6 letras: «expansiones» ~ «expansion», «EXPANSION_ZONAS»)."""
    toks = re.findall(r"[a-záéíóúñ0-9]+", texto.lower().replace("_", " ").replace("-", " "))
    return sum(1 for t in toks for w in ws if t == w or (len(w) >= 6 and len(t) >= 6 and t[:6] == w[:6]))


def _jsonl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(p).exists() else []


def linaje(familia: str) -> list:
    padres = {l["familia"]: l.get("padres") or [] for l in _jsonl(R / "LINAJES.jsonl")}; out, cola = [], [familia]
    while cola:
        f = cola.pop(0)
        if f in out: continue
        out.append(f); cola += padres.get(f, [])
    return out


def presupuesto(familia: str) -> list:
    from edgelab.research import holdout_ventanas as HV
    lin = linaje(familia); md = [f"### Presupuesto de datos de `{familia}` (linaje: {', '.join(lin)})", ""]
    carpetas = set()
    for l in _jsonl(R / "LINAJES.jsonl"):
        if l["familia"] in lin: carpetas |= set(re.findall(r"docs/research/([\w\-]+)/", l.get("justificacion", "")))
    texto = " ".join(p.read_text(encoding="utf-8", errors="ignore") for c in carpetas for p in (R / c).glob("*.md") if (R / c).is_dir())
    for nom, desc, marcas in VENTANAS:
        if nom == "HOLDOUT":
            u = [x for f in lin if (x := HV.ultima_consumida(f))]; ap = [a for f in lin for a in HV.aperturas_vigentes(f)]
            md.append(f"- **{nom}** {desc}: consumido hasta {max(u) if u else '—'}; aperturas del linaje: {len(ap)}"
                      + (f" ({', '.join(a['cid'] for a in ap)})" if ap else "") + "."); continue
        usada = [m for m in marcas if m in texto]
        md.append(f"- **{nom}** {desc}: " + (f"**mirada** por el linaje (aparece {usada[0]!r} en sus documentos)" if usada else "limpia para el linaje (verificar)"))
    return md + [""]


def ficha(q: str, familia: str | None = None) -> str:
    import familias as FA
    from existente import buscar
    ws = palabras(q); md = [f"# Antecedentes: «{q}»", ""]
    fam = sorted(((_puntaje(json.dumps(f, ensure_ascii=False), ws), f) for f in FA.tabla()), key=lambda x: -x[0])
    md += ["## Familias parecidas", "", "| familia | padres | pruebas | último desenlace | factores |", "|---|---|---|---|---|"]
    md += [f"| {f['familia']} | {', '.join(f['padres'])} | {f['pruebas']} | {(f['desenlaces'] or ['—'])[-1]} | {', '.join(f['factores'][:3])} |"
           for s, f in fam[:8] if s > 0]
    fac = sorted(((_puntaje(e["factor"] + " " + e.get("donde", "") + " " + e.get("efecto", ""), ws), e) for e in _jsonl(R / "FACTORES.jsonl")), key=lambda x: -x[0])
    md += ["", "## Factores relacionados (NO_REPETIR primero)", ""]
    md += [f"- **{e['estado']}** `{e['id']}`: {e['factor']} — {e.get('siguiente', '')[:160]}"
           for s, e in sorted([x for x in fac[:12] if x[0] > 0], key=lambda x: (x[1]["estado"] != "NO_REPETIR", -x[0]))]
    docs = []
    for p in R.glob("**/*.md"):
        try: cab = p.read_text(encoding="utf-8", errors="ignore")[:600]
        except OSError: continue
        s = _puntaje(p.name + " " + cab, ws)
        if s >= 2: docs.append((s, p))
    md += ["", "## Documentos", ""] + [f"- `{p.relative_to(ROOT)}`" for s, p in sorted(docs, key=lambda x: -x[0])[:10]]
    md += ["", "## Código reutilizable (tools/existente.py)", ""] + [f"- `{r['ref']}` — {r['doc'][:120]}" for r in buscar(q, k=8)]
    md += ["", "## Ventanas del holdout ya consumidas (todas las familias)", ""]
    md += [f"- {r['familia']}: {r['desde']} → {r['hasta']} (relacionadas: {', '.join(r.get('relacionadas', []))})" for r in _jsonl(R / "HOLDOUT_VENTANAS.jsonl")
           if r.get("tipo") == "consumida" and _puntaje(r["familia"] + " " + " ".join(r.get("relacionadas", [])), ws)]
    if familia: md += [""] + presupuesto(familia)
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    fam = sys.argv[sys.argv.index("--familia") + 1] if "--familia" in sys.argv else None
    print(ficha(a[0] if a and a[0] != fam else "", fam))
