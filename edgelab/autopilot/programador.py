"""Rol programador: el agente del Debian escribe código (pedido de Nico, 2026-10-22: «el agente del debian sí puede escribir
código; si no puede ahora, debería poder»).

Lo que se aplica solo y lo que no lo decide este módulo por la RUTA de cada archivo tocado, no un prompt:

| zona | ejemplos | qué pasa |
|---|---|---|
| perímetro del agente | `edgelab/research/agente/`, `tools/agente/`, `tests/agente/`, `docs/research/agente/`, `config/autopilot/grillas/` | con tests verdes y controles, se commitea y se aplica en el checkout del Debian; la corrida queda atada al commit (la guarda exige script committeado) |
| motor compartido | `edgelab/research/*.py`, `edgelab/funnel/`, `tools/*.py`, tests existentes | se commitea en una rama `autopilot/propuesta/<id>` y se registra en `mejoras.jsonl`; lo mergea una persona |
| reglas | guardas, FDR, holdout, costos, mandato, protegidos, `edgelab/autopilot/`, `deploy/` | se rechaza entero: un sistema que pudiera reescribir sus reglas fabricaría falsos positivos |

Un cambio mixto toma la zona más restrictiva. El código se escribe en una worktree descartable, nunca en el checkout vivo.
Todo experimento nuevo del perímetro trae sus controles (`docs/research/GUIA_GRILLA_MASIVA.md` §1): ruido puro sin
hallazgos, efecto plantado encontrado y, si usa numba, oráculo en Python con empates. Sin eso no se aplica.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

from .mejora import NUNCA, RegistroMejoras

PERIMETRO = ("edgelab/research/agente/", "tools/agente/", "tests/agente/", "docs/research/agente/", "config/autopilot/grillas/")
REGLAS = NUNCA + ("edgelab/autopilot/", "edgelab/holdout.py", "edgelab/costos.py", "config/costos/", "config/autopilot/protected.json",
                  "config/autopilot/mandate.json", "edgelab/research/holdout_guard.py", "edgelab/funnel/multiplicity.py", "deploy/",
                  "tests/conftest.py", ".gitattributes", ".gitignore", "CLAUDE.md", "docs/incidents/", "docs/data_catalog/")
# Campañas: definen familia, holdout.desde, n_fijo y activa (reglas por la puerta de datos). Nunca se aplican solas: PROPUESTA
# (revisión 2026-10-24: renombrar una familia reiniciaría LORD++; mover holdout.desde reabriría ventanas consumidas).
SOLO_PROPUESTA = ("config/autopilot/grillas/campanas/",)
ORDEN = {"PERIMETRO": 0, "PROPUESTA": 1, "SOLO_HUMANO": 2}
LOG = "programacion.jsonl"
PEDIDOS = "pedidos_codigo.jsonl"


def zona(path: str, protegidos=()) -> str:
    p = path.replace("\\", "/").removeprefix("./")
    if p in protegidos or any(p == r or (r.endswith("/") and p.startswith(r)) for r in REGLAS): return "SOLO_HUMANO"
    if any(p.startswith(r) for r in SOLO_PROPUESTA): return "PROPUESTA"
    if any(p.startswith(r) for r in PERIMETRO): return "PERIMETRO"
    return "PROPUESTA"


def clasificar(paths, protegidos=()) -> str:
    return max((zona(p, protegidos) for p in paths), key=ORDEN.get, default="PERIMETRO")


def controles_faltantes(wt: Path, paths) -> list:
    """Cada módulo de experimento del perímetro necesita su archivo de tests con los controles de la guía."""
    falta = []
    for p in paths:
        p = p.replace("\\", "/")
        if not (p.startswith("edgelab/research/agente/") and p.endswith(".py")) or p.endswith("__init__.py") or not (wt / p).exists(): continue
        stem = Path(p).stem; t = wt / "tests/agente" / f"test_{stem}.py"
        if not t.exists(): falta.append(f"{p}: falta tests/agente/test_{stem}.py"); continue
        txt, src = t.read_text(encoding="utf-8", errors="replace"), (wt / p).read_text(encoding="utf-8", errors="replace")
        exp = "def disparos(" in src                                 # experimento de grilla genérica (grilla_generica.py)
        req = ("test_control_ruido", "test_control_plantado") + (("test_oraculo",) if re.search(r"\bnumba\b|@njit|@jit", src) else ()) + (("test_causal",) if exp else ())
        for f in req:
            if not re.search(rf"def {f}\w*\(", txt): falta.append(f"{p}: falta {f} en tests/agente/test_{stem}.py")
        if exp and not re.search(r"^INDICADORES\s*=", src, re.M): falta.append(f"{p}: un experimento declara INDICADORES (config/autopilot/indicadores.json)")
    return falta


def preflight_experimentos(wt: Path, paths, python: str, timeout: int) -> list:
    """`edgelab.research.preflight` sobre cada experimento de grilla nuevo o cambiado: interfaz, indicadores, causalidad, cortes,
    potencia del control, ruido sin rechazos, perillas muertas. Corre en la worktree (el código del agente, no el vivo)."""
    out = []
    for p in paths:
        p = p.replace("\\", "/")
        if not (p.startswith("edgelab/research/agente/") and p.endswith(".py")) or not (wt / p).exists(): continue
        if "def disparos(" not in (wt / p).read_text(encoding="utf-8", errors="replace"): continue
        mod = p[:-3].replace("/", ".")
        r = subprocess.run([python, "-m", "edgelab.research.preflight", mod], cwd=wt, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=dict(os.environ, NUMBA_CACHE_DIR=str(wt / ".numba_cache")))
        if r.returncode != 0: out.append(f"{mod}: {(r.stdout + r.stderr)[-600:]}")
    return out


def _git(*a, cwd, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode: raise RuntimeError(f"git {' '.join(a[:2])}: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def cambios(wt: Path) -> list:
    """Archivos tocados en la worktree (incluye nuevos y borrados), relativos a la raíz."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "-z"], cwd=wt, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=True).stdout   # sin strip: el primer espacio es parte del estado
    paths, it = [], iter(out.split("\0"))
    for e in it:
        if not e: continue
        st, p = e[:2], e[3:]
        if "R" in st or "C" in st: paths.append(next(it, ""))   # renombre: también cuenta el origen
        paths.append(p)
    return sorted({p for p in paths if p})


SISTEMA = ("Sos el programador del agente de investigación EdgeLab. Escribís código Python en el directorio actual (una worktree "
           "descartable). Seguí docs/research/GUIA_GRILLA_MASIVA.md, docs/research_funnel_playbook.md y docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md "
           "(errores que no se repiten: leelo antes de escribir). Reglas fijas: el código nuevo de "
           "experimentos va en edgelab/research/agente/, sus kernels en tools/agente/, sus tests en tests/agente/ y su documentación en "
           "docs/research/agente/. Cada módulo de experimento trae tests/agente/test_<modulo>.py con test_control_ruido (ruido puro sin "
           "hallazgos), test_control_plantado (efecto plantado encontrado) y, si usa numba, test_oraculo (Python simple con empates). "
           "Reutilizá edgelab/research/grilla_masiva.py, edgelab/funnel/escalera.py, edgelab/costos.py y edgelab/holdout.py; no los copies. "
           "Un barrido nuevo es un módulo con la interfaz de edgelab/research/grilla_generica.py (NOMBRE, disparos, VARIABLES, "
           "EJECUCIONES, niveles, EJES_ORDINALES, BASE, INDICADORES); el ejemplo es edgelab/research/u1_indaga.py. Sólo usa indicadores "
           "PASS de config/autopilot/indicadores.json o indicadores propios NATIVO_AGENTE con test_causal (edgelab/research/indicadores.causal), registrados en config/autopilot/grillas/indicadores_agente.json (sólo ese estado). "
           "El kernel se arma con tools/kaggle_grilla/construir_kernel_experimento.py y va a tools/agente/kernel_<nombre>.py. "
           "Para que se lance, escribí su campaña en config/autopilot/grillas/campanas/<id>.json con \"embudo\": true y \"conductor\": \"debian\" (formato en "
           "docs/research/GUIA_GRILLA_MASIVA.md §8): el embudo hace solo preflight, descubrimiento, indagación, integridad, OOS, topes, "
           "acta y holdout. "
           "Antes de un P&L básico de una variante buena, indagala con marginales (ATJ-26). "
           "Antes de terminar corré `python -m edgelab.research.preflight <tu módulo>`: si falla, el cambio no se aplica (ATJ-27). "
           "Si hace falta mejorar el motor compartido, hacelo igual: quedará como propuesta para revisión humana. Nunca toques guardas, "
           "FDR, holdout, costos, mandato ni edgelab/autopilot/: ese cambio se descarta entero. No leas datos del holdout. Corré los tests "
           "antes de terminar. Respondé con un resumen corto de qué hiciste y qué falta.")


def claude_code_cli(prompt, *, cwd, model, python, timeout=3600):
    """Única llamada real: Claude Code headless con herramientas de archivo y SÓLO pytest/git de lectura en Bash. Sin MCP ni settings."""
    env = {k: os.environ[k] for k in ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "APPDATA", "LOCALAPPDATA", "CLAUDE_CODE_OAUTH_TOKEN", "TMPDIR", "TEMP", "TMP") if k in os.environ}
    env["NUMBA_CACHE_DIR"] = str(Path(cwd) / ".numba_cache")
    permitidas = ["Read", "Edit", "Write", "Glob", "Grep", f"Bash({python} -m pytest:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)"]
    argv = ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--append-system-prompt", SISTEMA,
            "--allowedTools", *permitidas, "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence"]
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env, shell=False)
    try: return json.loads(r.stdout)
    except json.JSONDecodeError: return {"is_error": True, "result": (r.stdout + r.stderr)[-500:]}


def correr_tests(wt: Path, python: str, tests, timeout: int):
    env = dict(os.environ, NUMBA_CACHE_DIR=str(wt / ".numba_cache"), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([python, "-m", "pytest", *tests, "-q", "-m", "not vectorbt", "-p", "no:cacheprovider"], cwd=wt, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def pendientes(root: Path) -> list:
    """Pedidos de código sin procesar (los escriben el proponente, la mejora de módulos o una persona)."""
    f, hechos = root / PEDIDOS, {r.get("pedido") for r in _filas(root / LOG)}
    return [p for p in _filas(f) if p.get("id") and p["id"] not in hechos]


def _filas(f: Path):
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []


def pedir(root: Path, que: str, por_que: str, aceptacion: str = "", origen: str = "humano", pid: str | None = None) -> dict:
    row = dict(id=pid or f"cod-{int(time.time())}", ts=time.time(), que=que, por_que=por_que, aceptacion=aceptacion, origen=origen)
    with (Path(root) / PEDIDOS).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def existentes(repo: Path, consulta: str, k: int = 12) -> str:
    """Lo que ya hay en el repo para este pedido (tools/existente.py buscar): va en el prompt para que no se reconstruya
    (pedido de Nico, 2026-10-24). Las copias igual las frena tests/test_existente.py, que corre antes de aplicar."""
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("existente", Path(repo) / "tools" / "existente.py")
        E = importlib.util.module_from_spec(sp); sp.loader.exec_module(E)
        res = E.buscar(consulta, k=k, root=Path(repo))
    except Exception as e:                                                  # sin buscador el pedido sigue, pero se dice
        return f"(no se pudo buscar lo existente: {type(e).__name__})\n"
    filas = "\n".join(f"- {r['ref']} {r['nombre']}: {r['doc']}" for r in res)
    return ("REUTILIZAR ANTES DE CONSTRUIR. Esto ya existe en el repo y puede hacer parte del pedido; también mirá docs/MODULES.md y "
            "docs/HERRAMIENTAS.md, y buscá más con `python tools/existente.py buscar \"...\"`. Si algo sirve, importalo o reemplazá su "
            "lector; si construís algo nuevo, el resumen final dice qué encontraste y por qué no sirve. Una función copiada hace "
            f"fallar tests/test_existente.py.\n{filas}\n")


def programar(pedido: dict, *, repo: Path, root: Path, cli=claude_code_cli, model: str = "claude-opus-5-5", python: str = sys.executable,
              tests=("tests",), timeout_s: int = 3600, protegidos=(), push: bool = True, aplicar: bool = True, ahora=None) -> dict:
    """Un pedido -> worktree -> código -> zona -> controles -> tests -> commit -> aplicar o proponer. Siempre deja una fila en programacion.jsonl."""
    repo, root = Path(repo), Path(root); pid = re.sub(r"[^A-Za-z0-9_-]", "-", pedido["id"])[:60]
    wt = root / "programador" / pid; row = dict(ts=ahora or time.time(), pedido=pedido["id"], que=pedido.get("que", ""))
    antes = _git("status", "--porcelain", cwd=repo); base = _git("rev-parse", "HEAD", cwd=repo); row["base"] = base
    if wt.exists(): shutil.rmtree(wt, ignore_errors=True); _git("worktree", "prune", cwd=repo, check=False)
    wt.parent.mkdir(parents=True, exist_ok=True); _git("worktree", "add", "-q", "--detach", str(wt), base, cwd=repo)
    try:
        prompt = (f"Pedido {pedido['id']}: {pedido.get('que', '')}\nPor qué: {pedido.get('por_que', '')}\n"
                  f"Aceptación: {pedido.get('aceptacion') or 'tests verdes y controles de la guía'}\nPython del entorno: {python}\n"
                  + existentes(repo, f"{pedido.get('que', '')} {pedido.get('por_que', '')}"))
        resp = cli(prompt, cwd=str(wt), model=model, python=python, timeout=timeout_s)
        row["resumen"] = str((resp or {}).get("result", ""))[-1500:]
        if _git("status", "--porcelain", cwd=repo) != antes:      # escribió fuera de la worktree: no se usa nada y se avisa
            return _fin(root, row, "INCIDENTE", detalle="el checkout vivo cambió durante la programación; revisar a mano")
        shutil.rmtree(wt / ".numba_cache", ignore_errors=True)
        paths = cambios(wt); row["archivos"] = paths
        if not paths: return _fin(root, row, "SIN_CAMBIOS")
        z = clasificar(paths, protegidos); row["zona"] = z
        if z == "SOLO_HUMANO":
            return _fin(root, row, "RECHAZADO", detalle=[p for p in paths if zona(p, protegidos) == "SOLO_HUMANO"])
        if (falta := controles_faltantes(wt, paths)): return _fin(root, row, "FALLA_CONTROLES", detalle=falta)
        rc, out = correr_tests(wt, python, list(tests), timeout_s); row["tests"] = out[-800:]
        if rc != 0: return _fin(root, row, "FALLA_TESTS")
        if (pf := preflight_experimentos(wt, paths, python, timeout_s)): return _fin(root, row, "FALLA_PREFLIGHT", detalle=pf)
        _git("add", "-A", "--", *paths, cwd=wt)
        _git("-c", "user.name=edgelab-autopilot", "-c", "user.email=autopilot@localhost", "commit", "-q", "-m",
             f"agente({pid}): {pedido.get('que', '')[:60]}\n\nPedido {pedido['id']} · zona {z} · tests verdes.\n{pedido.get('por_que', '')[:400]}", cwd=wt)
        sha = _git("rev-parse", "HEAD", cwd=wt); row["commit"] = sha
        rama = f"autopilot/{'codigo' if z == 'PERIMETRO' else 'propuesta'}/{pid}"; row["rama"] = rama
        if push:                                                  # sin deploy key queda local; el commit igual existe y update.sh lo protege
            row["push_ok"] = subprocess.run(["git", "push", "-q", "origin", f"{sha}:refs/heads/{rama}"], cwd=wt, capture_output=True).returncode == 0
        if z == "PROPUESTA":
            RegistroMejoras(root / "mejoras.jsonl").proponer("modulo", pedido.get("que", ""), f"rama {rama} @ {sha[:12]}, tests verdes", archivos=paths, origen="programador")
            return _fin(root, row, "PROPUESTA")
        if not aplicar: return _fin(root, row, "LISTO_SIN_APLICAR")
        if _git("rev-parse", "HEAD", cwd=repo) != base or _git("status", "--porcelain", cwd=repo) != antes:
            return _fin(root, row, "FALLA_APLICAR", detalle="el checkout cambió mientras se programaba; se reintenta en el próximo ciclo")
        r = subprocess.run(["git", "-c", "user.name=edgelab-autopilot", "-c", "user.email=autopilot@localhost", "cherry-pick", sha], cwd=repo, capture_output=True, text=True)
        if r.returncode:
            _git("cherry-pick", "--abort", cwd=repo, check=False)
            return _fin(root, row, "FALLA_APLICAR", detalle=r.stderr[-300:])
        row["commit_aplicado"] = _git("rev-parse", "HEAD", cwd=repo)
        return _fin(root, row, "APLICADO")
    finally:
        _git("worktree", "remove", "--force", str(wt), cwd=repo, check=False); shutil.rmtree(wt, ignore_errors=True)


def _fin(root: Path, row: dict, estado: str, detalle=None) -> dict:
    row.update(estado=estado, **({"detalle": detalle} if detalle is not None else {}))
    with (root / LOG).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def ciclo(root: Path, repo: Path, cfg: dict, cli=claude_code_cli, ahora=None) -> list:
    """Lo que corre el timer: a lo sumo `max_por_dia` pedidos por día, en orden de llegada."""
    c = cfg.get("programador") or {}
    if not c.get("activo"): return []
    ahora = ahora or time.time(); hoy = [r for r in _filas(Path(root) / LOG) if ahora - r.get("ts", 0) < 86400]
    cupo = int(c.get("max_por_dia", 1)) - len(hoy)
    prot = tuple(json.loads(Path(cfg["protected"]).read_text())) if cfg.get("protected") and Path(cfg["protected"]).exists() else ()
    return [programar(p, repo=repo, root=root, cli=cli, model=c.get("modelo", "claude-opus-5-5"), python=c.get("python", sys.executable),
                      tests=tuple(c.get("tests", ["tests"])), timeout_s=int(c.get("timeout_s", 3600)), protegidos=prot,
                      push=bool(c.get("push", True)), aplicar=bool(c.get("aplicar", True)), ahora=ahora)
            for p in pendientes(Path(root))[:max(cupo, 0)]]
