"""Normaliza resultados de campañas conocidas a registros comparables y aplica la regla de decisión pre-registrada. «hit» = al menos una prueba evaluable con Holm ≤ nivel familiar.
Un resultado solo es *hallazgo* para el selector; no es edge: la promoción requiere réplica y pre-registro propios (fuera del autopilot)."""
from __future__ import annotations

from .fdr import holm_rejections


def records(result: dict) -> list:
    """Soporta: GEX (results[].tests{}), OU-1 (part_a/part_b), AVCL (rth[]), descubrimiento por familias (combos[].p_max)."""
    out = []
    if "results" in result and result["results"] and "tests" in result["results"][0]:
        for r in result["results"]:
            for k, t in r["tests"].items():
                out.append(dict(test=f"{r['source']}/{k}", p=t.get("p"), p_holm=t.get("p_holm"), evaluable=t.get("evaluable", t.get("p") is not None), effect=t.get("obs")))
    if "part_a" in result:
        for r in result["part_a"] + result.get("part_b", []):
            ph = next((v for k, v in r.items() if k.startswith("p_holm_")), None)
            out.append(dict(test=f"{r.get('asset', r.get('source'))}/{r.get('bar_min', r.get('slot'))}/{r.get('win_min', '')}", p=r.get("p", r.get("p_one_sided_neg")),
                            p_holm=ph, evaluable=r.get("evaluable", False), effect=r.get("z", r.get("corr"))))
    if "rth" in result and result["rth"] and "kind" in result["rth"][0]:
        for r in result["rth"]:
            out.append(dict(test=f"{r['kind']}/H{r['H']}/{r['channel']}", p=r["p"], p_holm=r.get("p_holm"), evaluable=True, effect=r["D"]))
    return out


def decide(result: dict, family_alpha: float, n_planned: int) -> dict:
    """Aplica Holm propio al nivel familiar que apostó el alpha-investing (`family_alpha`), sobre `n_planned` pruebas. Devuelve hit y rechazos; las no evaluables cuentan en n_planned."""
    rec = [r for r in records(result) if r["evaluable"] and r["p"] is not None]
    rej = holm_rejections([r["p"] for r in rec], family_alpha, n_planned)
    return dict(hit=rej > 0, rejections=rej, n_evaluable=len(rec), n_planned=n_planned, family_alpha=family_alpha,
                top=sorted(rec, key=lambda r: r["p"])[:5], note="hallazgo exploratorio: requiere réplica pre-registrada; no es edge")
