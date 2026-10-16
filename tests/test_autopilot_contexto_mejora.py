"""Paquete de contexto, lentes, novedad, diagnóstico y registro de mejoras. Sin red."""
from edgelab.autopilot.contexto import LENTES, PRIORIDADES, armar_paquete, elegir_lente, novedad, proponer
from edgelab.autopilot.mejora import RegistroMejoras, diagnosticar


def test_lente_rota_y_prefiere_la_menos_usada():
    h = [{"lente": k, "hit": False} for k in LENTES if k != "artefacto"]
    assert elegir_lente(h) == "artefacto"
    assert elegir_lente([]) in LENTES

def test_paquete_siempre_lleva_prioridades_y_lente_aunque_recorte():
    p = armar_paquete(tablero={"alfa": 0.04}, vacios=["v" * 500] * 20, fichas=["f" * 500] * 40, retiradas=["BigTrap2 imán"], lente="replica_debil", max_chars=4000)
    assert p["prioridades"] == PRIORIDADES and p["lente"]["nombre"] == "replica_debil"
    assert "BigTrap2 imán" in p["prohibido"]["familias_retiradas"] and len(p["fichas"]) < 40

def test_novedad_descarta_repetidas():
    ok, _, _ = novedad({"familia": "racimos de zonas en NQ", "mecanismo": "compresión tras acumulación"}, ["ORB 5 minutos ES"])
    assert ok
    rep, parecida, sim = novedad({"familia": "racimos zonas compresión", "mecanismo": "acumulación racimos"}, ["racimos zonas compresión acumulación"])
    assert not rep and sim >= 0.6

class R:
    def __init__(self, out): self.out = out
    def call(self, role, payload): return {"status": "OK", "output": self.out}

def test_proponer_devuelve_borrador_no_autorizado_o_repetida():
    p = armar_paquete(tablero={}, vacios=[], fichas=[], retiradas=[], lente="artefacto")
    nueva = proponer(R({"familia": "rebote bid ask en ZB", "mecanismo": "precio medio", "prediccion": "p", "refutacion": "r", "parametros_libres": [], "refs": []}), p, ["racimos"])
    assert nueva["status"] == "BORRADOR_NO_AUTORIZADO" and "promote" in nueva["siguiente"]
    rep = proponer(R({"familia": "racimos", "mecanismo": "racimos", "prediccion": "p", "refutacion": "r", "parametros_libres": [], "refs": []}), p, ["racimos racimos"])
    assert rep["status"] == "DESCARTADA_POR_REPETIDA"

def test_diagnostico_separa_automatico_de_humano():
    d = diagnosticar([{"event": "tick", "blocked": [("X", ["no se pudo traer el resultado: timeout"])]}, {"event": "STOP_protected_changed"}],
                     {"send_uncertain": ["R1"], "heartbeat_age_s": 7200, "alpha_wealth": 0.03})
    por = {x["sintoma"]: x["automatica"] for x in d}
    assert por == {"STOP_protected_changed": False, "fetch_failed": True, "send_uncertain": False, "heartbeat_viejo": False}

def test_mejoras_globales_o_sobre_reglas_son_solo_humano(tmp_path):
    reg = RegistroMejoras(tmp_path / "mejoras.jsonl")
    assert reg.proponer("eficiencia", "batch de outcomes", "3x en benchmark")["estado"] == "PROPUESTA"
    assert reg.proponer("modulo", "relajar guarda", "x", archivos=["edgelab/autopilot/guard.py"])["estado"] == "SOLO_HUMANO"
    assert reg.proponer("global", "cambiar FDR", "x")["estado"] == "SOLO_HUMANO"
    assert len(reg.abiertas()) == 3


def test_lecciones_k32_en_prioridades_y_catalogo():
    import json, pathlib
    assert any("replay tick a tick" in p and "réplica" in p for p in PRIORIDADES)
    cat = json.loads((pathlib.Path(__file__).resolve().parents[1] / "config/autopilot/herramientas.json").read_text(encoding="utf-8"))
    assert {"replay_causal_fills_pasivos", "aprendizaje_continuo_con_embargo"} <= {t["id"] for t in cat["tecnicas"]}
