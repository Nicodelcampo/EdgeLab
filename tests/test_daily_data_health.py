import datetime as dt
import importlib.util
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "tools" / "daily_data_health.py"
spec = importlib.util.spec_from_file_location("daily_data_health", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _l2(root, contract, dates):
    d = root / contract / "l2_depth"
    d.mkdir(parents=True)
    for x in dates:
        (d / f"{x}.parquet").write_bytes(b"x")


def test_detecta_huecos_de_dias_habiles_y_captura_cortada(tmp_path):
    _l2(tmp_path, "ES_09-26", ["20261005", "20261006", "20261008"])        # falta el miercoles 07
    st = m.l2_status(tmp_path, dt.date(2026, 10, 14))["ES_09-26"]
    assert st["missing_weekdays_in_range"] == ["2026-10-07"]
    assert st["business_days_since_last"] == 4


def test_respaldo_detecta_faltantes_y_diferencias(tmp_path):
    src, dst = tmp_path / "s", tmp_path / "d"
    (src / "a").mkdir(parents=True)
    (dst / "a").mkdir(parents=True)
    (src / "a" / "1.bin").write_bytes(b"12")
    (src / "a" / "2.bin").write_bytes(b"1")
    (src / "3.bin").write_bytes(b"1")
    (dst / "a" / "1.bin").write_bytes(b"12")
    (dst / "a" / "2.bin").write_bytes(b"123")
    r = m.backup_status(src, dst)
    assert r["checked"] == 3 and r["missing_in_backup"] == 1 and r["size_differs"] == 1


def test_main_sale_1_cuando_la_captura_se_corto(tmp_path, monkeypatch):
    _l2(tmp_path / "l2", "NQ_12-26", ["20260901"])
    monkeypatch.setattr(sys, "argv", ["x", "--l2-root", str(tmp_path / "l2"), "--out", str(tmp_path / "o.json"), "--today", "2026-10-14"])
    assert m.main() == 1
    _l2(tmp_path / "l2b", "NQ_12-26", ["20261013"])
    monkeypatch.setattr(sys, "argv", ["x", "--l2-root", str(tmp_path / "l2b"), "--out", str(tmp_path / "o2.json"), "--today", "2026-10-14"])
    assert m.main() == 0


def test_solo_alerta_el_contrato_mas_reciente_de_cada_producto():
    l2 = {"ES_09-26": {"last": "2026-09-18", "business_days_since_last": 18}, "ES_12-26": {"last": "2026-09-27", "business_days_since_last": 13},
          "GC_12-26": {"last": "2026-10-13", "business_days_since_last": 1}}
    assert m.stale_alerts(l2, 3) == ["L2 ES_12-26: 13 dias habiles sin dato nuevo (ultimo 2026-09-27)"]
