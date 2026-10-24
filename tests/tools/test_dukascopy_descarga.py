import datetime as dt, importlib.util, io, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("dk_t", ROOT / "tools/dukascopy_descarga.py"); DK = importlib.util.module_from_spec(spec); spec.loader.exec_module(DK)


class R:
    def __init__(self, b): self.b = b
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.b


def test_reintenta_ante_limite_de_tasa_y_404_es_hora_vacia():
    seq = [urllib.error.HTTPError("u", 429, "x", {}, io.BytesIO()), ConnectionResetError(), urllib.error.HTTPError("u", 503, "x", {}, io.BytesIO()), R(b"ok")]
    pausas, uas = [], []
    def abrir(req, timeout):
        uas.append(req.get_header("User-agent")); x = seq.pop(0)
        if isinstance(x, Exception): raise x
        return x
    t = dt.datetime(2026, 8, 3, 14, tzinfo=dt.timezone.utc)
    assert DK.bajar_hora("USATECHIDXUSD", t, abrir=abrir, dormir=pausas.append) == b"ok"
    assert [p for p in pausas if p >= 5][:3] == [5, 10, 20] and all("edgelab" not in u for u in uas)
    def a404(req, timeout): raise urllib.error.HTTPError("u", 404, "x", {}, io.BytesIO())
    assert DK.bajar_hora("USATECHIDXUSD", t, abrir=a404, dormir=lambda s: None) == b""
