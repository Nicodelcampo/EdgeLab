"""Arreglos de la auditoría del embudo del 2026-10-24 (docs/research/auditoria_kaggle_20261024/) que no cubre
tests/research/test_embudo_auditoria_debian.py (PR #130): registro obligatorio, A3, un solo conductor, slug, libro de ventanas."""
import json

import pytest

from edgelab.research import embudo as EM, embudo_runners as R, holdout_ventanas as HV

SPEC = dict(cid="AUD-1", familia="AUD", experimento="tests.research.exp_u1_sin_be", sensor="DK:X", ejecucion="Y", desc=[20250801, 20250930],
            justificacion_economica="j", como_podria_refutarse="r", embudo=True, preflight_dinamico=False)


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


class Runner:
    """Runner de juguete: estado y resultado configurables por etapa."""
    def __init__(self, estado="complete", res=None, falla_traer=False): self.est, self.res, self.falla, self.lanzadas = estado, res or {}, falla_traer, []
    def lanzar(self, spec, etapa, params, periodo): self.lanzadas.append((etapa, params)); return f"h{len(self.lanzadas)}"
    def estado(self, h): return self.est
    def traer(self, h):
        if self.falla: raise FileNotFoundError("RESULTADO.json")
        return self.res


def _embudo(tmp_path, run, registro="reg"):
    return EM.Embudo(tmp_path / "e", dict(kaggle=run, local=run), registro=Reg() if registro == "reg" else registro, libro=None,
                     ahora=lambda: 1_792_900_000, log=lambda s: None, ventanas=tmp_path / "v.jsonl")






def test_sin_registro_no_se_lanza_una_etapa_con_desenlaces(tmp_path):
    run = Runner(); em = _embudo(tmp_path, run, registro=None)
    st = em.estado(dict(SPEC, n_celdas_por_canal=10)); st.update(etapa="DESC", fase="PENDIENTE", spec=dict(SPEC, n_celdas_por_canal=10),
                                                         reglas={k: EM._cfg(SPEC, k) for k in EM.DEFECTOS}); em._guardar(SPEC, st)
    with pytest.raises(RuntimeError, match="sin registro"): em.avanzar(dict(SPEC, n_celdas_por_canal=10))
    assert run.lanzadas == []








def test_campana_a3():
    a3 = lambda d: [e for e in EM.problemas_campana(d) if "HOLDOUT-A3" in e]
    assert a3(SPEC) == []
    assert a3(dict(SPEC, sensor="DK:USATECHIDXUSD", ejecucion="NQ", desc=[20250805, 20260930]))
    assert a3(dict(SPEC, sensor="ES", ejecucion=None, desc=[20250805, 20260601]))
    assert a3(dict(SPEC, sensor="NQ", desc=[20250805, 20260331])) == []


def test_campanas_del_repo_pasan_el_chequeo_de_campana_y_declaran_conductor():
    from pathlib import Path
    for f in sorted((Path(__file__).resolve().parents[2] / "config/autopilot/grillas/campanas").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("embudo"): continue
        assert d.get("conductor") in EM.CONDUCTORES, f.name
        if d.get("activa", True): assert EM.problemas_campana(d) == [], f.name


def test_un_solo_conductor(tmp_path):
    c = tmp_path / "c"; c.mkdir()
    (c / "a.json").write_text(json.dumps(dict(SPEC, cid="A", conductor="local"))); (c / "b.json").write_text(json.dumps(dict(SPEC, cid="B")))
    run = Runner(); out = EM.avanzar_todas(c, _embudo(tmp_path, run), conductor="debian")
    assert {o["cid"] for o in out if "omitida" in o} == {"A", "B"} and run.lanzadas == []


def test_slug_sin_guion_bajo(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path, dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado")
    spec = dict(cid="X_3", experimento="tests.research.exp_u1_sin_be", sensor="DK:USATECHIDXUSD", ejecucion="NQ")
    a = k.argumentos(spec, "HOLDOUT_CONTEO", dict(celdas=[[0]], acta=dict(cid="X_3")), [20261023, 20261101])
    slug = a[a.index("--slug") + 1]
    assert "_" not in slug and slug == "nicolasbuttaro/embudo-x-3-holdout-conteo-20261023"


def test_libro_de_ventanas_del_estado_se_une_al_del_repo(tmp_path):
    repo, est = tmp_path / "repo.jsonl", tmp_path / "estado.jsonl"
    repo.write_text(json.dumps(dict(tipo="consumida", familia="A", desde=20261001, hasta=20261022, relacionadas=[])) + "\n")
    HV.registrar_apertura("B", "c1", 20261023, 150, est)
    assert HV.sincronizar(repo, est) == 1 and HV.sincronizar(repo, est) == 0
    assert {r["tipo"] for r in HV.leer(est)} == {"consumida", "apertura"} and HV.problemas("A", 20261010, "c9", est)
