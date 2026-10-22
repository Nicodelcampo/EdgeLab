"""Biblioteca del agente: todo lo que el proyecto sabe, indexado con trazabilidad (pedido de Nico, 2026-10-19).

El proponente, el revisor y los informes deben ponderar con TODA la información del proyecto, no con lo que entre en un
prompt armado a mano. Este módulo, sin LLM y determinista:
  1. `indexar`: recorre las fuentes declaradas en FUENTES (cerebro/hipocampo, papers SSRN y literatura, research propio,
     resultados del autopilot, registros de pruebas, edges, mandato) y las del estado vivo; parte cada archivo en pasajes;
     cada pasaje lleva ruta, sha256 del archivo, último commit que lo tocó y número de línea;
  2. `buscar`: recuperación léxica (BM25) sobre los pasajes; devuelve citas verificables;
  3. `tablero`: hechos que se recuerdan en todos los ciclos (familias retiradas, edges promovidos, corridas del ledger);
  4. `contexto_para`: arma las fichas y vacíos para `contexto.armar_paquete` y devuelve la lista de fuentes usadas
     (id + sha256), que se guarda junto a cada propuesta para poder reconstruir con qué información se decidió.
Lo recuperado es CONTEXTO, nunca evidencia: la literatura y los resúmenes no cuentan como prueba propia.
"""
from __future__ import annotations
import glob, hashlib, json, math, re, subprocess, time
from collections import Counter
from pathlib import Path

# (tipo, patrón glob relativo al repo). Agregar una fuente = agregar una línea; el índice registra qué patrón la trajo.
FUENTES = [                    # el orden importa: un archivo queda con el tipo del PRIMER patrón que lo trae
    ("mandato", "MANDATO.md"), ("mandato", "docs/NORTH_STAR.md"), ("mandato", "docs/edge_validation_contract.md"),
    ("edges", "EDGES_DISCOVERED.md"), ("edges", "PENDIENTE.md"),
    ("cerebro", "docs/research/edge_brain/*.jsonl"), ("cerebro", "docs/research/**/edge_brain_ledger.jsonl"),
    ("autopilot", "docs/research/autopilot_runs/*.md"), ("autopilot", "docs/autopilot/*.md"),
    ("registro", "docs/research/**/TRIAL_REGISTRY*.json*"), ("registro", "config/autopilot/evidence_seed.json"),
    ("papers", "corpus/ssrn/cerebro/*.md"), ("papers", "corpus/ssrn/*.md"), ("papers", "config/autopilot/literature_leads.json"),
    ("papers", "corpus/ssrn/extraccion/completo/**/*"), ("papers", "corpus/ssrn/grafo/*.md"),
    ("papers", "corpus/ssrn/Normalizado/documentos/*.txt"),
    ("research", "docs/research/*MEDIDO_Y_NO_MEDIDO*.md"), ("research", "docs/research/**/RESULTADO*.md"),
    ("research", "docs/research/**/PREREG*.md"), ("research", "docs/research/**/*.md"), ("research", "docs/incidents/*.md"),
]
# Estado vivo (fuera del repo): rutas relativas al directorio de estado del autopilot.
FUENTES_ESTADO = [("cerebro", "edge_brain_ledger.jsonl"), ("registro", "trial_registry.jsonl"), ("autopilot", "evidence_runtime.jsonl"),
                  ("autopilot", "promociones.jsonl"), ("autopilot", "propuestas.jsonl"), ("autopilot", "mejoras.jsonl")]
MAX_BYTES = 2_000_000          # un archivo más grande se indexa sólo por su cabecera (se marca truncado)
PASAJE_LINEAS = 25


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _commit(repo: Path, rel: str) -> str | None:
    r = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=repo, capture_output=True, text=True)
    return r.stdout.strip() or None


def _tokens(s: str) -> list:
    return [t for t in re.findall(r"[a-záéíóúñü0-9_]+", s.lower()) if len(t) > 2]


def _pasajes(texto: str):
    lineas = texto.splitlines()
    for i in range(0, len(lineas), PASAJE_LINEAS):
        bloque = "\n".join(lineas[i:i + PASAJE_LINEAS]).strip()
        if bloque: yield i + 1, bloque


def indexar(repo: Path, estado: Path | None = None, fuentes=FUENTES, con_commit: bool = True) -> dict:
    repo = Path(repo); docs, vistos = [], set()
    cands = [(t, p, repo, False) for t, p in fuentes] + ([(t, p, Path(estado), True) for t, p in FUENTES_ESTADO] if estado else [])
    for tipo, patron, base, vivo in cands:
        for f in sorted(glob.glob(str(base / patron), recursive=True)):
            fp = Path(f)
            if not fp.is_file() or fp.resolve() in vistos or "/archive/" in fp.as_posix(): continue          # as_posix: en Windows glob devuelve "\\"
            vistos.add(fp.resolve()); raw = fp.read_bytes(); trunc = len(raw) > MAX_BYTES
            rel = fp.relative_to(base).as_posix()                                                   # misma clave en Windows y en el Debian
            docs.append(dict(id=("estado:" if vivo else "") + rel, tipo=tipo, patron=patron, sha256=_sha(raw), bytes=len(raw), truncado=trunc,
                             commit=None if (vivo or not con_commit) else _commit(repo, rel),
                             texto=raw[:MAX_BYTES].decode("utf-8", errors="replace")))
    idx = dict(creado=time.time(), repo_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip() or None,
               docs=[{k: v for k, v in d.items() if k != "texto"} for d in docs], pasajes=[])
    for d in docs:
        for linea, txt in _pasajes(d["texto"]):
            idx["pasajes"].append(dict(doc=d["id"], tipo=d["tipo"], linea=linea, texto=txt))
    idx["huella"] = _sha(json.dumps([(d["id"], d["sha256"]) for d in idx["docs"]]).encode())
    return idx


def guardar(idx: dict, path: Path) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({k: v for k, v in idx.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8"); tmp.replace(path)


def cargar(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifiesto(idx: dict) -> dict:
    """Lo que se sube a autopilot/state: qué versión exacta de cada fuente tenía el agente (sin el texto)."""
    return dict(creado=idx["creado"], repo_head=idx["repo_head"], huella=idx["huella"], docs=idx["docs"])


def _prep(idx: dict):
    """Índice invertido en memoria (no se guarda): postings por término, largo de cada pasaje."""
    if "_inv" not in idx:
        inv, lens = {}, []
        for i, p in enumerate(idx["pasajes"]):
            ts = _tokens(p["texto"]); lens.append(len(ts))
            for t, n in Counter(ts).items(): inv.setdefault(t, []).append((i, n))
        idx["_inv"], idx["_lens"] = inv, lens
    return idx["_inv"], idx["_lens"]


def buscar(idx: dict, consulta: str, k: int = 8, tipos=None, k1: float = 1.4, b: float = 0.75) -> list:
    """BM25 sobre pasajes. Devuelve [{doc, tipo, linea, sha256, score, texto}] (texto recortado)."""
    if not idx["pasajes"]: return []
    inv, lens = _prep(idx); n = len(lens); avg = sum(lens) / n or 1; ps = idx["pasajes"]; score = Counter()
    for t in set(_tokens(consulta)):
        post = inv.get(t, []); idf = math.log(1 + (n - len(post) + .5) / (len(post) + .5))
        for i, tf in post:
            if tipos and ps[i]["tipo"] not in tipos: continue
            score[i] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * lens[i] / avg))
    sha = {d["id"]: d["sha256"] for d in idx["docs"]}
    top = sorted(score.items(), key=lambda x: (-x[1], ps[x[0]]["doc"], ps[x[0]]["linea"]))[:k]
    return [dict(doc=ps[i]["doc"], tipo=ps[i]["tipo"], linea=ps[i]["linea"], sha256=sha.get(ps[i]["doc"]), score=round(s, 3), texto=ps[i]["texto"][:700]) for i, s in top]


def tablero(idx: dict, cfg: dict | None = None, outcomes: list | None = None) -> dict:
    cfg = cfg or {}; por_tipo = Counter(d["tipo"] for d in idx["docs"])
    edges = next((p["texto"][:600] for p in idx["pasajes"] if p["doc"] == "EDGES_DISCOVERED.md"), None)
    return dict(fuentes_por_tipo=dict(por_tipo), huella_biblioteca=idx["huella"], repo_head=idx["repo_head"],
                familias_retiradas=list(cfg.get("familias_retiradas", [])), edges_promovidos=edges,
                corridas=[{k: o.get(k) for k in ("run_id", "family", "hit", "status") if k in o} for o in (outcomes or [])][-30:])


def contexto_para(idx: dict, tema: str, k_papers: int = 5, k_propio: int = 7) -> dict:
    """Fichas citables para el proponente: literatura y research propio por separado (la literatura no es evidencia propia).
    `fuentes` = (doc, sha256, línea) de todo lo entregado: se guarda con la propuesta."""
    lit = buscar(idx, tema, k_papers, tipos={"papers"})
    propio = buscar(idx, tema, k_propio, tipos={"research", "cerebro", "autopilot", "registro", "edges"})
    fichas = [dict(ref=f"{x['doc']}#L{x['linea']}", tipo=x["tipo"], pasaje=x["texto"]) for x in lit + propio]
    vacios = [f"{x['doc']}#L{x['linea']}" for x in propio if re.search(r"NO MEDIDO|no medido|pendiente|falta", x["texto"])]
    return dict(fichas=fichas, vacios=vacios, fuentes=[(x["doc"], x["sha256"], x["linea"]) for x in lit + propio])
