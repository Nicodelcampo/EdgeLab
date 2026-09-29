"""NQ-CRUCE25-CLIMA v2 (pre-registro docs/research/MANIFIESTO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md). NO LANZAR sin OK de Nico.
Preflight (Entrada 067, punto 1): falla salvo snapshot de código y dataset EXACTOS; luego velas 25t de los ticks NT8 de NQ
jul–sep (catálogo NQ_ext_2026q3) con el mismo código y tools/nq_cruce25_clima.py."""
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

EXPECTED_CODE_COMMIT = "b221f7978283c4c3c0a6bbabfcb2c75e10d0d7e8"
EXPECTED_CODE_SHA256 = {  # archivos que deciden el resultado
    "tools/nq_cruce25_clima.py": "ff4bd7cc11480f210b947b41b69620cb16cc322683745e151a067c57c3536cfc",
    "tools/tbzx_iter2.py": "4376739c6bf5a9994c58cf4d22601b5f99fbbd9eb6ff200528a3196c86221c84",
    "tools/tbz_e2.py": "78fca19c64eededfbe274e6ff2f49da362257c7c3840e50221c3706a3fd5672f",
    "edgelab/bridge/indicators/espejo_impulsos.py": "c023db31077ea13fd23817b2e446a121c7b91e1014a6e5bc10e311ba91fdfbf9",
    "edgelab/research/espejo_nulo.py": "d52a4b19715f238f03f432c8c3209c135bf812de0eeec244a2aeedc7d9d39691",
}
DATASET_MANIFEST = json.loads(r'''{
 "NQ_ext_2026q3_sessions_catalog.json": "d82d38510257d8e87cf1fd834b19c0933819e75f679666a822ac37f8fc22e47a",
 "gate_report.json": "b5beb96ab1917ceadd54dc1dbf5af2d03a36f95691fe4b6528399fdeb10dff77",
 "l2_contexts_NQ_labels.parquet": "86fcf56b115a148405249d5d5211433398a827dad1375f0f6dbd2da3898ad081",
 "model.json": "b8e2095746f909f9e9b3db52171d35f344268adebdbf1a741c612a7b2fefd74a",
 "NQ_09-26_manifest_ext.json": "0dd6498f1eac7e9cda674dec4bb9e93055bb32652e253ea080478cf125aa6b16",
 "NQ_09-26_sessions_ext.json": "d03c90c1afd92f3c5ba696a65d21b508f5e3182b97ce75d0e4b4464bcdc3bdbb",
 "NQ_09-26_ticks_ext.parquet": "0010c079b73597288fb19f88a09f4edf8c9858c561d2e98e1888b3c295ffed49",
 "NQ_12-26_manifest_ext.json": "0f581d132cf107189a6e257678f0943fab18b3b44f8414604d3a2d93f5e2b4bd",
 "NQ_12-26_sessions_ext.json": "14c6e2c940b5e1c4b95b276e7cb04205021a473aebbc05e0b0c738222562487a",
 "NQ_12-26_ticks_ext.parquet": "615d489952e4fc41c117466226d65ae814fa4e387941c2ab2e9a12dfa19d7ee5"
}''')
HOLDOUT_NS = 1_790_805_600 * 1_000_000_000   # sesión CME del 1-oct-2026 (HOLDOUT-A3)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


CODE = next(p for p in Path("/kaggle/input").rglob("CODE_COMMIT.txt")).parent
DATA = next(p for p in Path("/kaggle/input").rglob("l2_contexts_NQ_labels.parquet")).parent


def preflight():
    got = (CODE / "CODE_COMMIT.txt").read_text().strip()
    assert got == EXPECTED_CODE_COMMIT, f"snapshot de código {got} != {EXPECTED_CODE_COMMIT}"
    for rel, h in EXPECTED_CODE_SHA256.items():
        assert sha(CODE / rel) == h, f"hash de código distinto: {rel}"
    seen = {}
    for rel, h in DATASET_MANIFEST.items():
        g = sha(next(DATA.rglob(rel))); seen[rel] = g
        assert g == h, f"hash de dataset distinto: {rel}"
    cat = json.loads(next(DATA.rglob("NQ_ext_2026q3_sessions_catalog.json")).read_text(encoding="utf-8"))
    ends = [int(s["end"]) for s in cat["sessions"]]
    assert max(ends) <= HOLDOUT_NS, "el catálogo llega al holdout"
    return cat, dict(code_commit=got, dataset_sha256=seen, sesiones=[(s["trade_date"], s["contract"]) for s in cat["sessions"]])


# módulo (también en los workers del pool)
if True:
    sys.path.insert(0, str(CODE)); sys.path.insert(0, str(CODE / "tools"))
    import tbz_e2 as TB  # noqa: E402
    import tbzx_iter2 as T2  # noqa: E402
    assert TB.HOLDOUT_NS == HOLDOUT_NS, "frontera del holdout distinta en tbz_e2"
    W = Path("/kaggle/working"); BARS = W / "bars_NQ"
    T2.bars_dir = lambda inst: BARS
    FILES = {p.name: p for p in DATA.rglob("*_ticks_ext.parquet")}


def build_one(s):
    return T2._bars_session(("NQ", dict(trade_date=s["trade_date"], path=str(FILES[Path(s["path"]).name]), contract=s["contract"],
                                        start=int(s["start"]), end=int(s["end"]))))


if __name__ == "__main__":
    CAT, prov = preflight()
    (W / "out").mkdir(parents=True, exist_ok=True)
    (W / "out" / "preflight.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
    print("preflight OK", prov["code_commit"], len(prov["sesiones"]), "sesiones", flush=True)
    BARS.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:  # _bars_session falla si un tick llega al holdout
        st = list(ex.map(build_one, CAT["sessions"]))
    print("velas", {k: sum(1 for _, x in st if x == k) for k in {x for _, x in st}}, flush=True)
    sys.argv = ["nq_cruce25_clima.py", "--bars", str(BARS), "--labels", str(DATA / "l2_contexts_NQ_labels.parquet"),
                "--gate", str(DATA / "gate_report.json"), "--out", str(W / "out")]
    import nq_cruce25_clima as R
    R.main()
