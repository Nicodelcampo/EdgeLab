#!/usr/bin/env python3
r"""Arma el kernel de Kaggle de la réplica AVZP2 (etapa 1 + análisis integrados) para UN instrumento, con el detector VALIDADO.

A diferencia de un kernel escrito aparte, éste se genera a partir de los archivos del repo (nada se copia a mano):
  - el indicador `edgelab/bridge/indicators/avolzonepoi2.py` (paridad exacta con aVolZonePOI2.cs) se EMBEBE reemplazando su import;
  - las barras/footprint NT8 salen de `edgelab.bridge.bars` del dataset de código `edgelab-code-avcl-fast`;
  - la etapa 1 es `tools/avzp2_racimo_replica_stage1.py` (doble modo local/Kaggle, lector de la release con preflight de ambos relojes);
  - el análisis son las funciones de `avzp2_rebote_stage2` (onehot, absorb), `avzp2_racimo_stage2` (beta, prep) y `avzp2_racimo_replica_stage2`
    (holm, analyze, analyze_all) extraídas por AST, sin ejecutar esos módulos.
Salidas del kernel: tablas por evento (parquet) y UN JSON agregado `AVZP2_RACIMO_REPLICA_V2_<INST>.json` con todas las variantes. Sin red, privado.

Uso: python tools/build_avzp2_replica_kernel.py ES --out OUT_DIR --manifest-sha256 <sha256 del release_manifest.json de la v4>
Escribe OUT_DIR/<slug>/{z.py, kernel-metadata.json} y OUT_DIR/push_request_<INST>.json (pedido listo para el inbox del puente).
"""
import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RELEASE_SLUG = "nicolasbuttaro/edgelab-liquid-ticks-20261014"
CODE_SLUG = "nicolasbuttaro/edgelab-code-avcl-fast"
IMPORT_LINE = "from edgelab.bridge.indicators.avolzonepoi2 import run as zp2_run, _racimo  # noqa: E402"


def extract(path, funcs=(), assigns=()):
    """Fuente de funciones/asignaciones de primer nivel de un módulo, sin importarlo."""
    src = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in funcs:
            out.append(ast.get_source_segment(src, n))
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assigns for t in n.targets):
            out.append(ast.get_source_segment(src, n))
    missing = (set(funcs) | set(assigns)) - {getattr(n, "name", None) for n in tree.body if isinstance(n, ast.FunctionDef)} \
        - {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    assert not missing, "no se encontraron en %s: %s" % (path, sorted(missing))
    return "\n\n\n".join(out)


ANALYSIS_DRIVER = '''

def run_analysis():
    """Análisis integrado: lee las tablas por evento de este kernel y escribe un único JSON agregado con todas las variantes."""
    t = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(OUT / ("%s_*_avzp2racgrid.parquet" % INST))))], ignore_index=True)
    out = analyze_all(t, INST)
    out["procedencia"] = dict(
        schema="avzp2_racimo_replica_v2_20261014", repo_commit=os.environ.get("EDGELAB_CODE_COMMIT", "?"), repo_tree=os.environ.get("EDGELAB_TREE", "?"),
        release_manifest_sha256=hashlib.sha256((RELEASE / "release_manifest.json").read_bytes()).hexdigest(),
        release_status=json.loads((RELEASE / "release_manifest.json").read_text(encoding="utf-8")).get("status"),
        purpose="provisional_research", holdout="excluido: preflight de trade_date y ts_utc_ns antes de leer cualquier payload",
        pnl="no calculado", filas=int(len(t)))
    p = OUT / ("AVZP2_RACIMO_REPLICA_V2_%s.json" % INST)
    p.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("RESUMEN", json.dumps({n: dict(O5=v["replica_O5"], O1=v["replica_O1"]) for n, v in out["variantes"].items()}), flush=True)
'''


def build(inst, out_dir, manifest_sha, slug_prefix="edgelab-avzp2-replica-v2"):
    s = (REPO / "tools" / "avzp2_racimo_replica_stage1.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert s.count(IMPORT_LINE) == 1, "stage1 tiene que importar avolzonepoi2 en una sola línea exacta"
    mod = (REPO / "edgelab/bridge/indicators/avolzonepoi2.py").read_text(encoding="utf-8").replace("\r\n", "\n").split("from __future__ import annotations", 1)[1]
    git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()
    commit, tree = git("rev-parse", "HEAD"), ("dirty" if git("status", "--porcelain") else "clean")
    pre = ('\nimport os\nos.environ.setdefault("AVCL_INST", "%s")\nos.environ.setdefault("EXPECT_MANIFEST_SHA256", "%s")\n'
           'os.environ.setdefault("EDGELAB_CODE_COMMIT", "%s")\nos.environ.setdefault("EDGELAB_TREE", "%s")\n') % (inst, manifest_sha or "", commit, tree)
    i = s.index("from __future__ import annotations") + len("from __future__ import annotations")
    s = s[:i] + pre + s[i:]
    s = s.replace(IMPORT_LINE, "from collections import defaultdict\n" + mod + "\nzp2_run = run\n")
    stats = ["import glob", "import scipy.sparse as sp",
             extract(REPO / "tools/avzp2_rebote_stage2.py", funcs=("onehot", "absorb")),
             extract(REPO / "tools/avzp2_racimo_stage2.py", funcs=("beta", "prep")),
             extract(REPO / "tools/avzp2_racimo_replica_stage2.py", funcs=("holm", "analyze", "analyze_all"), assigns=("MIN_RAC", "O5_CELLS", "O1_CELLS"))]
    marker = 'if __name__ == "__main__":'
    j = s.rindex(marker)
    s = s[:j] + "\n\n".join(stats) + "\n" + ANALYSIS_DRIVER + "\n\n" + s[j:]
    ast.parse(s)                                               # el kernel tiene que compilar
    slug = "%s-%s" % (slug_prefix, inst.lower())
    d = Path(out_dir) / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "z.py").write_text(s, encoding="utf-8")
    meta = dict(id="nicolasbuttaro/" + slug, title=slug, code_file="z.py", language="python", kernel_type="script", is_private=True,
                enable_gpu=False, enable_internet=False, dataset_sources=[RELEASE_SLUG, CODE_SLUG], competition_sources=[], kernel_sources=[])
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    req = dict(request_id="push_%s_v2" % inst.lower(), action="push_kernel",
               params=dict(slug=slug, title=slug, script=s, accelerator="cpu", dataset_sources=[RELEASE_SLUG, CODE_SLUG], enable_internet=False))
    (Path(out_dir) / ("push_request_%s.json" % inst)).write_text(json.dumps(req), encoding="utf-8")
    return dict(slug=slug, z_py=str(d / "z.py"), sha256=hashlib.sha256(s.encode("utf-8")).hexdigest(), lines=s.count("\n"), commit=commit, tree=tree)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inst"); ap.add_argument("--out", required=True); ap.add_argument("--manifest-sha256", default="")
    a = ap.parse_args()
    print(json.dumps(build(a.inst.upper(), a.out, a.manifest_sha256.lower()), indent=1))
