"""Crawler de reglas por firma: recorre los sitemaps (centro de ayuda, sitio, términos), baja cada página una vez,
clasifica cada oración con la taxonomía y arma un **inventario de reglas** por firma con su fuente y la cobertura por
categoría. Las páginas que el sitio bloquea (403) quedan listadas para bajarlas con un navegador o con Firecrawl y
agregarlas con `--extra-dir` (archivos .md/.txt con la URL en la primera línea).

    python -m edgelab.propfirm.crawl --config config/propfirms/crawl.json --out artifacts/propfirm/crawl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

from .scraper import UA, fetch, html_to_text
from .taxonomy import CATEGORIES, classify, coverage


def sitemap_urls(url: str) -> list[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            xml = r.read().decode("utf-8", "replace")
    except Exception:
        return []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    out = []
    for loc in locs:
        if loc.endswith(".xml"):
            out += sitemap_urls(loc)
        else:
            out.append(loc)
    return out


def zendesk_articles(base: str, locale: str = "en-us") -> list[dict]:
    """Centros de ayuda Zendesk: la API pública devuelve el cuerpo de cada artículo aunque la web bloquee (403)."""
    out, url = [], f"{base.rstrip('/')}/api/v2/help_center/{locale}/articles.json?per_page=100"
    while url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            break
        out += [dict(url=a["html_url"], html=a.get("body") or "", title=a.get("title", ""), updated=a.get("updated_at"))
                for a in d.get("articles", [])]
        url = d.get("next_page")
    return out


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower().split("://", 1)[-1])[:150].strip("_")


def crawl_firm(firm: dict, out: Path, pause_s: float = 0.6, max_pages: int = 400) -> dict:
    """firm = {firm, sitemaps: [...], include: regex, exclude: regex, urls: [...], extra_dir: opcional}"""
    fdir = out / firm["firm"]; (fdir / "pages").mkdir(parents=True, exist_ok=True)
    urls = list(firm.get("urls", []))
    for sm in firm.get("sitemaps", []):
        urls += sitemap_urls(sm)
    inc = re.compile(firm.get("include", "."), re.I); exc = re.compile(firm["exclude"], re.I) if firm.get("exclude") else None
    seen, todo = set(), []
    for u in urls:
        u = u.split("#")[0]
        if u in seen or not inc.search(u) or (exc and exc.search(u)):
            continue
        seen.add(u); todo.append(u)
    todo = todo[:max_pages]
    pages, blocked = [], []
    for u in todo:
        cache = fdir / "pages" / (_slug(u) + ".txt")
        if cache.exists():
            text = cache.read_text(encoding="utf-8"); status = 200; sha = hashlib.sha256(text.encode()).hexdigest()
        else:
            r = fetch(u)
            if not r["html"]:
                blocked.append(dict(url=u, status=r["status"], error=r.get("error"))); time.sleep(pause_s); continue
            text = html_to_text(r["html"]); status = r["status"]; sha = hashlib.sha256(r["html"].encode()).hexdigest()
            cache.write_text(text, encoding="utf-8"); time.sleep(pause_s)
        pages.append(dict(url=u, status=status, sha256=sha, text=text))
    # centros de ayuda Zendesk (API pública)
    for zd in firm.get("zendesk", []):
        for a in zendesk_articles(zd):
            if not inc.search(a["url"]) or (exc and exc.search(a["url"])):
                continue
            text = a["title"] + ". " + html_to_text(a["html"])
            pages.append(dict(url=a["url"], status="zendesk", sha256=hashlib.sha256(a["html"].encode()).hexdigest(),
                              text=text, updated=a["updated"]))
    # páginas bajadas a mano o con Firecrawl: primera línea = URL
    xd = firm.get("extra_dir")
    if xd and Path(xd).exists():
        for f in sorted(Path(xd).glob("*")):
            if f.suffix.lower() in (".md", ".txt"):
                raw = f.read_text(encoding="utf-8"); first, _, rest = raw.partition("\n")
                pages.append(dict(url=first.strip(), status="manual", sha256=hashlib.sha256(raw.encode()).hexdigest(),
                                  text=re.sub(r"\s+", " ", rest)))
    # inventario: oraciones únicas con todas sus fuentes
    inv: dict[str, dict] = {}
    for p in pages:
        for it in classify(p["text"]):
            key = it["texto"].lower()
            if key not in inv:
                inv[key] = dict(texto=it["texto"], categorias=it["categorias"], numeros=it["numeros"], fuentes=[])
            if p["url"] not in inv[key]["fuentes"]:
                inv[key]["fuentes"].append(p["url"])
    items = list(inv.values())
    cov = coverage(items)
    res = dict(firm=firm["firm"], paginas=len(pages), bloqueadas=blocked, urls_candidatas=len(todo),
               cobertura=cov, sin_evidencia=[k for k, v in cov.items() if v == 0], items=items,
               paginas_meta=[{k: p[k] for k in ("url", "status", "sha256")} for p in pages])
    (fdir / "inventario.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (fdir / "inventario.md").write_text(render_md(res), encoding="utf-8")
    return res


def render_md(res: dict) -> str:
    L = [f"# Inventario de reglas — {res['firm']}", "",
         f"Páginas leídas: {res['paginas']} · bloqueadas: {len(res['bloqueadas'])} · oraciones con reglas: {len(res['items'])}", "",
         "## Cobertura por categoría", "", "| Categoría | Impacto | Oraciones |", "|---|---|---|"]
    for k, v in res["cobertura"].items():
        L.append(f"| {k} | {CATEGORIES[k]['impacto']} | {v if v else '**0 — sin evidencia, buscar a mano**'} |")
    for k in CATEGORIES:
        its = [i for i in res["items"] if k in i["categorias"]]
        if not its:
            continue
        L += ["", f"## {k} ({CATEGORIES[k]['impacto']})", ""]
        for i in its[:60]:
            src = i["fuentes"][0]
            L.append(f"- {i['texto']}  ")
            L.append(f"  <sub>{', '.join(i['numeros'][:6])} · [{src.split('/')[-1][:60] or src}]({src})"
                     f"{' +' + str(len(i['fuentes']) - 1) if len(i['fuentes']) > 1 else ''}</sub>")
        if len(its) > 60:
            L.append(f"- … {len(its) - 60} más en inventario.json")
    if res["bloqueadas"]:
        L += ["", "## Páginas bloqueadas (bajar con navegador o Firecrawl)", ""] + [f"- {b['url']} ({b['status']})" for b in res["bloqueadas"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/propfirms/crawl.json")
    ap.add_argument("--out", default="artifacts/propfirm/crawl")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--max-pages", type=int, default=400)
    a = ap.parse_args(argv)
    firms = json.loads(Path(a.config).read_text(encoding="utf-8"))
    out = Path(a.out)
    for f in firms:
        if a.only and f["firm"] not in a.only:
            continue
        r = crawl_firm(f, out, max_pages=a.max_pages)
        print(f"{r['firm']:<18} páginas {r['paginas']:>4} (de {r['urls_candidatas']}) bloqueadas {len(r['bloqueadas']):>3} "
              f"oraciones {len(r['items']):>5}  sin evidencia: {', '.join(r['sin_evidencia']) or '-'}", flush=True)


if __name__ == "__main__":
    main()
