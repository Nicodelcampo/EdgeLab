"""Tests sintéticos del auditor de captura: transporte != procedencia."""
from __future__ import annotations

from edgelab.data.capture_tsv import (
    SCHEMA_V2, SCHEMA_V21, V2_COLUMNS, V21_COLUMNS, audit_capture_tsv,
)


def write_capture(path, *, schema=SCHEMA_V21, n=3, callback=None, capture=None,
                  drops=0, writer_errors=0, sentinel=False, mode="live",
                  provider="CQG", account="Simulation",
                  timezone="America/Chicago", source_ticks=None,
                  monotonic=None, omit_summary=False):
    columns = V21_COLUMNS if schema == SCHEMA_V21 else V2_COLUMNS
    callback = callback or list(range(n))
    capture = capture or list(range(n))
    source_ticks = source_ticks or [638000000000000000 + i for i in range(n)]
    monotonic = monotonic or [1000 + i for i in range(n)]
    lines = [
        "# schema=" + schema,
        "# capture_id=cap-1",
        "# process_instance_id=pid-1",
        "# stopwatch_frequency=10000000",
        "# source_sequence=NOT_EXPOSED_BY_THIS_NT8_CALLBACK",
        "\t".join(columns),
    ]
    for i in range(n):
        row = {c: "" for c in columns}
        row.update(capture_id="cap-1", process_instance_id="pid-1",
                   callback_seq=str(callback[i]), capture_seq=str(capture[i]),
                   source_time_ticks=str(source_ticks[i]),
                   source_time_kind="Unspecified",
                   source_time_iso="2026-08-03T17:00:00.0000000",
                   capture_utc_ticks=str(638000000010000000 + i),
                   capture_utc_iso="2026-08-03T20:00:00.0000000Z",
                   monotonic_ticks=str(monotonic[i]),
                   stopwatch_frequency="10000000", nt8_state="Realtime",
                   event_kind="Last", instrument="6E", contract="6E 09-26",
                   price="1.15", volume="1", bid="1.1499", ask="1.1501",
                   aggressor="unclassified", aggressor_provenance="quote_rule",
                   timestamp_provenance="nt8_event_time",
                   quote_provenance="nt8_snapshot", capture_mode_label=mode)
        if schema == SCHEMA_V21:
            row.update(provider_label=provider,
                       account_environment_label=account,
                       source_timezone_label=timezone)
        if sentinel and i == 0:
            row["bid"] = "-1.7976931348623157E+308"
        lines.append("\t".join(row[c] for c in columns))
    if not omit_summary:
        lines.append("# summary callbacks_seen=%d,rows_written=%d,dropped_at_queue=%d,writer_errors=%d" %
                     (n, n, drops, writer_errors))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_v21_limpio_separa_simulation_de_cqg(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p)
    report = audit_capture_tsv(p)
    assert report.transport_ok
    assert report.schema_ok
    assert report.verdict == "TRANSPORT_PASS_WITH_SCHEMA_DEBT"
    assert any("upstream" in w for w in report.warnings)


def test_drops_y_writer_errors_fallan_transporte(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p, drops=2, writer_errors=1)
    report = audit_capture_tsv(p)
    assert not report.transport_ok
    assert report.verdict == "TRANSPORT_FAIL"


def test_secuencias_deben_ser_exactas_y_coincidir(tmp_path):
    p = tmp_path / "capture.tsv"
    write_capture(p, callback=[0, 1, 3], capture=[0, 1, 2])
    report = audit_capture_tsv(p)
    assert not report.transport_ok
    assert any("callback_seq" in e for e in report.transport_errors)


def test_monotonic_estricto_es_gate_de_transporte(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p, monotonic=[10, 10, 11])
    assert not audit_capture_tsv(p).transport_ok


def test_source_time_puede_retroceder_sin_inventar_perdida(tmp_path):
    p = tmp_path / "capture.tsv"
    base = 638000000000000000
    write_capture(p, source_ticks=[base, base + 10, base - 20])
    report = audit_capture_tsv(p)
    assert report.transport_ok
    assert report.source_time_regressions == 1
    assert report.max_source_time_regression_ns == 3000
    assert any("source_time" in w for w in report.warnings)


def test_double_min_value_es_deuda_de_schema_no_drop(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p, sentinel=True)
    report = audit_capture_tsv(p)
    assert report.transport_ok
    assert not report.schema_ok
    assert report.sentinel_values == 1


def test_v2_legado_conserva_transport_pass_pero_declara_deuda(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p, schema=SCHEMA_V2)
    report = audit_capture_tsv(p)
    assert report.transport_ok
    assert report.schema_ok
    assert any("v2 legado" in w for w in report.warnings)


def test_v21_rechaza_placeholders_de_procedencia(tmp_path):
    p = tmp_path / "capture.tsv"
    write_capture(p, provider="DECLARAR_provider", timezone="Unspecified")
    report = audit_capture_tsv(p)
    assert not report.schema_ok
    assert any("provider_label" in e for e in report.schema_errors)
    assert any("source_timezone_label" in e for e in report.schema_errors)


def test_capture_mode_placeholder_es_deuda(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p, mode="DECLARAR_live")
    assert not audit_capture_tsv(p).schema_ok


def test_reporte_json_incluye_veredicto(tmp_path):
    p = tmp_path / "capture.tsv"; write_capture(p)
    text = audit_capture_tsv(p).to_json()
    assert '"transport_ok": true' in text
    assert '"verdict": "TRANSPORT_PASS_WITH_SCHEMA_DEBT"' in text
