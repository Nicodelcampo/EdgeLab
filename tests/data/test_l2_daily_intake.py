"""Orquestador de intake diario (tools/l2_daily_intake.py): CSV crudo -> parquet validado ->
chequeo de frontera con el dia anterior -> log de custodia -> borrado opcional del CSV.

No prueba nada de descarga (eso queda fuera, ver docstring del modulo). Prueba que el
encadenamiento de piezas ya construidas (convert_l2_session, classify_gap) se comporta
fail-closed en cada punto, y que el CSV NUNCA se borra salvo pedido explicito y exito
completo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.l2_daily_intake import run_intake

TICK = 0.1

CSV_OK = "\n".join([
    "L2;0;20260901010000;0;0;0;;4300.0;5",
    "L2;1;20260901010000;0;0;0;;4299.9;3",
    "L1;0;20260901010000;0;4300.0;5",
    "L1;2;20260901010000;1;4300.0;1",
]) + "\n"

CSV_SIN_L2 = "L1;0;20260901010000;0;4300.0;5\nL1;2;20260901010000;1;4300.0;1\n"

CSV_PRECIO_MALO = "\n".join([
    "L2;0;20260902010000;0;0;0;;4300.0;5",
    "L1;0;20260902010000;0;4300.037;5",       # no es multiplo de tick 0.1 -- esto tiene que abortar
]) + "\n"


@pytest.fixture
def base(tmp_path):
    return tmp_path / "canonical"


def test_intake_ok_no_borra_el_csv_por_default(tmp_path, base):
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_OK, encoding="utf-8")

    record = run_intake(csv_path=csv, base=base, instrument="GC", contract="GC 08-26",
                        tick_size=TICK, downloader_id="manual")

    assert record["conversion_status"] == "PASS"
    assert record["l1_present"] is True and record["l2_present"] is True
    assert record["csv_deleted"] is False
    assert csv.exists()                     # el CSV sigue ahi: default es NO borrar
    assert record["parquet_l2_sha256"] and record["parquet_l1_sha256"]
    assert record["boundary_status"] == "NO_PREVIOUS_SESSION"


def test_delete_csv_after_validation_borra_solo_si_todo_paso(tmp_path, base):
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_OK, encoding="utf-8")

    record = run_intake(csv_path=csv, base=base, instrument="GC", contract="GC 08-26",
                        tick_size=TICK, downloader_id="manual", delete_csv_after_validation=True)

    assert record["conversion_status"] == "PASS"
    assert record["csv_deleted"] is True
    assert not csv.exists()


def test_csv_sin_l2_no_convierte_y_preserva_el_csv(tmp_path, base):
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_SIN_L2, encoding="utf-8")

    record = run_intake(csv_path=csv, base=base, instrument="GC", contract="GC 08-26",
                        tick_size=TICK, downloader_id="manual", delete_csv_after_validation=True)

    assert record["conversion_status"] == "ABSTAIN_MISSING_L1_OR_L2"
    assert record["l2_present"] is False
    assert csv.exists()                     # nunca se borra si no convirtio
    assert not (base / "l2_depth" / "20260901.parquet").exists()


def test_precio_fuera_de_grilla_aborta_y_preserva_el_csv(tmp_path, base):
    csv = tmp_path / "20260902.csv"
    csv.write_text(CSV_PRECIO_MALO, encoding="utf-8")

    record = run_intake(csv_path=csv, base=base, instrument="GC", contract="GC 08-26",
                        tick_size=TICK, downloader_id="manual", delete_csv_after_validation=True)

    assert record["conversion_status"].startswith("ABORTED_PRICE_ROUNDTRIP")
    assert csv.exists()
    assert not (base / "l1_quotes" / "20260902.parquet").exists()


def test_segunda_sesion_calcula_frontera_contra_la_primera(tmp_path, base):
    csv1 = tmp_path / "20260901.csv"
    csv1.write_text(CSV_OK, encoding="utf-8")
    run_intake(csv_path=csv1, base=base, instrument="GC", contract="GC 08-26",
              tick_size=TICK, downloader_id="manual")

    csv2_content = "\n".join([
        "L2;0;20260902010000;0;0;0;;4300.0;5",
        "L1;2;20260902010000;1;4300.0;1",
    ]) + "\n"
    csv2 = tmp_path / "20260902.csv"
    csv2.write_text(csv2_content, encoding="utf-8")
    record2 = run_intake(csv_path=csv2, base=base, instrument="GC", contract="GC 08-26",
                         tick_size=TICK, downloader_id="manual")

    assert record2["conversion_status"] == "PASS"
    assert record2["boundary_status"]["left_session"] == "20260901"
    assert "gap_classification" in record2["boundary_status"]


def test_nrd_path_opcional_agrega_su_hash_al_registro(tmp_path, base):
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_OK, encoding="utf-8")
    nrd = tmp_path / "20260901.nrd"
    nrd.write_bytes(b"contenido binario simulado del .nrd")

    record = run_intake(csv_path=csv, base=base, instrument="GC", contract="GC 08-26",
                        tick_size=TICK, downloader_id="manual", nrd_path=nrd)

    assert record["nrd_bytes"] == nrd.stat().st_size
    assert record["nrd_sha256"] is not None


def test_main_escribe_el_log_como_jsonl_append_only(tmp_path):
    from tools.l2_daily_intake import main
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_OK, encoding="utf-8")
    base = tmp_path / "canonical"
    log = tmp_path / "intake.jsonl"

    rc = main(["--csv", str(csv), "--base", str(base), "--instrument", "GC", "--contract", "GC 08-26",
              "--tick-size", str(TICK), "--downloader-id", "manual", "--log", str(log)])
    assert rc == 0

    csv2_content = "\n".join([
        "L2;0;20260902010000;0;0;0;;4300.0;5",
        "L1;2;20260902010000;1;4300.0;1",
    ]) + "\n"
    csv2 = tmp_path / "20260902.csv"
    csv2.write_text(csv2_content, encoding="utf-8")
    rc2 = main(["--csv", str(csv2), "--base", str(base), "--instrument", "GC", "--contract", "GC 08-26",
               "--tick-size", str(TICK), "--downloader-id", "manual", "--log", str(log)])
    assert rc2 == 0

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2                  # las dos corridas se acumulan, no se pisan
    records = [json.loads(l) for l in lines]
    assert records[0]["session_date"] == "20260901"
    assert records[1]["session_date"] == "20260902"


def test_main_devuelve_codigo_distinto_de_cero_si_no_paso(tmp_path):
    from tools.l2_daily_intake import main
    csv = tmp_path / "20260901.csv"
    csv.write_text(CSV_SIN_L2, encoding="utf-8")
    rc = main(["--csv", str(csv), "--base", str(tmp_path / "canonical"), "--instrument", "GC",
              "--contract", "GC 08-26", "--tick-size", str(TICK), "--downloader-id", "manual",
              "--log", str(tmp_path / "intake.jsonl")])
    assert rc != 0
