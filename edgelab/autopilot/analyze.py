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
    if "results_flat" in result:                       # tools/study_slot_effect.py
        for r in result["results_flat"]:
            ph = next((v for k, v in r.items() if k.startswith("p_holm_")), None)
            out.append(dict(test=r.get("test", "?"), p=r.get("p"), p_holm=ph, evaluable=bool(r.get("evaluable")), effect=r.get("corr", r.get("diff"))))
    if "rth" in result and result["rth"] and "kind" in result["rth"][0]:
        for r in result["rth"]:
            out.append(dict(test=f"{r['kind']}/H{r['H']}/{r['channel']}", p=r["p"], p_holm=r.get("p_holm"), evaluable=True, effect=r["D"]))
    return out


def decide(result: dict, family_alpha: float, n_planned: int) -> dict:
    """Aplica Holm propio al nivel familiar que apostó el alpha-investing (`family_alpha`), sobre `n_planned` pruebas. Devuelve hit y rechazos; las no evaluables cuentan en n_planned."""
    rec = [r for r in records(result) if r["evaluable"] and r["p"] is not None]
    rej = holm_rejections([r["p"] for r in rec], family_alpha, n_planned)
    return dict(hit=rej > 0, rejections=rej, n_evaluable=len(rec), n_planned=n_planned, family_alpha=family_alpha,
                top=sorted(rec, key=lambda r: r["p"])[:5], tier_hint="C (información) hasta que exista P&L neto, estabilidad y diversificación (mandato)", note="hallazgo estadístico exploratorio: NO es un edge útil por serlo (ver MANDATO.md); requiere réplica pre-registrada y evaluación de utilidad")


def rejected_tests(result: dict, family_alpha: float, n_planned: int) -> set:
    """Nombres de las pruebas rechazadas por Holm al nivel familiar (mismo procedimiento que `decide`)."""
    rec = sorted([r for r in records(result) if r["evaluable"] and r["p"] is not None], key=lambda r: r["p"]); m = max(n_planned, len(rec)); out = set()
    for k, r in enumerate(rec):
        if r["p"] <= family_alpha / (m - k): out.add(r["test"])
        else: break
    return out
