#!/usr/bin/env python3
r"""Búsqueda de literatura para EdgeLab con APIs oficiales y gratuitas (no Google Scholar: sus términos prohíben el
scraping). Fuentes: OpenAlex (sin clave) y Semantic Scholar Graph API (sin clave; con S2_API_KEY si existe).

Por tema: consulta ambas fuentes, une por DOI / título normalizado, ordena por citas y recencia, descarta lo ya
registrado y escribe:
  docs/research/literatura/index.json           registro acumulado (id, título, año, citas, fuentes, temas, estado)
  docs/research/literatura/<tema>.md             fichas nuevas del tema (resumen, enlaces, campos a completar)
Los campos "por qué sirve / hipótesis testeable / datos en EdgeLab" quedan PENDIENTES: los completa quien lea el
paper. La herramienta no inventa relevancia.

    .venv\Scripts\python tools\literatura.py                 # todos los temas
    .venv\Scripts\python tools\literatura.py --tema gamma --n 15
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs/research/literatura"
MAILTO = "edgelab-research@users.noreply.github.com"      # pool "polite" de OpenAlex (sin datos personales)
TEMAS = {
    "gamma": ["dealer gamma exposure intraday", "option market maker hedging intraday momentum", "0DTE options gamma volatility"],
    "momentum_intradia": ["intraday momentum futures last half hour", "intraday return predictability index futures"],
    "regimenes": ["regime switching trading strategy allocation", "factor momentum timing", "strategy performance persistence"],
    "microestructura": ["order flow imbalance futures price impact", "limit order book liquidity futures intraday",
                        "volume profile support resistance price levels"],
    "validacion": ["backtest overfitting probability", "deflated sharpe ratio multiple testing", "combinatorial purged cross validation"],
    "calendario": ["macroeconomic announcement futures intraday", "fixing effect currency 4pm london", "overnight returns futures"],
}


def get(url, headers=None, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EdgeLab-literatura/1.0", **(headers or {})})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                                  # 429 / red: espera y reintenta (sin evadir límites)
            if k == tries - 1:
                print("  aviso:", url[:90], e)
                return None
            time.sleep(3 * 2 ** k)


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def openalex(q, n):
    u = ("https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"search": q, "per-page": n, "sort": "relevance_score:desc", "filter": "from_publication_date:2000-01-01",
         "mailto": MAILTO}))
    d = get(u) or {}
    out = []
    for w in d.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        pos = sorted((i, word) for word, ix in inv.items() for i in ix)
        out.append(dict(title=w.get("title"), year=w.get("publication_year"), cites=w.get("cited_by_count", 0),
                        doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
                        url=(w.get("primary_location") or {}).get("landing_page_url") or w.get("id"),
                        venue=((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                        oa_pdf=(w.get("best_oa_location") or {}).get("pdf_url"),
                        abstract=" ".join(x for _, x in pos)[:1500] or None, src="openalex"))
    return out


def s2(q, n):
    h = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    u = ("https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(
        {"query": q, "limit": n, "fields": "title,year,citationCount,abstract,tldr,externalIds,url,venue,openAccessPdf"}))
    d = get(u, h) or {}
    out = []
    for p in d.get("data", []) or []:
        out.append(dict(title=p.get("title"), year=p.get("year"), cites=p.get("citationCount") or 0,
                        doi=(p.get("externalIds") or {}).get("DOI"), url=p.get("url"), venue=p.get("venue"),
                        oa_pdf=(p.get("openAccessPdf") or {}).get("url"), abstract=(p.get("abstract") or "")[:1500] or None,
                        tldr=(p.get("tldr") or {}).get("text"), src="semanticscholar"))
    time.sleep(1.2)                                             # sin clave: ~1 req/s
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tema", choices=sorted(TEMAS)); ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = OUT / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}
    for tema in ([a.tema] if a.tema else sorted(TEMAS)):
        found = {}
        for q in TEMAS[tema]:
            for r in openalex(q, a.n) + s2(q, a.n):
                if not r.get("title"):
                    continue
                key = (r["doi"] or "").lower() or norm(r["title"])
                cur = found.get(key)
                if cur is None:
                    found[key] = dict(r, queries=[q], fuentes=[r["src"]])
                else:                                           # unir: conservar lo mejor de cada fuente
                    cur["cites"] = max(cur["cites"], r["cites"]); cur["queries"] = sorted(set(cur["queries"] + [q]))
                    cur["fuentes"] = sorted(set(cur["fuentes"] + [r["src"]]))
                    for f in ("abstract", "tldr", "oa_pdf", "venue", "doi"):
                        cur[f] = cur.get(f) or r.get(f)
        nuevos = [(k, v) for k, v in found.items() if k not in idx]
        nuevos.sort(key=lambda kv: (-(kv[1]["cites"] or 0), -(kv[1]["year"] or 0)))
        L = [f"# Literatura — {tema} (generado {date.today()})", "",
             "Fuentes: OpenAlex + Semantic Scholar. Orden: citas. Campos *pendiente* = completar al leer.", ""]
        for k, v in nuevos:
            idx[k] = dict(title=v["title"], year=v["year"], cites=v["cites"], doi=v.get("doi"), url=v.get("url"),
                          temas=[tema], fuentes=v["fuentes"], estado="sin_leer", agregado=str(date.today()))
            L += [f"## {v['title']} ({v['year']}) — {v['cites']} citas", "",
                  f"- Fuente: {v.get('venue') or 'n/d'} · {v.get('url') or ''}" + (f" · DOI {v['doi']}" if v.get("doi") else ""),
                  f"- PDF abierto: {v['oa_pdf']}" if v.get("oa_pdf") else "- PDF abierto: no",
                  f"- TL;DR: {v['tldr']}" if v.get("tldr") else "",
                  f"- Resumen: {v['abstract']}" if v.get("abstract") else "- Resumen: no disponible",
                  "- Por qué sirve a EdgeLab: *pendiente*", "- Hipótesis testeable: *pendiente*",
                  "- ¿Hay datos en EdgeLab para testearla?: *pendiente*", ""]
        if nuevos:
            (OUT / f"{tema}.md").write_text("\n".join(x for x in L if x is not None), encoding="utf-8")
        print(tema, "encontrados", len(found), "nuevos", len(nuevos), flush=True)
    idx_p.write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
