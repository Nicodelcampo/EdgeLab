"""Auditoría post-corrida (pedido de Nico, 2026-10-19). Corre FUERA del ciclo de lanzamiento, sobre corridas ANALYZED.

Por cada corrida no auditada:
  1. chequeos mecánicos, sin LLM (deciden solos si fallan):
     - el pre-registro y el script tienen commit ANTERIOR al lanzamiento y no cambiaron después;
     - la configuración lanzada está en el pre-registro (guard.check_env_in_prereg);
     - holdout: ningún `needs` llega a la fecha de corte;
     - pruebas evaluables <= pruebas planeadas; p inválidos declarados;
  2. auditor (LLM): compara pre-registro, especificación y decisión → CONFORME / DESVIO / SOSPECHA_FUGA;
  3. si la corrida es hallazgo (hit): abogado del diablo (LLM) → explicación no-edge y prueba refutadora.
Resultado en `auditorias.jsonl` (append-only, se sube a autopilot/state) con el estado final:
  CONFORME | EN_DUDA (desvío o abogado de gravedad alta) | BLOQUEADA (falla mecánica o sospecha de fuga).
Un hallazgo EN_DUDA o BLOQUEADO no recarga la confianza del selector: queda anotado para revisión humana.
Nada de acá modifica el libro de corridas ni el alfa: la auditoría informa, no reescribe la historia.
"""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path

from . import guard
from .spec import RunSpec


def _commit_ts(repo: Path, rel: str, primero: bool = False):
    a = ["git", "log", "--format=%ct", "--", rel]
    r = subprocess.run(a, cwd=repo, capture_output=True, text=True).stdout.split()
    if not r: return None
    return int(r[-1] if primero else r[0])


def chequeos(spec: RunSpec, decision: dict, launched_at: float | None, repo: Path) -> list:
    e = []
    for rel, que in ((spec.prereg, "pre-registro"), (spec.script, "script")):
        primero, ultimo = _commit_ts(repo, rel, True), _commit_ts(repo, rel)
        if primero is None: e.append(f"{que} sin commit: {rel}"); continue
        if launched_at and primero > launched_at: e.append(f"{que} committeado DESPUÉS del lanzamiento: {rel}")
        if launched_at and ultimo and ultimo > launched_at and que == "pre-registro": e.append(f"pre-registro modificado después del lanzamiento: {rel}")
    e += guard.check_holdout(spec)                                       # para kind=holdout sólo exige que no mezcle desarrollo
    e += [f"configuración: {x}" for x in guard.check_env_in_prereg(spec, repo)]
    n_ev, n_pl = decision.get("n_evaluable"), decision.get("n_planned")
    if isinstance(n_ev, int) and isinstance(n_pl, int) and n_ev > n_pl: e.append(f"pruebas evaluables ({n_ev}) > planeadas ({n_pl}): hubo pruebas no pre-registradas")
    if decision.get("invalid_p_tests"): e.append(f"p inválidos: {decision['invalid_p_tests'][:5]}")
    return e


def pendientes(ledger, hechas: set) -> list:
    rows = ledger.db.execute("SELECT run_id, spec, result, launched_at FROM runs WHERE status='ANALYZED' ORDER BY finished_at").fetchall()
    return [(rid, RunSpec.from_dict(json.loads(sp)), json.loads(res), la) for rid, sp, res, la in rows if rid not in hechas]


def auditar(ledger, repo: Path, log_path: Path, runner=None, antecedentes_fn=None, max_por_ciclo: int = 5, ahora=None) -> list:
    repo, log_path = Path(repo), Path(log_path)
    hechas = {json.loads(l)["run_id"] for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()} if log_path.exists() else set()
    out = []
    for rid, spec, dec, la in pendientes(ledger, hechas)[:max_por_ciclo]:
        mec = chequeos(spec, dec, la, repo)
        row = dict(ts=ahora or time.time(), run_id=rid, family=spec.family, prereg=spec.prereg, hit=bool(dec.get("hit")), mecanicos=mec)
        try: texto = (repo / spec.prereg).read_text(encoding="utf-8")[:9000]
        except OSError: texto = ""
        publico = dict(top=[{k: t.get(k) for k in ("test", "p", "effect")} for t in dec.get("top", [])][:5], hit=dec.get("hit"),
                       rejections=dec.get("rejections"), n_planned=dec.get("n_planned"), n_evaluable=dec.get("n_evaluable"), family_alpha=dec.get("family_alpha"))
        especificacion = dict(family=spec.family, group=spec.group, script=spec.script, needs=list(spec.needs), n_trials=spec.n_trials, env=dict(spec.env))
        ant = list(antecedentes_fn(spec)) if antecedentes_fn else []
        if runner is not None and not mec:
            a = runner.call("auditor", dict(preregistro=texto, especificacion=especificacion, decision=publico, chequeos_mecanicos=mec))
            row["auditor"] = a.get("output") or a.get("status")
            if row["hit"]:
                d = runner.call("abogado", dict(preregistro=texto, decision=publico, antecedentes=ant))
                row["abogado"] = d.get("output") or d.get("status")
        aud, abo = row.get("auditor"), row.get("abogado")
        if mec or (isinstance(aud, dict) and aud.get("veredicto") == "SOSPECHA_FUGA"): estado = "BLOQUEADA"
        elif (isinstance(aud, dict) and aud.get("veredicto") == "DESVIO") or (isinstance(abo, dict) and abo.get("gravedad") == "alta"): estado = "EN_DUDA"
        elif runner is None or isinstance(aud, dict): estado = "CONFORME" if runner is not None else "MECANICO_OK_SIN_LLM"
        else: estado = "PENDIENTE_LLM"                                                   # rol sin cupo o salida inválida: se reintenta
        row["estado"] = estado
        if estado != "PENDIENTE_LLM":
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        out.append((rid, estado))
    return out


def estados(log_path: Path) -> dict:
    """run_id -> último estado de auditoría (para el selector, el tablero y el cronista)."""
    p = Path(log_path)
    if not p.exists(): return {}
    d = {}
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.strip(): r = json.loads(l); d[r["run_id"]] = r["estado"]
    return d
