"""Apertura del holdout aprobada por el agente (decisión de Nico, 2026-10-20: «que el agente también apruebe abrir el holdout»).

Cambia QUIÉN aprueba, no el protocolo. Una corrida `kind="holdout"` sólo se lanza si se cumplen TODAS:
  1. confirma a un candidato: `origin["candidato"]` es una corrida ANALYZED con hallazgo (hit);
  2. ese candidato pasó la auditoría post-corrida (`auditorias.jsonl`: CONFORME);
  3. una sola apertura por familia: la familia no tiene una apertura previa registrada (ni lanzada ni fallida);
  4. regla congelada: la configuración (`env`) es idéntica a la del candidato; lo único que cambia es el período;
  5. sólo holdout: todos los `needs` empiezan en la fecha de corte o después (no se mezcla con desarrollo);
  6. pasó por la promoción de siempre (pre-registro publicado, doble revisión, guardas) — eso lo hace el ciclo antes.
MODO EXPLORATORIO (decisión de Nico, 2026-11-08: «que sí lo pueda abrir», tras abrir el holdout de CANASTA-ORB sin candidato
confirmado): con `permitir_exploratoria` (clave `holdout_exploratorio` de la configuración), una apertura con
`origin["modo"] == "exploratoria"` no exige 1–2 (hallazgo ni auditoría CONFORME) pero sí: la probabilidad de azar de desarrollo
declarada (`origin["p_desarrollo"]`), la combinación pre-registrada (`origin["combinacion"]`, p. ej. "fisher") y el pre-registro.
Siguen 3 (una por familia), 4 (regla congelada contra `origin["referencia"]` si se nombra) y 5 (sólo holdout). Sirve para estimar
cuánto baja la probabilidad de azar; nunca para elegir ni ajustar.
La apertura se REGISTRA (append-only, `holdout_aperturas.jsonl`, se sube a autopilot/state) ANTES de lanzar, con
el pre-registro y su commit. Un resultado del holdout confirma o refuta: nunca se usa para elegir, ajustar o reintentar.
"""
from __future__ import annotations
import json, time
from pathlib import Path

from . import HOLDOUT_FIRST_TRADE_DATE
from .spec import RunSpec

ARCHIVO = "holdout_aperturas.jsonl"


def aperturas(root: Path) -> list:
    p = Path(root) / ARCHIVO
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _requisitos_exploratoria(spec: RunSpec, ledger, root: Path) -> list:
    o = spec.origin or {}; e = []
    p = o.get("p_desarrollo")
    if not isinstance(p, (int, float)) or not 0 < p <= 1: e.append("apertura exploratoria sin p_desarrollo (probabilidad de azar de desarrollo) en origin")
    if o.get("combinacion") not in ("fisher", "stouffer"): e.append("apertura exploratoria sin combinación pre-registrada (fisher o stouffer) en origin")
    if not spec.prereg: e.append("apertura exploratoria sin pre-registro")
    if any(a.get("family") == spec.family for a in aperturas(root)): e.append(f"la familia {spec.family} ya usó su única apertura del holdout")
    if (ref := o.get("referencia")):
        row = ledger.db.execute("SELECT spec FROM runs WHERE run_id=?", (ref,)).fetchone()
        if not row: e.append(f"la referencia {ref} no existe")
        elif dict(json.loads(row[0]).get("env") or {}) != dict(spec.env or {}): e.append("la configuración difiere de la referencia: la regla debe ir congelada")
    for n in spec.needs:
        q = n.split(":")
        if len(q) != 3 or q[1] < HOLDOUT_FIRST_TRADE_DATE: e.append(f"need {n} no es sólo holdout (debe empezar en {HOLDOUT_FIRST_TRADE_DATE} o después)")
    return e


def requisitos(spec: RunSpec, ledger, root: Path, exigir_escalera: bool = False, permitir_exploratoria: bool = False) -> list:
    """exigir_escalera (regla escalera_v1): además, el resultado del candidato debe traer el veredicto de la escalera del embudo
    (`escalera`, de edgelab/funnel/escalera.evaluar) en LISTA_PARA_HOLDOUT: réplica confirmada + económico con costos canónicos +
    potencia suficiente para el efecto recortado con el n que dará el holdout. Fail-closed: sin veredicto, no se abre."""
    if (spec.origin or {}).get("modo") == "exploratoria":
        if not permitir_exploratoria: return ["apertura exploratoria no habilitada (clave holdout_exploratorio de la configuración)"]
        return _requisitos_exploratoria(spec, ledger, root)
    e = []
    cand = (spec.origin or {}).get("candidato")
    if not cand: return ["apertura sin candidato: origin.candidato debe nombrar la corrida que se confirma"]
    row = ledger.db.execute("SELECT status, result, spec FROM runs WHERE run_id=?", (cand,)).fetchone()
    if not row or row[0] != "ANALYZED": return [f"el candidato {cand} no es una corrida ANALYZED"]
    if not json.loads(row[1] or "{}").get("hit"): e.append(f"el candidato {cand} no es un hallazgo (hit=false)")
    if exigir_escalera:
        v = (json.loads(row[1] or "{}").get("escalera") or {}).get("estado")
        if v != "LISTA_PARA_HOLDOUT":
            e.append(f"el candidato {cand} no trae veredicto de la escalera en LISTA_PARA_HOLDOUT (tiene {v!r}): falta económico o potencia; no se gasta la única apertura")
    from .auditoria import estados
    if estados(Path(root) / "auditorias.jsonl").get(cand) != "CONFORME": e.append(f"el candidato {cand} no tiene auditoría CONFORME")
    if any(a.get("family") == spec.family for a in aperturas(root)): e.append(f"la familia {spec.family} ya usó su única apertura del holdout")
    if dict(json.loads(row[2]).get("env") or {}) != dict(spec.env or {}): e.append("la configuración difiere de la del candidato: la regla debe ir congelada")
    for n in spec.needs:
        p = n.split(":")
        if len(p) != 3 or p[1] < HOLDOUT_FIRST_TRADE_DATE: e.append(f"need {n} no es sólo holdout (debe empezar en {HOLDOUT_FIRST_TRADE_DATE} o después)")
    return e


def registrar(spec: RunSpec, root: Path, prereg_commit: str | None = None, ahora=None) -> dict:
    row = dict(ts=ahora or time.time(), run_id=spec.run_id, family=spec.family, candidato=(spec.origin or {}).get("candidato"),
               needs=list(spec.needs), prereg=spec.prereg, prereg_commit=prereg_commit, aprobado_por="agente autonomo (decision 2026-10-20)",
               modo=(spec.origin or {}).get("modo", "confirmatoria"), p_desarrollo=(spec.origin or {}).get("p_desarrollo"))
    p = Path(root) / ARCHIVO; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
