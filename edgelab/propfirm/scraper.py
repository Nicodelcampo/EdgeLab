"""Scraper de reglas de prop firms: baja páginas públicas, guarda una instantánea con sha256 y extrae **candidatos**
(montos y porcentajes cerca de palabras clave), cada uno con su fragmento de contexto.

No convierte candidatos en reglas: las páginas mezclan planes, promociones y reglas viejas, y un número sacado de
contexto produce una esperanza falsa. El flujo es: `fetch` → `extract` → revisión humana → `Rules(verified=True)`
en `config/propfirms/`. Algunas firmas bloquean descargas automáticas (403): quedan marcadas `BLOQUEADO` para bajar a
mano o con un navegador.

    python -m edgelab.propfirm.scraper --sources config/propfirms/sources.json --out artifacts/propfirm/scrape
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "Mozilla/5.0 (compatible; EdgeLab-research/1.0; one-shot rule snapshot)"

# palabra clave → campo de Rules al que apunta el candidato
KEYWORDS = {
    "profit_target": r"profit\s*target|objetivo\s*de\s*(?:beneficio|ganancia)",
    "max_loss": r"(?:max(?:imum)?\s*(?:loss|drawdown)|trailing\s*(?:max(?:imum)?\s*)?drawdown|end[- ]of[- ]day\s*drawdown|eod\s*drawdown)",
    "daily_loss_limit": r"daily\s*loss\s*limit|daily\s*drawdown|max(?:imum)?\s*daily\s*loss",
    "consistency_cap": r"consistency",
    "payout_split": r"profit\s*split|payout\s*split|keep\s*\d+\s*%",
    "eval_fee": r"(?:per\s*month|/\s*mo(?:nth)?|monthly|one[- ]time\s*fee|evaluation\s*fee|challenge\s*fee)",
    "activation_fee": r"activation\s*fee|reset\s*fee",
    "min_trading_days": r"min(?:imum)?\s*(?:trading\s*)?days",
    "payout_cap": r"payout\s*(?:cap|limit)|max(?:imum)?\s*payout",
    "account_size": r"\b(?:25|50|75|100|150|200|250|300)\s*k\b",
}
NUM = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?\s?%|\b\d{1,3}(?:,\d{3})+\b|\b\d+\s?(?:days?|trading days)\b", re.I)


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def fetch(url: str, timeout: int = 25) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    t = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return dict(url=url, status=r.status, fetched_at=t, html=body)
    except urllib.error.HTTPError as e:
        return dict(url=url, status=e.code, fetched_at=t, html="", error="BLOQUEADO" if e.code in (401, 403, 429) else str(e))
    except Exception as e:  # red, TLS, timeout
        return dict(url=url, status=0, fetched_at=t, html="", error=type(e).__name__)


def extract(text: str, window: int = 160) -> list[dict]:
    """Candidatos: cada número a menos de `window` caracteres de una palabra clave, con su contexto."""
    out = []
    for field, pat in KEYWORDS.items():
        for m in re.finditer(pat, text, re.I):
            a, b = max(0, m.start() - window), min(len(text), m.end() + window)
            ctx = text[a:b]
            nums = [n.group(0).strip() for n in NUM.finditer(ctx)]
            if nums:
                out.append(dict(campo=field, clave=m.group(0), numeros=nums[:8], contexto=ctx))
    # dedupe por (campo, contexto)
    seen, uniq = set(), []
    for c in out:
        k = (c["campo"], c["contexto"][:80])
        if k not in seen:
            seen.add(k); uniq.append(c)
    return uniq


def run(sources: list[dict], out_dir: Path, pause_s: float = 2.0) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for s in sources:
        r = fetch(s["url"])
        text = html_to_text(r["html"]) if r["html"] else ""
        sha = hashlib.sha256(r["html"].encode()).hexdigest() if r["html"] else ""
        cands = extract(text) if text else []
        slug = re.sub(r"[^a-z0-9]+", "_", (s["firm"] + "_" + s.get("page", "")).lower()).strip("_")
        if text:
            (out_dir / f"{slug}.txt").write_text(text, encoding="utf-8")
        rec = dict(firm=s["firm"], page=s.get("page", ""), url=s["url"], status=r["status"], error=r.get("error"),
                   fetched_at=r["fetched_at"], sha256=sha, n_chars=len(text), candidatos=cands)
        (out_dir / f"{slug}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        summary.append({k: rec[k] for k in ("firm", "page", "url", "status", "error", "sha256", "n_chars")} |
                       {"candidatos": len(cands)})
        time.sleep(pause_s)
    (out_dir / "_resumen.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="config/propfirms/sources.json")
    ap.add_argument("--out", default="artifacts/propfirm/scrape")
    a = ap.parse_args(argv)
    sources = json.loads(Path(a.sources).read_text(encoding="utf-8"))
    for row in run(sources, Path(a.out)):
        print(f"{row['firm']:<18} {row['page']:<22} {row['status']:>4} {str(row['error'] or ''):<11} "
              f"{row['n_chars']:>7} chars  {row['candidatos']:>3} candidatos")


if __name__ == "__main__":
    main()
