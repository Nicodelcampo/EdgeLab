"""Promoción automática de candidatas, sin humano en el camino (decisión de Nico, 2026-10-16).

Vale bajo la enmienda AUTONOMIA-A1 (docs/incidents/AMENDMENT_AUTONOMIA-A1_2026-10-16_PROPUESTA.md). Hasta que
Nico la firme, `config["auto_promocion"]` debe quedar en False. Lo que cambia es quién aprueba, no cuánto se exige.

Orden fijo, y cualquier paso que falle corta:
  1. mecánico, sin LLM: hay estudio listo (template); límite de pruebas; novedad contra retiradas; mismo RunSpec no
     repetido; tope de promociones por ciclo;
  2. doble revisión: revisor (Opus) y, sólo si dijo PROMOTE, revisor2 (Sonnet, otra consigna, sin ver la razón del
     primero). Hacen falta los DOS PROMOTE; si no, se rechaza;
  3. pre-registro escrito y committeado por el agente ANTES de lanzar, en el clon de código, y PUBLICADO en la rama
     `autopilot/prereg/<run_id>` (si `publicar=True`): un pre-registro que sólo existe en la máquina no es trazable, así que
     si el push falla la candidata se rechaza;
  4. las guardas de siempre (guard.all_checks) sobre el RunSpec, incluida la configuración textual en el pre-registro;
  5. se agrega a candidates.json; el ciclo normal cuenta, apuesta alfa y lanza.
Cada decisión queda en promociones.jsonl (promovida o rechazada, con motivo).
"""
from __future__ import annotations
import fcntl, hashlib, json, os, subprocess, time
from pathlib import Path

from . import friccion, guard
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


def escribir_atomico(path: Path, data) -> None:
    """El ciclo lee candidates.json en cualquier momento: nunca debe ver un JSON a medias."""
    path = Path(path); tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8"); os.replace(tmp, path)


def chequeos_mecanicos(c, rs: dict | None, retiradas: list, ya: set) -> list:
    e = []
    if rs is None: e.append("sin estudio listo (NEEDS_SCRIPT): se registra como pedido de módulo, no se lanza")
    if c.n_trials > MAX_TRIALS_AUTO: e.append(f"agrega {c.n_trials} pruebas (> {MAX_TRIALS_AUTO}): sólo con revisión humana")
    nueva, parecida, sim = novedad({"familia": c.title, "mecanismo": ""}, retiradas)        # por título: el "por qué" diluye la similitud
    if not nueva: e.append(f"repite una familia retirada ({parecida}, similitud {sim})")
    if rs is not None and RunSpec.from_dict(rs).spec_hash() in ya: e.append("el mismo RunSpec ya se lanzó o se promovió")
    f = friccion.evaluar(c)
    if getattr(c, "utility_class", "bridgeable") != "info" and not f["ok"]: e.append("fricción: " + f["motivo"])   # los estudios sólo de información quedan exentos
    return e


def promover_auto(candidatas, *, draft_fn, to_runspec, runner, repo: Path, candidates_path: Path, log_path: Path,
                  retiradas=(), ya_hashes=frozenset(), max_por_ciclo: int = 1, allow_internet=frozenset(), protected=None,
                  publicar: bool = False, lock_path: Path | None = None, antecedentes_fn=None) -> list:
    """antecedentes_fn(c) -> fichas citables (conocimiento.contexto_para): el revisor pondera con lo que el proyecto ya sabe."""
    """lock_path: el `.lock` del directorio de estado del ciclo; mientras se promueve, el ciclo no corre (y viceversa)."""
    if lock_path is not None:
        Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            return promover_auto(candidatas, draft_fn=draft_fn, to_runspec=to_runspec, runner=runner, repo=repo, candidates_path=candidates_path,
                                 log_path=log_path, retiradas=retiradas, ya_hashes=ya_hashes, max_por_ciclo=max_por_ciclo,
                                 allow_internet=allow_internet, protected=protected, publicar=publicar, lock_path=None, antecedentes_fn=antecedentes_fn)
    repo, candidates_path = Path(repo), Path(candidates_path)
    cur = json.loads(candidates_path.read_text()) if candidates_path.exists() else []
    have = {c["run_id"] for c in cur} | set()
    hashes = set(ya_hashes) | {RunSpec.from_dict(c).spec_hash() for c in cur}
    out, promovidas = [], 0
    candidatas = sorted(candidatas, key=lambda c: -float(c.score) * friccion.peso(c))      # primero donde la fricción pesa menos
    for c in candidatas:
        if promovidas >= max_por_ciclo: break
        rs = to_runspec(c)
        row = dict(ts=time.time(), cid=c.cid, score=round(float(c.score), 6), friccion=friccion.evaluar(c))
        errs = chequeos_mecanicos(c, rs, list(retiradas), hashes)
        if not errs and rs["run_id"] in have: errs = ["ya está en candidates.json"]
        if errs:
            _log(log_path, dict(row, decision="RECHAZADA_MECANICO", motivos=errs)); out.append((c.cid, "RECHAZADA_MECANICO")); continue
        texto = draft_fn(c)
        ant = list(antecedentes_fn(c)) if antecedentes_fn else []
        entrada = {"borrador": texto[:9000], "publicas": dict(score=c.score, pruebas=c.n_trials, a_favor=c.pro, en_contra=c.contra, regla=c.rule)}
        if ant: entrada["antecedentes"] = ant
        row["antecedentes"] = [a_.get("ref") for a_ in ant]
        rev = runner.call("revisor", entrada)
        if rev.get("status") not in ("OK", "CACHED") or rev["output"]["decision"] != "PROMOTE":
            _log(log_path, dict(row, decision="RECHAZADA_REVISOR", revisor=rev.get("output") or rev.get("status"))); out.append((c.cid, "RECHAZADA_REVISOR")); continue
        rev2 = runner.call("revisor2", entrada)                            # misma entrada, sin la razón del primero
        row["revisor2"] = rev2.get("output") or rev2.get("status")
        if rev2.get("status") not in ("OK", "CACHED") or rev2["output"]["decision"] != "PROMOTE":
            _log(log_path, dict(row, decision="RECHAZADA_REVISOR2", revisor=rev["output"])); out.append((c.cid, "RECHAZADA_REVISOR2")); continue
        p = repo / rs["prereg"]                                            # 3) pre-registro committeado ANTES de lanzar
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(texto, encoding="utf-8")
        _git(repo, "add", "--", rs["prereg"])
        if _git(repo, "status", "--porcelain", "--", rs["prereg"]):
            _git(repo, "-c", "user.name=edgelab-agente", "-c", "user.email=agente@edgelab.local", "commit", "-q", "-m",
                 f"prereg(autopilot): {c.cid} promovido automáticamente (revisor: PROMOTE)", "--", rs["prereg"])
        sha = _git(repo, "log", "-1", "--format=%H", "--", rs["prereg"])
        rama = None
        if publicar:                                                       # trazabilidad: público antes de lanzar
            rama = f"autopilot/prereg/{rs['run_id']}"
            try: _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{rama}")
            except RuntimeError as e:
                _log(log_path, dict(row, decision="RECHAZADA_NO_PUBLICADA", motivos=[str(e)], prereg_commit=sha)); out.append((c.cid, "RECHAZADA_NO_PUBLICADA")); continue
        g = guard.all_checks(RunSpec.from_dict(rs), set(allow_internet), repo, Path(protected) if protected else None)   # 4) guardas de siempre
        if g:
            _log(log_path, dict(row, decision="RECHAZADA_GUARDAS", motivos=g, prereg_commit=sha)); out.append((c.cid, "RECHAZADA_GUARDAS")); continue
        cur.append(rs); have.add(rs["run_id"]); hashes.add(RunSpec.from_dict(rs).spec_hash())
        escribir_atomico(candidates_path, cur)
        _log(log_path, dict(row, decision="PROMOVIDA", run_id=rs["run_id"], prereg=rs["prereg"], prereg_commit=sha, prereg_rama=rama,
                            prereg_sha256=hashlib.sha256(texto.encode()).hexdigest(), revisor=rev["output"]))
        out.append((c.cid, "PROMOVIDA")); promovidas += 1
    return out
