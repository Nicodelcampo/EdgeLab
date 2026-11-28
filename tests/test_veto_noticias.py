import numpy as np
import pandas as pd

from edgelab import veto_noticias as VN

MIN = 60_000_000_000


def ns(s):
    return pd.Timestamp(s, tz="UTC").value


def _V():
    # dos noticias: CPI 2024-03-12 12:30Z (±2) y FOMC 2024-03-20 18:00Z (±5)
    return pd.DataFrame({"inicio_ns": [ns("2024-03-12 12:28"), ns("2024-03-20 17:55")],
                         "fin_ns": [ns("2024-03-12 12:32"), ns("2024-03-20 18:05")], "eventos": ["CPI", "FOMC_DECISION"]})


def _m1():
    idx = pd.date_range("2024-03-12 12:00", "2024-03-12 13:00", freq="1min", tz="UTC")
    return pd.Series(np.arange(len(idx), dtype=float) + 100.0, index=idx)


def test_ventanas_del_calendario_real_fomc_mas_ancho():
    V = VN.ventanas()
    cpi = ns("2024-03-12 12:30")
    i = np.searchsorted(V.inicio_ns.to_numpy(), cpi, side="right") - 1
    assert V.inicio_ns.iloc[i] == cpi - 2 * MIN and V.fin_ns.iloc[i] == cpi + 2 * MIN
    fomc = ns("2024-03-20 18:00")
    i = np.searchsorted(V.inicio_ns.to_numpy(), fomc, side="right") - 1
    assert V.inicio_ns.iloc[i] == fomc - 5 * MIN
    assert V.inicio_ns.min() < ns("2008-02-01")                                    # cubre 2008


def test_en_ventana_bordes_cerrados():
    V = _V()
    assert VN.en_ventana([ns("2024-03-12 12:28"), ns("2024-03-12 12:32"), ns("2024-03-12 12:33")], V).tolist() == [True, True, False]


def test_aplicar_veto_anula_cierra_y_deja():
    ops = pd.DataFrame({"entrada_ns": [ns("2024-03-12 12:29"), ns("2024-03-12 12:10"), ns("2024-03-12 12:40")],
                        "salida_ns": [ns("2024-03-12 12:50"), ns("2024-03-12 12:45"), ns("2024-03-12 12:50")],
                        "lado": [1, -1, 1], "precio_entrada": [110.0, 120.0, 140.0], "precio_salida": [150.0, 100.0, 150.0]})
    o = VN.aplicar_veto(ops, _m1(), _V())
    assert o.veto.tolist() == ["anulada", "cerrada_por_noticia", "sin_cambio"]
    assert o.salida_ns.iloc[1] == ns("2024-03-12 12:28") and o.precio_salida.iloc[1] == 128.0   # apertura de la vela 12:28
    assert o.pts.tolist() == [0.0, -1 * (128.0 - 120.0), 10.0]
    assert VN.resumen(o) == {"n": 3, "anuladas": 1, "cerradas_por_noticia": 1, "pct_afectadas": 66.67}


def test_paridad_con_nt8_csharp(tmp_path):
    """El NewsVetoCalendar de EdgeLabFundedSyncCore.cs veta exactamente los mismos minutos que veto_noticias."""
    import glob, subprocess
    import pytest
    from pathlib import Path
    cscs = sorted(glob.glob(r"C:\Windows\Microsoft.NET\Framework64\v4*\csc.exe"))
    if not cscs:
        pytest.skip("csc.exe no disponible")
    root = Path(__file__).resolve().parents[1]
    src = (root / "nt8" / "strategies" / "EdgeLabFundedSyncCore.cs").read_text(encoding="ascii")
    cls = src[src.index("    public sealed class NewsVetoCalendar"):src.index("    public sealed class PortfolioCoordinator")]
    prog = ("using System;using System.IO;using System.Collections.Generic;using System.Globalization;namespace T { " + cls +
            " class P { static void Main(string[] a){ var c=new NewsVetoCalendar(a[0],2,2,5,5); var o=new StreamWriter(a[2]);"
            " foreach(var l in File.ReadAllLines(a[1])){ var t=DateTime.ParseExact(l,\"yyyy-MM-ddTHH:mm:ss\",CultureInfo.InvariantCulture,"
            "DateTimeStyles.AdjustToUniversal|DateTimeStyles.AssumeUniversal); o.WriteLine(c.BlocksAt(t)?1:0);} o.Close(); } } }")
    (tmp_path / "t.cs").write_text(prog)
    subprocess.run([cscs[-1], "/nologo", f"/out:{tmp_path / 't.exe'}", str(tmp_path / "t.cs")], check=True, capture_output=True)
    from edgelab import noticias
    cal = noticias.cargar()
    base = cal[cal.impacto == "tier1"].ts_utc.dt.tz_convert(None).sample(300, random_state=3)
    ts = [b + pd.Timedelta(minutes=k) for b in base for k in (-6, -5, -3, -2, -1, 0, 1, 2, 3, 5, 6)]
    (tmp_path / "ts.txt").write_text("\n".join(t.strftime("%Y-%m-%dT%H:%M:%S") for t in ts))
    subprocess.run([str(tmp_path / "t.exe"), str(root / "config" / "noticias" / "calendario_usd_tier1.csv"),
                    str(tmp_path / "ts.txt"), str(tmp_path / "cs.txt")], check=True)
    cs = [int(x) for x in (tmp_path / "cs.txt").read_text().split()]
    py = VN.en_ventana(np.array([pd.Timestamp(t, tz="UTC").value for t in ts]), VN.ventanas()).astype(int).tolist()
    assert cs == py and 0 < sum(py) < len(py)
