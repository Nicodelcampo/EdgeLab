import json, os
from edgelab.autopilot import pedidos
from edgelab.autopilot.sala import aplicar_comandos


def test_pedido_no_se_duplica_y_se_cierra_desde_la_sala(tmp_path):
    a = pedidos.pedir(tmp_path, "datos", "ticks MNQ 12-26 desde 2026-09-28", "la captura L2 está cortada", bloquea="AVZVOL-3")
    b = pedidos.pedir(tmp_path, "datos", "ticks MNQ 12-26 desde 2026-09-28", "otra vez")
    assert a["id"] == b["id"] and len(pedidos.abiertos(tmp_path)) == 1
    assert "PEDIDO" in (tmp_path / "sala_outbox.jsonl").read_text() and (tmp_path / "sala_outbox.jsonl").read_text().count("PEDIDO") == 1
    ib = tmp_path / "sala_inbox.jsonl"; ib.write_text(json.dumps({"autor": "nico", "texto": f"resuelto {a['id']} subido a Kaggle"}) + "\n"); os.chmod(ib, 0o644)
    aplicar_comandos(tmp_path, tmp_path / "PAUSE_SALA", ["nico"], lambda: {})
    assert pedidos.abiertos(tmp_path) == [] and pedidos.estado(tmp_path)[a["id"]]["resuelto_por"] == "nico"


def test_bloqueo_por_datos_del_ciclo_se_convierte_en_pedido(tmp_path):
    rep = {"blocked": [("slot-9", ["falta ES 2026-09-02: sin fuente en Kaggle"]), ("x", ["holdout: llega a 2026-10-01"])]}
    out = pedidos.desde_ciclo(tmp_path, rep)
    assert len(out) == 1 and out[0]["tipo"] == "datos" and "slot-9" in out[0]["que"]
