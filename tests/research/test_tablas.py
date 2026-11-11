"""Tablas de eventos: contrato, preflight (atrapa el look-ahead), exploración con nulo, congelado con hash y confirmación una vez."""
import json
import types

import numpy as np
import pandas as pd
import pytest

from edgelab.research import analizar_tabla as AT, grilla_generica as GG, plantilla_tabla as P, sintetico, tablas as TB


def _tabla(seed, dias=60, fuente="NQ", desde=20250801):
    T = TB.generar(P, GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=seed), tick=0.25))
    T["ses"] = T.ses + desde; T["fuente"] = fuente
    return T


def test_contrato_y_conteo():
    assert TB.contrato(P) == []
    malo = types.SimpleNamespace(NOMBRE="a_b", EJECUCIONES=[("MERCADO", 0.5, 0.5, 0.5, 0)], FILTROS={"x": ("c", "~", 1)})
    e = TB.contrato(malo)
    assert any("NOMBRE" in x for x in e) and any("eventos" in x for x in e) and any("FILTROS" in x for x in e) and any("parcial" in x for x in e)
    assert TB.conteo(P) == 2 * 4 * 2
    assert TB.fuente_costo(P, "USATECHIDXUSD") == "NQ" and TB.fuente_costo(P, "NQ") == "NQ"


def test_preflight_pasa_la_plantilla_y_atrapa_el_lookahead(monkeypatch):
    assert TB.preflight(P, dias=40, kernel=False) == []
    trampa = types.ModuleType("trampa"); trampa.__dict__.update({k: getattr(P, k) for k in ("NOMBRE", "EJECUCIONES", "DEFINICIONES", "FILTROS")})

    def eventos(ctx):                                                       # mira la vela siguiente: no puede pasar
        E = P.eventos(ctx); c = np.asarray(ctx["c"]); k = E.k.to_numpy()
        return E.assign(vel=c[np.minimum(k + 1, len(c) - 1)])
    trampa.eventos = eventos
    assert any("causalidad" in x for x in TB.preflight(trampa, dias=40, kernel=False))


def test_explorar_congelar_y_confirmar(tmp_path):
    T = pd.concat([_tabla(3), _tabla(4, desde=20260401, fuente="USATECHIDXUSD")], ignore_index=True)
    res = AT.explorar(P, T, top=5)
    c = res["cortes"]["todos"]
    assert c["celdas"] > 0 and "t_max_p95" in c["nulo_busqueda"] and c["control"]
    assert {"NQ/DESC", "USATECHIDXUSD/REP"} <= set(res["cortes"])
    assert "Nulo de la búsqueda" in AT.informe_exploracion(res)

    class Reg:
        def __init__(self): self.n = []
        def ensure(self, *a): self.n.append(a); return True
    reg = Reg(); hip = [dict(defn="def_m3", ejec="M_sl0.5_tp1.0_N", filtro="todos")]
    p = AT.congelar(P, hip, "PLANTILLA", tmp_path, [dict(fuente="NQ", desde=20230101, hasta=20231231)], reg)
    assert reg.n and reg.n[0][2] == 1
    with pytest.raises(ValueError): AT.congelar(P, [dict(defn="def_m3", ejec="NO_EXISTE")], "PLANTILLA", tmp_path, [], reg)
    r = AT.confirmar(P, _tabla(9, desde=20230101), p)
    assert r["hipotesis"][0]["veredicto"] in ("CONFIRMADA", "EN_CONTRA", "NO_CONCLUYENTE", "SIN_POTENCIA", "EN_CONTRA_SIN_POTENCIA")
    d = json.loads(p.read_text()); d["hipotesis"][0]["filtro"] = "rapido"; p.write_text(json.dumps(d))
    with pytest.raises(ValueError): AT.verificar_congeladas(p)             # tocar las congeladas rompe el hash


def test_fisher():
    assert AT.fisher([0.5]) == pytest.approx(0.5) and AT.fisher([0.05, 0.05]) == pytest.approx(0.01748, abs=1e-4)


def test_cli_slug_y_ventanas():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import tablas as CLI
    s = CLI.slug("edgelab.research.plantilla_tabla", "DK:USATECHIDXUSD", 20230103, 20250731, "nicolasbuttaro")
    assert "_" not in s and len(s) <= 49 and s.startswith("nicolasbuttaro/t-plantilla-usatech-")
    assert CLI._ventanas(["DK:USATECHIDXUSD:20230103:20250731", "NQ:20250805:20260331"]) == [("DK:USATECHIDXUSD", 20230103, 20250731), ("NQ", 20250805, 20260331)]


def test_cli_curva(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import tablas as CLI
    (tmp_path / "tablas").mkdir()
    for seed, desde in ((3, 20250801), (4, 20260401)):
        T = _tabla(seed, desde=desde); n = f"TABLA_PLANTILLA_NQ_{desde}_x"
        T.drop(columns=["fuente"]).to_csv(tmp_path / "tablas" / f"{n}.csv.gz", index=False)
        (tmp_path / "tablas" / f"{n}.json").write_text(json.dumps(dict(fuente="NQ")))
    monkeypatch.setattr(CLI, "carpeta", lambda m: tmp_path)
    CLI.curva("edgelab.research.plantilla_tabla", "def_m3", "M_sl0.5_tp1.0_N")
    res = json.loads(next(tmp_path.glob("CURVA_*.json")).read_text())
    assert set(res) == {"IS", "OOS"} and res["IS"]["n"] > 0 and next(tmp_path.glob("CURVA_*.svg")).read_text().startswith("<svg")
