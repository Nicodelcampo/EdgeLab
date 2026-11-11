"""tools/uso_agente.py y la duración por llamada de RoleRunner (2026-11-10)."""
import importlib.util, json, sqlite3
from pathlib import Path

from edgelab.autopilot.roles import RoleRunner

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("uso_agente", ROOT / "tools/uso_agente.py"); U = importlib.util.module_from_spec(spec); spec.loader.exec_module(U)
DIA_TS = 1794355200.0                                                     # 2026-11-11 00:00 UTC


class Reloj:
    def __init__(self, t): self.t = t
    def __call__(self): return self.t


def _runner(tmp_path, reloj, respuestas):
    def cli(prompt, *, model, schema, system, timeout=600):
        reloj.t += 30                                                     # cada llamada tarda 30 s
        return respuestas.pop(0)
    return RoleRunner(tmp_path / "llm_calls.sqlite", cli=cli, clock=reloj)


OK = dict(structured_output={"resumen_sala": "x", "aporte_al_referente": "y"}, usage={"input_tokens": 100, "output_tokens": 10}, total_cost_usd=0.01)


def test_rolerunner_guarda_duracion_y_migra_libro_viejo(tmp_path):
    db = sqlite3.connect(tmp_path / "llm_calls.sqlite")                   # libro de antes del 2026-11-10, sin dur_s
    db.execute("CREATE TABLE llm_calls (id INTEGER PRIMARY KEY, ts REAL, day TEXT, role TEXT, model TEXT, in_sha TEXT, out_sha TEXT, status TEXT, "
               "tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, output TEXT)"); db.commit(); db.close()
    r = Reloj(DIA_TS); rr = _runner(tmp_path, r, [dict(OK)])
    assert rr.call("cronista", {"hechos": {"a": 1}})["status"] == "OK"
    fila = sqlite3.connect(tmp_path / "llm_calls.sqlite").execute("SELECT status, dur_s FROM llm_calls").fetchall()
    assert fila == [("OK", 30.0)]


def test_informe_llm_huecos_y_reintentos(tmp_path):
    r = Reloj(DIA_TS); malo = dict(is_error=True, result="boom")
    rr = _runner(tmp_path, r, [dict(OK), malo, dict(OK)])
    rr.call("cronista", {"hechos": {"a": 1}})                             # termina en +30
    r.t += 120                                                            # 120 s sin llamadas
    rr.call("cronista", {"hechos": {"a": 2}})                             # intento 1 inválido (+30), intento 2 OK (+30)
    x = U.llm(tmp_path / "llm_calls.sqlite", "2026-11-11")
    assert len(x) == 1 and x[0]["llamadas"] == 3 and x[0]["ok"] == 2 and x[0]["errores"] == 1 and x[0]["reintentos"] == 1
    assert x[0]["tokens_in"] == 200 and abs(x[0]["costo_usd"] - 0.02) < 1e-9 and x[0]["dur_s"] == 90
    h = U.huecos(tmp_path / "llm_calls.sqlite", "2026-11-11", cola=[(DIA_TS + 30, DIA_TS + 90)])
    assert h["n_huecos"] == 2 and h["hueco_total_s"] == 120 and h["hueco_con_cola_total_s"] == 60 and not h["aproximado"]


def test_kaggle_produccion_y_markdown(tmp_path):
    (tmp_path / "embudo/C1").mkdir(parents=True)
    (tmp_path / "embudo/C1/estado.json").write_text(json.dumps(dict(historial=[dict(ts=DIA_TS + 10, etapa="DESC", fin=True), dict(ts=DIA_TS + 20, etapa="OOS", falla="error")])))
    lan = tmp_path / "account_launches.jsonl"
    lan.write_text("\n".join(json.dumps(dict(ts=DIA_TS + i, slug=s)) for i, s in enumerate(["nicolasbuttaro/a", "nicobuttaro/b", "nicolasbuttaro/c"])) + "\n")
    (tmp_path / "propuestas.jsonl").write_text(json.dumps(dict(ts=DIA_TS, status="OK")) + "\n")
    (tmp_path / "promociones.jsonl").write_text(json.dumps(dict(ts=DIA_TS, decision="RECHAZADA_REVISOR", revisor=dict(decision="KILL"))) + "\n")
    rep = U.informe(tmp_path, "2026-11-11", lan)
    assert rep["kaggle"]["lanzados_por_cuenta"] == {"nicobuttaro": 1, "nicolasbuttaro": 2}
    assert rep["kaggle"]["fallas_embudo"] == 1 and rep["kaggle"]["etapas_terminadas"] == 1
    assert rep["produccion"]["propuestas"] == 1 and rep["produccion"]["revisor"] == {"KILL": 1}
    md = U.markdown(rep); assert md.startswith("# Uso del agente del Debian — 2026-11-11") and "Estado: VIGENTE" in md
    assert "3 kernels" in U.resumen_sala(rep)


def test_cola_superpuesta_no_se_cuenta_dos_veces():
    assert U._intersec(0, 100, [(0, 60), (10, 50), (40, 80)]) == 80
    assert U._intersec(0, 100, []) == 0
