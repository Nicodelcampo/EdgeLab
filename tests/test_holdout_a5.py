"""HOLDOUT-A5 (2026-11-17): partición intercalada por meses, determinista, 7/2/3 por año, con embargo de un día hábil a cada lado de cada
mes de holdout y TERMINAL desde la frontera A4 (que no cambia)."""
import datetime as dt

from edgelab import holdout as H


def test_reparto_7_2_3_y_determinista():
    for a in range(2006, 2027):
        m = H.a5_meses(a)
        assert sorted(m) == list(range(1, 13))
        assert [list(m.values()).count(k) for k in ("DESC", "REP", "HOLDOUT")] == [7, 2, 3]
        assert m == H.a5_meses(a)


def test_terminal_y_embargo():
    assert H.a5_bloque(H.HOLDOUT_PRIMERA_SESION_INT) == "TERMINAL" and H.a5_bloque(20261231) == "TERMINAL"
    for a in range(2008, 2026):
        for mes, b in H.a5_meses(a).items():
            if b != "HOLDOUT": continue
            d0 = dt.date(a, mes, 1)
            while d0.weekday() >= 5: d0 += dt.timedelta(days=1)
            antes = d0 - dt.timedelta(days=1)
            while antes.weekday() >= 5: antes -= dt.timedelta(days=1)
            assert H.a5_bloque(int(d0.strftime("%Y%m%d"))) == "HOLDOUT"
            if H.a5_meses(antes.year)[antes.month] != "HOLDOUT":
                assert H.a5_bloque(int(antes.strftime("%Y%m%d"))) == "EMBARGO"


def test_la_frontera_a4_no_cambia():
    assert H.HOLDOUT_PRIMERA_SESION_INT == 20261001 and H.HOLDOUT_APERTURA_UTC_ISO == "2026-09-30T22:00:00"
