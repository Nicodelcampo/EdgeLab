"""Mirada exploratoria: todo se escribe antes de correr, consume la ventana, anula la apertura sin mirar y mueve la confirmación."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "tools"))
import holdout_exploratorio as HE  # noqa: E402
from edgelab.research import holdout_ventanas as HV  # noqa: E402


class Fake:
    def lanzar(self, spec, etapa, params, periodo): self.p = (etapa, params, periodo); return "h"
    def traer(self, h): return dict(operaciones=dict(neto=[5.0, -2.0, 3.0, 1.0, -1.0, 4.0], ses=[1, 1, 2, 3, 3, 4]))


def test_flujo_completo(tmp_path):
    raiz = tmp_path / "embudo"; d = raiz / "C"; d.mkdir(parents=True); lib = tmp_path / "v.jsonl"
    st = dict(etapa="CONTEO", fase="PENDIENTE", historial=[], regla=dict(celda=[1], tope=["mult", 2.0]), cortes={},
              spec=dict(familia="F", experimento="e", sensor="DK:X", holdout=dict(desde=20261001)), reglas=dict(holdout=dict(desde=20261001)),
              acta=dict(n_fijo=150))
    (d / "estado.json").write_text(json.dumps(st)); (d / "ACTA_HOLDOUT.json").write_text("{}"); (d / "MEDIDO.md").write_text("")
    HV.registrar_apertura("F", "C", 20261001, 150, lib)
    HE.preparar(raiz, "C", 20261025, ventanas=lib)
    assert not HV.aperturas_vigentes("F", lib) and HV.ultima_consumida("F", lib) == 20261025
    run = Fake(); out = HE.correr(raiz, "C", {}, runner=run)
    assert run.p[0] == "REP" and run.p[1]["tope"] == ["mult", 2.0] and run.p[2] == [20261001, 20261025]
    assert out["n"] == 6 and out["ganadoras"] == 4 and "ic90" in out
    nuevo = HE.cerrar(raiz, "C", campanas=tmp_path)
    st2 = json.loads((d / "estado.json").read_text())
    assert nuevo == 20261026 and st2["etapa"] == "ACTA" and st2["spec"]["holdout"]["desde"] == 20261026 and "acta" not in st2
    assert HV.problemas("F", 20261026, "C", lib) == [] and HV.problemas("F", 20261020, "C", lib)   # la confirmación, sólo después
