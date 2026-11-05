import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.kaggle_drive_bridge import (
    BridgePolicy,
    KaggleBridgeError,
    load_kaggle_auth_headers,
    normalize_dataset_files_payload,
    process_bridge_request,
    reassemble_drive_chunks,
    sanitize_request_id,
    split_file_into_drive_chunks,
    watch_bridge_directory,
    check_patch,
)


class _FakeKaggleClient:
    def __init__(self):
        self.pushed = []

    def search_datasets(self, query: str, max_results: int = 20, sort_by: str = "updated", page: int = 1):
        return {"query": query, "page": page, "returned_count": 1, "potentially_truncated": False, "results": [{"ref": "nicolasbuttaro/edgelab-data-catalog"}]}

    def list_my_datasets(self, query=None, page: int = 1):
        return {"group": "my", "page": page, "returned_count": 1, "potentially_truncated": False, "results": [{"ref": "nicolasbuttaro/edgelab-data-catalog"}]}

    def list_dataset_files(self, dataset: str, page_size: int = 100, page_token=None):
        return normalize_dataset_files_payload(
            {"datasetFiles": [{"name": "discovery.json", "totalBytes": 1234}], "nextPageToken": "tok_2"},
            requested_page_size=page_size,
        )

    def inspect_dataset(self, dataset: str):
        return {"dataset": dataset, "metadata": {"title": "Catalog"}, "files_listing": self.list_dataset_files(dataset)}

    def read_dataset_file_preview(self, dataset: str, file_name: str, max_bytes: int = 200_000):
        return {"dataset": dataset, "file": file_name, "bytes_returned": 4, "truncated": False, "content": "test"}

    def download_dataset_file_to_path(self, dataset: str, file_name: str, dest_path: Path):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = b"PAR1_FAKE_PARQUET_PAYLOAD_" * 1000
        dest_path.write_bytes(payload)
        return {
            "dataset": dataset,
            "file": file_name,
            "local_path": str(dest_path),
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }

    def push_kernel(self, slug: str, title: str, script_text: str, accelerator: str = "cpu", dataset_sources=None, kernel_sources=None, enable_internet: bool = False):
        self.pushed.append(dict(slug=slug, enable_internet=enable_internet, sources=list(dataset_sources or []), kernel_sources=list(kernel_sources or [])))
        return {"slug": slug, "accelerator": accelerator, "enableInternet": enable_internet, "sources": list(dataset_sources or []), "kernelSources": list(kernel_sources or [])}

    def get_kernel_status(self, owner: str, slug: str, version_label=None):
        return {"status": "COMPLETE", "owner": owner, "slug": slug}

    def get_kernel_output(self, owner: str, slug: str, page_size: int = 50, page_token=None):
        return {"owner": owner, "slug": slug, "log": "OK_LOG", "files": [{"fileName": "out.json"}]}


class TestKaggleDriveBridge(unittest.TestCase):
    def test_dataset_files_parser_recognizes_datasetFiles_and_truncation(self):
        payload = {
            "datasetFiles": [
                {"name": "ES_12-25.parquet", "totalBytes": 1048576, "creationDate": "2026-10-01T00:00:00Z"},
                {"name": "NQ_12-25.parquet", "totalBytes": 2097152, "creationDate": "2026-10-01T00:00:00Z"},
            ],
            "nextPageToken": "page_2_token",
        }
        res = normalize_dataset_files_payload(payload, requested_page_size=50)
        self.assertEqual(res["returned_count"], 2)
        self.assertEqual(res["files"][0]["name"], "ES_12-25.parquet")
        self.assertEqual(res["files"][0]["totalBytes"], 1048576)
        self.assertEqual(res["next_page_token"], "page_2_token")
        self.assertTrue(res["is_truncated"])
        self.assertFalse(res["exhaustive"])

    def test_chunk_split_and_reassemble_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "sample.parquet"
            raw_bytes = b"0123456789abcdef" * 4096
            src.write_bytes(raw_bytes)
            expected_sha = hashlib.sha256(raw_bytes).hexdigest()

            chunks_dir = tmp_path / "chunks"
            manifest = split_file_into_drive_chunks(
                src,
                chunks_dir,
                chunk_size_bytes=16384,
                expected_sha256=expected_sha,
                expected_size_bytes=len(raw_bytes),
            )
            self.assertEqual(manifest["chunk_count"], 4)
            self.assertEqual(manifest["sha256"], expected_sha)

            restored = tmp_path / "restored.parquet"
            manifest_file = chunks_dir / "sample.parquet.manifest.json"
            out = reassemble_drive_chunks(manifest_file, restored)
            self.assertEqual(out["sha256"], expected_sha)
            self.assertEqual(restored.read_bytes(), raw_bytes)

            part0 = chunks_dir / manifest["chunks"][0]["filename"]
            part0.write_bytes(b"TAMPERED" + part0.read_bytes()[8:])
            with self.assertRaises(KaggleBridgeError):
                reassemble_drive_chunks(manifest_file, tmp_path / "bad.parquet")

    def test_auth_headers_from_env_and_kaggle_json(self):
        h1 = load_kaggle_auth_headers(env={"KAGGLE_API_TOKEN": "tok_secret_123"})
        self.assertEqual(h1["Authorization"], "Bearer tok_secret_123")

        with tempfile.TemporaryDirectory() as tmp:
            kjson = Path(tmp) / "kaggle.json"
            kjson.write_text(json.dumps({"username": "nico", "key": "key123"}), encoding="utf-8")
            h2 = load_kaggle_auth_headers(env={}, kaggle_json_path=kjson)
            self.assertTrue(h2["Authorization"].startswith("Basic "))

    def test_watch_directory_processes_inbox_and_writes_outbox_con_politica_de_datos_habilitada(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "EdgeLab_Bridge"
            (bdir / "inbox").mkdir(parents=True)
            req = {
                "request_id": "job_001",
                "action": "download_file_chunked",
                "params": {
                    "dataset": "nicolasbuttaro/edgelab-data-catalog/15",
                    "file": "sample.parquet",
                    "chunk_size_bytes": 10000,
                },
            }
            (bdir / "inbox" / "job_001.json").write_text(json.dumps(req), encoding="utf-8")
            watch_bridge_directory(bdir, _FakeKaggleClient(), max_loops=1, policy=BridgePolicy(allow_data_download=True, allowed_source_owners=("nicolasbuttaro",)))

            resp_path = bdir / "outbox" / "job_001.response.json"
            self.assertTrue(resp_path.is_file())
            resp = json.loads(resp_path.read_text(encoding="utf-8"))
            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp["result"]["manifest"]["chunk_count"], 3)
            self.assertTrue((bdir / "processed" / "job_001.json").is_file())


class TestHardening(unittest.TestCase):
    def test_request_id_traversal_es_rechazado_y_no_borra_ni_escribe_fuera(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bdir = root / "Drive" / "EdgeLab_Bridge"
            victim = root / "victima"
            victim.mkdir()
            (victim / "dato.txt").write_text("no me borres", encoding="utf-8")
            (bdir / "inbox").mkdir(parents=True)
            for i, rid in enumerate(["../../victima", "..", "a/b", "x" * 200, "../victima"]):
                req = {"request_id": rid, "action": "ping", "params": {}}
                (bdir / "inbox" / f"evil_{i}.json").write_text(json.dumps(req), encoding="utf-8")
            watch_bridge_directory(bdir, _FakeKaggleClient(), max_loops=1)
            self.assertTrue((victim / "dato.txt").is_file())
            for p in (bdir / "outbox").glob("*.json"):
                self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["status"], "ERROR")
            self.assertEqual(sorted(x.name for x in root.iterdir()), ["Drive", "victima"])    # nada escrito fuera del puente

    def test_sanitize_request_id(self):
        self.assertEqual(sanitize_request_id("job_001.v2-a"), "job_001.v2-a")
        for bad in ("", "../x", "a..b", "a/b", "a\\b", ".oculto", "x" * 65):
            with self.assertRaises(KaggleBridgeError):
                sanitize_request_id(bad)

    def test_push_kernel_apagado_por_defecto(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = _FakeKaggleClient()
            req = {"request_id": "p1", "action": "push_kernel", "params": {"slug": "mi-kernel", "title": "t", "script": "print(1)"}}
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request(req, cli, Path(tmp))
            self.assertEqual(cli.pushed, [])

    def test_push_kernel_encendido_nunca_con_internet_y_solo_owners_permitidos(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = _FakeKaggleClient()
            pol = BridgePolicy(allow_push=True, allowed_source_owners=("nicolasbuttaro",))
            base = {"slug": "mi-kernel", "title": "t", "script": "print(1)", "dataset_sources": ["nicolasbuttaro/edgelab-data-catalog"]}
            ok = process_bridge_request({"request_id": "p2", "action": "push_kernel", "params": base}, cli, Path(tmp), policy=pol)
            self.assertEqual(ok["status"], "OK")
            self.assertFalse(cli.pushed[-1]["enable_internet"])
            self.assertEqual(cli.pushed[-1]["slug"], "nicolasbuttaro/mi-kernel")
            ok2 = process_bridge_request({"request_id": "p2b", "action": "push_kernel", "params": {**base, "slug": "nicolasbuttaro/mi-kernel"}}, cli, Path(tmp), policy=pol)
            self.assertEqual(ok2["status"], "OK")
            self.assertEqual(cli.pushed[-1]["slug"], "nicolasbuttaro/mi-kernel")
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "p2c", "action": "push_kernel", "params": {**base, "slug": "otro/mi-kernel"}}, cli, Path(tmp), policy=pol)
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "p3", "action": "push_kernel", "params": {**base, "enable_internet": True}}, cli, Path(tmp), policy=pol)
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "p4", "action": "push_kernel", "params": {**base, "dataset_sources": ["otro/dataset"]}}, cli, Path(tmp), policy=pol)
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "p5", "action": "push_kernel", "params": {**base, "slug": "../x"}}, cli, Path(tmp), policy=pol)

    def test_descarga_de_parquet_bloqueada_por_defecto_y_texto_chico_permitido(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp)
            cli = _FakeKaggleClient()
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "d1", "action": "download_file_chunked",
                                        "params": {"dataset": "o/s", "file": "data/ES_ticks.parquet"}}, cli, bridge_dir=bdir)
            self.assertFalse((bdir / "artifacts").exists())
            ok = process_bridge_request({"request_id": "d2", "action": "download_file_chunked",
                                        "params": {"dataset": "o/s", "file": "README_AGENTES.md"}}, cli, bridge_dir=bdir)
            self.assertEqual(ok["status"], "OK")

    def test_tope_de_tamano_en_descargas_de_texto(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "d3", "action": "download_file_chunked",
                                        "params": {"dataset": "o/s", "file": "grande.json"}}, _FakeKaggleClient(), Path(tmp),
                                       policy=BridgePolicy(max_download_bytes=1000))

    def test_la_descarga_intermedia_no_pasa_por_la_carpeta_de_drive(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / "EdgeLab_Bridge"
            bdir.mkdir()
            seen = []

            class Cli(_FakeKaggleClient):
                def download_dataset_file_to_path(self, dataset, file_name, dest_path):
                    seen.append(Path(dest_path).resolve())
                    return super().download_dataset_file_to_path(dataset, file_name, dest_path)

            process_bridge_request({"request_id": "d4", "action": "download_file_chunked",
                                    "params": {"dataset": "o/s", "file": "a.json"}}, Cli(), bdir)
            self.assertTrue(seen)
            for p in seen:
                self.assertNotIn(bdir.resolve(), p.parents)
            self.assertFalse((bdir / "_tmp_downloads").exists())

    def test_manifiesto_con_ruta_fuera_de_la_carpeta_no_se_sigue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chunks").mkdir()
            secreto = root / "secreto.bin"
            secreto.write_bytes(b"SECRETO")
            m = {"schema": "edgelab_drive_chunk_manifest_v1", "total_size_bytes": 7, "sha256": hashlib.sha256(b"SECRETO").hexdigest(),
                 "chunks": [{"filename": "../secreto.bin", "size_bytes": 7, "sha256": hashlib.sha256(b"SECRETO").hexdigest()}]}
            (root / "chunks" / "x.manifest.json").write_text(json.dumps(m), encoding="utf-8")
            with self.assertRaises(KaggleBridgeError):
                reassemble_drive_chunks(root / "chunks" / "x.manifest.json", root / "salida.bin")


def _git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    def g(*a):
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
    g("init", "-q")
    (repo / "a.txt").write_text("uno\n", encoding="utf-8")
    g("add", "."); g("commit", "-q", "-m", "c1")
    (repo / "a.txt").write_text("uno\ndos\n", encoding="utf-8")
    (repo / "datos.parquet").write_bytes(b"PAR1" * 100)
    (repo / "data").mkdir()
    (repo / "data" / "x.csv").write_text("1,2\n", encoding="utf-8")
    g("add", "."); g("commit", "-q", "-m", "c2")
    return repo


class TestAccionesAmpliadas(unittest.TestCase):
    def test_git_head_info_solo_lectura(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _git_repo(Path(tmp))
            pol = BridgePolicy(repos={"main": str(repo)})
            r = process_bridge_request({"request_id": "g1", "action": "git_head_info", "params": {"repo": "main"}}, _FakeKaggleClient(), Path(tmp) / "b", policy=pol)
            self.assertEqual(len(r["result"]["log"]), 2)
            self.assertFalse(r["result"]["dirty"])
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "g2", "action": "git_head_info", "params": {"repo": "otro"}}, _FakeKaggleClient(), Path(tmp), policy=pol)

    def test_export_delta_excluye_parquet_y_data_y_rechaza_refs_con_opciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _git_repo(Path(tmp))
            pol = BridgePolicy(repos={"main": str(repo)})
            bdir = Path(tmp) / "b"
            r = process_bridge_request({"request_id": "g3", "action": "git_export_delta", "params": {"repo": "main", "base": "HEAD~1", "head": "HEAD"}}, _FakeKaggleClient(), bdir, policy=pol)
            patch = (bdir / "artifacts" / "g3" / "delta.patch").read_text(encoding="utf-8")
            self.assertIn("a.txt", patch)
            self.assertNotIn("datos.parquet", patch)
            self.assertNotIn("data/x.csv", patch)
            self.assertEqual(r["result"]["commits"], 1)
            for bad in ("--output=/tmp/x", "-n1", "a..b", "HEAD;rm"):
                with self.assertRaises(KaggleBridgeError):
                    process_bridge_request({"request_id": "g4", "action": "git_export_delta", "params": {"repo": "main", "base": bad, "head": "HEAD"}}, _FakeKaggleClient(), bdir, policy=pol)

    def test_check_patch_no_aplica_ni_ejecuta(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _git_repo(Path(tmp))
            bdir = Path(tmp) / "b"
            (bdir / "patches_for_review").mkdir(parents=True)
            ok = subprocess.run(["git", "-C", str(repo), "diff", "HEAD~1", "HEAD", "--", "a.txt"], capture_output=True).stdout
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "HEAD~1"], check=True, capture_output=True)
            (bdir / "patches_for_review" / "bueno.patch").write_bytes(ok)
            (bdir / "patches_for_review" / "malo.patch").write_text("esto no es un parche", encoding="utf-8")
            self.assertTrue(check_patch(repo, bdir, "bueno.patch")["applies_cleanly"])
            self.assertFalse(check_patch(repo, bdir, "malo.patch")["applies_cleanly"])
            self.assertEqual((repo / "a.txt").read_text(encoding="utf-8"), "uno\n")        # no se aplicó
            for bad in ("../x.patch", "a/b.patch", "x.sh", ".patch"):
                with self.assertRaises(KaggleBridgeError):
                    check_patch(repo, bdir, bad)

    def test_descarga_de_datos_encendida_solo_de_owners_declarados(self):
        with tempfile.TemporaryDirectory() as tmp:
            pol = BridgePolicy(allow_data_download=True, allowed_source_owners=("nicolasbuttaro",))
            ok = process_bridge_request({"request_id": "d9", "action": "download_file_chunked",
                                         "params": {"dataset": "nicolasbuttaro/x", "file": "data/ES_ticks.parquet"}}, _FakeKaggleClient(), Path(tmp), policy=pol)
            self.assertEqual(ok["status"], "OK")
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "d10", "action": "download_file_chunked",
                                        "params": {"dataset": "extrano/x", "file": "a.parquet"}}, _FakeKaggleClient(), Path(tmp), policy=pol)


    def test_get_kernel_output_y_kernel_sources_restringidos_a_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = _FakeKaggleClient()
            pol = BridgePolicy(allow_push=True, allowed_source_owners=("nicolasbuttaro",))
            ok = process_bridge_request(
                {"request_id": "ko1", "action": "get_kernel_output", "params": {"owner": "nicolasbuttaro", "slug": "edgelab-test"}},
                cli, Path(tmp), policy=pol,
            )
            self.assertEqual(ok["result"]["log"], "OK_LOG")
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request(
                    {"request_id": "ko2", "action": "get_kernel_output", "params": {"owner": "otro", "slug": "edgelab-test"}},
                    cli, Path(tmp), policy=pol,
                )
            ok_push = process_bridge_request(
                {"request_id": "kp1", "action": "push_kernel", "params": {
                    "slug": "edgelab-s2", "title": "t", "script": "print(1)",
                    "dataset_sources": ["nicolasbuttaro/edgelab-liquid-ticks-20261014"],
                    "kernel_sources": ["nicolasbuttaro/edgelab-s1"],
                }},
                cli, Path(tmp), policy=pol,
            )
            self.assertEqual(ok_push["status"], "OK")
            self.assertEqual(cli.pushed[-1]["kernel_sources"], ["nicolasbuttaro/edgelab-s1"])
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request(
                    {"request_id": "kp2", "action": "push_kernel", "params": {
                        "slug": "edgelab-s2", "title": "t", "script": "print(1)",
                        "kernel_sources": ["otro/edgelab-s1"],
                    }},
                    cli, Path(tmp), policy=pol,
                )


    def test_get_kernel_output_sin_owners_declarados_no_lee_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KaggleBridgeError):
                process_bridge_request({"request_id": "ko3", "action": "get_kernel_output", "params": {"owner": "nicolasbuttaro", "slug": "edgelab-test"}},
                                       _FakeKaggleClient(), Path(tmp), policy=BridgePolicy())

if __name__ == "__main__":
    unittest.main()


def test_archivar_reemplaza_un_pedido_ya_procesado_con_el_mismo_nombre(tmp_path):
    """El bucle --watch se cortaba en Windows cuando processed/ ya tenía un pedido con el mismo nombre."""
    import tools.kaggle_drive_bridge as M
    (tmp_path / "processed").mkdir(); viejo = tmp_path / "processed" / "x.json"; viejo.write_text("viejo")
    nuevo = tmp_path / "x.json"; nuevo.write_text("nuevo")
    M._archivar(nuevo, viejo)
    assert viejo.read_text() == "nuevo" and not nuevo.exists()


def test_holdout_sellado_no_se_expone_por_el_puente(tmp_path):
    """HOLDOUT-A4 (2026-10-28): ni lectura, ni descarga, ni adjuntar como fuente de un kernel, ni salidas de kernels de holdout."""
    from tools.kaggle_drive_bridge import BridgePolicy, KaggleBridgeError, process_bridge_request
    pol = BridgePolicy(allow_push=True, allow_data_download=True, allowed_source_owners=("nicolasbuttaro",))
    sellado = "nicolasbuttaro/edgelab-holdout-sellado"
    pedidos = [("inspect_dataset", {"dataset": sellado}), ("list_dataset_files", {"dataset": sellado}),
               ("read_dataset_file_preview", {"dataset": sellado, "file": "SELLADO.txt"}),
               ("download_file_chunked", {"dataset": sellado, "file": "ES_12-26_ticks.parquet"}),
               ("push_kernel", {"slug": "mi-kernel", "title": "x", "script": "print(1)", "dataset_sources": [sellado]}),
               ("get_kernel_output", {"owner": "nicolasbuttaro", "slug": "embudo-u1-es-grilla-holdout-conteo-20261001"})]

    class _C:                                                   # cliente que revienta si alguien lo LLAMA: la guarda tiene que cortar antes
        def __getattr__(self, k):
            def _no(*a, **kw):
                raise AssertionError(f"el cliente no debe llamarse ({k})")
            return _no

    for i, (accion, params) in enumerate(pedidos):
        try:
            process_bridge_request(dict(request_id=f"h{i}", action=accion, params=params), _C(), tmp_path, policy=pol)
        except KaggleBridgeError:
            continue
        raise AssertionError(f"{accion} sobre el holdout sellado no fue bloqueado")



def test_git_apply_and_push_aplica_commitea_y_bloquea_archivos_protegidos_l0(tmp_path):
    """Verifica que git_apply_and_push aplique parches limpios, haga commit+push a un remoto bare, y bloquee tocar L0 o el puente."""
    import hashlib, json, subprocess
    from tools.kaggle_drive_bridge import BridgePolicy, KaggleBridgeError, process_bridge_request

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "foundation/f0b-compatibility-probe"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "edge@edgelab.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "EdgeLab"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)

    # Crear archivo protegido L0 y archivo normal
    (repo / "edgelab").mkdir()
    f_l0 = repo / "edgelab" / "holdout.py"
    f_l0.write_text("HOLDOUT_PRIMERA_SESION_INT = 20261001\n", encoding="utf-8")
    sha_l0 = hashlib.sha256(f_l0.read_bytes()).hexdigest()

    (repo / "config" / "autopilot").mkdir(parents=True)
    (repo / "config" / "autopilot" / "protected.json").write_text(
        json.dumps({"files": {"edgelab/holdout.py": sha_l0}}), encoding="utf-8"
    )
    (repo / "docs").mkdir()
    (repo / "docs" / "NOTA.md").write_text("linea 1\n", encoding="utf-8")

    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-q", "origin", "foundation/f0b-compatibility-probe"], check=True)

    bridge_dir = tmp_path / "bridge"
    patches_dir = bridge_dir / "patches_for_review"
    patches_dir.mkdir(parents=True)

    # 1. Parche válido sobre docs/NOTA.md
    valid_patch = (
        "diff --git a/docs/NOTA.md b/docs/NOTA.md\n"
        "--- a/docs/NOTA.md\n"
        "+++ b/docs/NOTA.md\n"
        "@@ -1 +1,2 @@\n"
        " linea 1\n"
        "+linea 2\n"
    )
    (patches_dir / "ok.patch").write_text(valid_patch, encoding="utf-8")

    class _NoClient:
        pass

    # Sin allow_git_push debe fallar
    pol_off = BridgePolicy(allow_git_push=False, repos={"edgelab": str(repo)})
    try:
        process_bridge_request(
            {"request_id": "g1", "action": "git_apply_and_push", "params": {"repo": "edgelab", "patch": "ok.patch", "message": "test"}},
            _NoClient(),
            bridge_dir,
            policy=pol_off,
        )
        raise AssertionError("debio bloquearse con allow_git_push=False")
    except KaggleBridgeError:
        pass

    # Con allow_git_push=True aplica, commitea y pushea al remoto bare
    pol_on = BridgePolicy(allow_git_push=True, repos={"edgelab": str(repo)})
    resp = process_bridge_request(
        {"request_id": "g2", "action": "git_apply_and_push", "params": {"repo": "edgelab", "patch": "ok.patch", "message": "feat: nota"}},
        _NoClient(),
        bridge_dir,
        policy=pol_on,
    )
    assert resp["status"] == "OK"
    assert resp["result"]["pushed"] is True
    assert resp["result"]["files_changed"] == 1
    remote_head = subprocess.check_output(["git", "-C", str(remote), "rev-parse", "refs/heads/foundation/f0b-compatibility-probe"], text=True).strip()
    assert remote_head == resp["result"]["head"]

    # 2. Parche que intenta tocar archivo protegido L0 (edgelab/holdout.py) debe ser rechazado
    bad_patch = (
        "diff --git a/edgelab/holdout.py b/edgelab/holdout.py\n"
        "--- a/edgelab/holdout.py\n"
        "+++ b/edgelab/holdout.py\n"
        "@@ -1 +1 @@\n"
        "-HOLDOUT_PRIMERA_SESION_INT = 20261001\n"
        "+HOLDOUT_PRIMERA_SESION_INT = 20261101\n"
    )
    (patches_dir / "bad_l0.patch").write_text(bad_patch, encoding="utf-8")
    try:
        process_bridge_request(
            {"request_id": "g3", "action": "git_apply_and_push", "params": {"repo": "edgelab", "patch": "bad_l0.patch", "message": "hack"}},
            _NoClient(),
            bridge_dir,
            policy=pol_on,
        )
        raise AssertionError("debio bloquearse por guarda L0")
    except KaggleBridgeError:
        pass
