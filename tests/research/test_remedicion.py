"""Re-medición: el registro de cambios está completo, el criterio alcanza a quien debe y el documento generado está al día."""
import sys
from pathlib import Path

from edgelab.research import remedicion as RM

ROOT = Path(__file__).resolve().parents[2]


def test_cambios_bien_formados():
    C = RM.cargar(); assert C
    for c in C:
        assert {"id", "fecha", "que_cambio", "por_que_distinto", "como_remedir"} <= set(c) and (c.get("afecta") or c.get("patron_codigo")), c["id"]
    assert len({c["id"] for c in C}) == len(C)


def test_criterio_de_alcance():
    c = dict(id="X", afecta=dict(registrada_antes="2026-11-02", nombre_regex="ZONA", excluir_desenlace_regex=r"-R:"))
    assert RM.alcanza(c, dict(familia="ZONAS_A", registrada="2026-10-20", desenlaces=["ZA: SIN_CANDIDATAS"]))
    assert not RM.alcanza(c, dict(familia="ZONAS_A", registrada="2026-11-05", desenlaces=[]))           # posterior al cambio
    assert not RM.alcanza(c, dict(familia="ORB", registrada="2026-10-20", desenlaces=[]))               # no es de zonas
    assert not RM.alcanza(c, dict(familia="ZONAS_B", registrada="2026-10-20", desenlaces=["ZB-R: PISTAS_VIVAS"]))   # ya re-medida
    assert RM.alcanza(c, dict(familia="ZONAS_C", registrada="", desenlaces=[]))                         # sin fecha = vieja
    cand = RM.candidatas([dict(familia="ZONAS_A", registrada="2026-10-20", desenlaces=["ZA: SIN_CANDIDATAS"], factores=[], carpetas=[])], [c])
    assert cand[0]["cambios"] == ["X"] and cand[0]["prioridad"] == 3.0


def test_patron_de_codigo_viejo(tmp_path):
    d = tmp_path / "edgelab/research"; d.mkdir(parents=True)
    (d / "viejo.py").write_text("t = np.searchsorted(np.nanquantile(v, [1/3, 2/3]), x)\n")
    out = RM.patrones_codigo([dict(id="CM-ESTRATOS", patron_codigo=r"searchsorted\([^)]*(nan)?quantile")], root=tmp_path, carpetas=("edgelab/research",))
    assert out and out[0]["archivo"].endswith("viejo.py")


def test_documento_generado_al_dia():
    sys.path.insert(0, str(ROOT / "tools")); import remediciones
    assert (ROOT / "docs/research/REMEDICIONES_CANDIDATAS.md").read_text(encoding="utf-8") == remediciones.markdown(), \
        "regenerar: python tools/remediciones.py --write"
