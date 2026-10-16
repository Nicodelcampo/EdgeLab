"""Promoción automática de candidatas, sin humano en el camino (decisión de Nico, 2026-10-16).

Vale bajo la enmienda AUTONOMIA-A1 (docs/incidents/AMENDMENT_AUTONOMIA-A1_2026-10-16_PROPUESTA.md). Hasta que
Nico la firme, `config["auto_promocion"]` debe quedar en False. Lo que cambia es quién aprueba, no cuánto se exige.

Orden fijo, y cualquier paso que falle corta:
  1. mecánico, sin LLM: hay estudio listo (template); límite de pruebas; novedad contra retiradas; mismo RunSpec no
     repetido; tope de promociones por ciclo;
  2. revisor (Opus, sesión aparte, métricas públicas): debe decir PROMOTE, si no se rechaza;
  3. pre-registro escrito y committeado por el agente ANTES de lanzar, en el clon de código;
  4. las guardas de siempre (guard.all_checks) sobre el RunSpec, incluida la configuración textual en el pre-registro;
  5. se agrega a candidates.json; el ciclo normal cuenta, apuesta alfa y lanza.
Cada decisión queda en promociones.jsonl (promovida o rechazada, con motivo).
"""
from __future__ import annotations
import hashlib, json, subprocess, time
from pathlib import Path

from . import guard
from .contexto import novedad
from .spec import RunSpec

MAX_TRIALS_AUTO = 500          # una candidata que agrega más pruebas que esto no se auto-promueve


def _git(repo, *a):
    r = subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a[:2])} falló: {(r.stdout + r.stderr)[-200:]}")
    return r.stdout.strip()


def _log(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def chequeos_mecanicos(c, rs: dict | None, retiradas: list, ya: set) -> list:
    e = []
    if rs is None: e.append("sin estudio listo (NEEDS_SCRIPT): se registra como pedido de módulo, no se lanza")
    if c.n_trials > MAX_TRIALS_AUTO: e.append(f"agrega {c.n_trials} pruebas (> {MAX_TRIALS_AUTO}): sólo con revisión humana")
    nueva, parecida, sim = novedad({"familia": c.title, "mecanismo": ""}, retiradas)        # por título: el "por qué" diluye la similitud
    if not nueva: e.append(f"repite una familia retirada ({parecida}, similitud {sim})")
    if rs is not None and RunSpec.from_dict(rs).spec_hash() in ya: e.append("el mismo RunSpec ya se lanzó o se promovió")
    return e


def promover_auto(candidatas, *, draft_fn, to_runspec, runner, repo: Path, candidates_path: Path, log_path: Path,
                  retiradas=(), ya_hashes=frozenset(), max_por_ciclo: int = 1, allow_internet=frozenset(), protected=None) -> list:
    repo, candidates_path = Path(repo), Path(candidates_path)
    cur = json.loads(candidates_path.read_text()) if candidates_path.exists() else []
    have = {c["run_id"] for c in cur} | set()
    hashes = set(ya_hashes) | {RunSpec.from_dict(c).spec_hash() for c in cur}
    out, promovidas = [], 0
    for c in candidatas:
        if promovidas >= max_por_ciclo: break
        rs = to_runspec(c)
        row = dict(ts=time.time(), cid=c.cid, score=round(float(c.score), 6))
        errs = chequeos_mecanicos(c, rs, list(retiradas), hashes)
        if not errs and rs["run_id"] in have: errs = ["ya está en candidates.json"]
        if errs:
            _log(log_path, dict(row, decision="RECHAZADA_MECANICO", motivos=errs)); out.append((c.cid, "RECHAZADA_MECANICO")); continue
        texto = draft_fn(c)
        rev = runner.call("revisor", {"borrador": texto[:9000], "publicas": dict(score=c.score, pruebas=c.n_trials, a_favor=c.pro, en_contra=c.contra, regla=c.rule)})
        if rev.get("status") not in ("OK", "CACHED") or rev["output"]["decision"] != "PROMOTE":
            _log(log_path, dict(row, decision="RECHAZADA_REVISOR", revisor=rev.get("output") or rev.get("status"))); out.append((c.cid, "RECHAZADA_REVISOR")); continue
        p = repo / rs["prereg"]                                            # 3) pre-registro committeado ANTES de lanzar
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(texto, encoding="utf-8")
        _git(repo, "add", "--", rs["prereg"])
        if _git(repo, "status", "--porcelain", "--", rs["prereg"]):
            _git(repo, "-c", "user.name=edgelab-agente", "-c", "user.email=agente@edgelab.local", "commit", "-q", "-m",
                 f"prereg(autopilot): {c.cid} promovido automáticamente (revisor: PROMOTE)", "--", rs["prereg"])
        sha = _git(repo, "log", "-1", "--format=%H", "--", rs["prereg"])
        g = guard.all_checks(RunSpec.from_dict(rs), set(allow_internet), repo, Path(protected) if protected else None)   # 4) guardas de siempre
        if g:
            _log(log_path, dict(row, decision="RECHAZADA_GUARDAS", motivos=g, prereg_commit=sha)); out.append((c.cid, "RECHAZADA_GUARDAS")); continue
        cur.append(rs); have.add(rs["run_id"]); hashes.add(RunSpec.from_dict(rs).spec_hash())
        candidates_path.write_text(json.dumps(cur, indent=1))
        _log(log_path, dict(row, decision="PROMOVIDA", run_id=rs["run_id"], prereg=rs["prereg"], prereg_commit=sha,
                            prereg_sha256=hashlib.sha256(texto.encode()).hexdigest(), revisor=rev["output"]))
        out.append((c.cid, "PROMOVIDA")); promovidas += 1
    return out
