"""Puente con la sala: archivos, sin red."""
import json
from edgelab.autopilot.sala import reportar, aplicar_comandos

TICK = dict(event="tick", launched=None, proposed=("IDM-3", "score 0.4"), closed=[("SLOT-1", False)], blocked=[("X", ["holdout"])])
STATUS = dict(mode="propose", paused=False, alpha_wealth=0.0475, running=[], send_uncertain=[])


class Runner:
    def __init__(self, status="OK"): self.status, self.payloads = status, []
    def call(self, role, payload):
        self.payloads.append((role, payload))
        return {"status": self.status, "output": {"resumen_sala": "texto del cronista", "aporte_al_referente": "-"}}


def test_report_template_keeps_numbers_from_ledger(tmp_path):
    row = reportar(tmp_path, TICK, STATUS)
    assert row["fuente"] == "plantilla" and "IDM-3" in row["texto"] and "0.0475" in row["texto"]
    assert row["hechos"]["cerradas"] == [["SLOT-1", False]] or row["hechos"]["cerradas"] == [("SLOT-1", False)]
    assert json.loads((tmp_path / "sala_outbox.jsonl").read_text().splitlines()[0])["hechos"]["alfa"] == 0.0475

def test_report_uses_cronista_but_numbers_travel_apart(tmp_path):
    r = Runner()
    row = reportar(tmp_path, TICK, STATUS, runner=r)
    assert row["fuente"] == "cronista" and row["hechos"]["propuesta"][0] == "IDM-3"
    assert r.payloads[0][0] == "cronista" and "hechos" in r.payloads[0][1]

def test_report_falls_back_when_role_unavailable(tmp_path):
    assert reportar(tmp_path, TICK, STATUS, runner=Runner("RATE_LIMITED"))["fuente"] == "plantilla"

def test_commands_authorized_only_and_offset(tmp_path):
    ks = tmp_path / "PAUSE"
    inbox = tmp_path / "sala_inbox.jsonl"
    inbox.write_text("\n".join(json.dumps(x) for x in [
        {"autor": "gonzasib", "texto": "pausa"}, {"autor": "intruso", "texto": "reanudar"},
        {"autor": "nicobutta897", "texto": "aprobar IDM-3"}, {"autor": "gonzasib", "texto": "borrar todo"}]) + "\n")
    out = aplicar_comandos(tmp_path, ks, ["gonzasib", "nicobutta897"], lambda: STATUS)
    assert ks.exists()                                                    # pausa aplicada; el intruso no reanudó
    assert ("no_autorizado", "intruso") in out and ("desconocido", "borrar") in out
    ap = json.loads((tmp_path / "sala_aprobaciones.jsonl").read_text())
    assert ap["id"] == "idm-3" and ap["efecto"].startswith("ninguno")
    assert aplicar_comandos(tmp_path, ks, ["gonzasib"], lambda: STATUS) == []      # ya leídos
    with inbox.open("a") as f: f.write(json.dumps({"autor": "gonzasib", "texto": "reanudar"}) + "\n")
    aplicar_comandos(tmp_path, ks, ["gonzasib"], lambda: STATUS)
    assert not ks.exists()
