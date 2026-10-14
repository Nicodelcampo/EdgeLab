"""Pruebas del filtro de lista blanca del snapshot de código (sin tocar git ni datos)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from export_head_snapshot import allowed  # noqa: E402


class ListaBlanca(unittest.TestCase):
    def test_entra_codigo_y_docs(self):
        for n in ("tools/avzp2_pnl_sim.py", "tests/bridge/test_x.py", "docs/research/ACTA.md", "nt8/aVolZonePOI2.cs", "pyproject.toml", "CLAUDE.md",
                  "requirements/core.txt", "docs/chico.json"):
            self.assertTrue(allowed(n, 5_000)[0], n)

    def test_no_entran_datos_ni_binarios(self):
        for n in ("data/x.py", "oracles/a.json", "runs/r.json", "archive/viejo.py", "diag/x.json", "viewer/nt8_bridge/bundles/ES_03-26_ESPEJO.json",
                  "x/y.parquet", "x/e.csv", "x/e.jsonl", "pyarrow-20.0.0-cp313.whl", "viewer/index.html", "viewer/a.js", "x/log.txt", "x/f.svg"):
            self.assertFalse(allowed(n, 5_000)[0], n)

    def test_tope_de_tamano(self):
        self.assertFalse(allowed("tools/enorme.py", 1_500_000)[0])
        self.assertFalse(allowed("docs/grande.json", 400_000)[0])
        self.assertTrue(allowed("docs/mediano.json", 250_000)[0])

    def test_nombres_sensibles_nunca(self):
        for n in (".env", "cfg/credentials.py", "x/access_token", ".kaggle/kaggle.json", "k/id_rsa", "a/secret_keys.md", "a/b.pem"):
            self.assertFalse(allowed(n, 100)[0], n)

    def test_carpetas_excluidas_a_cualquier_profundidad(self):
        self.assertFalse(allowed("a/b/data/c.py", 100)[0])
        self.assertFalse(allowed("a/archive/c.md", 100)[0])


if __name__ == "__main__":
    unittest.main()
