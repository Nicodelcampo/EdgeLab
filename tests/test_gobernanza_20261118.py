"""Guardas K41–K44 (2026-11-18): errores de la sesión del 18-nov convertidos en chequeos que la cadena estándar no deja pasar.
Índice: docs/research/LEER_ANTES_DE_CADA_CORRIDA.md (v3) y docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md §E6."""
import json, py_compile, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _py_versionados():
    r = subprocess.run(["git", "ls-files", "tools/*.py", "edgelab/*.py", "edgelab/**/*.py"], cwd=ROOT, capture_output=True, text=True)
    return [ROOT / x for x in r.stdout.split() if x.endswith(".py") and (ROOT / x).exists()]


def test_todo_el_codigo_compila(tmp_path):
    """K44: `orb_confirmacion_o1.py` llegó a commitearse con un paréntesis de más (no tenía test). Ningún script versionado puede no
    compilar, tenga tests o no."""
    malos = []
    for f in _py_versionados():
        try: py_compile.compile(str(f), cfile=str(tmp_path / "x.pyc"), doraise=True)
        except py_compile.PyCompileError as e: malos.append(f"{f.relative_to(ROOT)}: {str(e)[:120]}")
    assert not malos, malos


def test_apertura_exige_potencia_al_alfa_reservado(monkeypatch):
    """K42: potencia declarada a α 0,05 con un nivel LORD++ reservado de 0,0036."""
    from edgelab.research import holdout_ventanas as HV
    from edgelab.funnel import libro_lord

    class Falso:
        estado = dict(reservas={"FAM::R1": dict(familia="FAM", reserva_id="R1", t=2, nivel=0.0036, resuelta=False)})
    monkeypatch.setattr(libro_lord, "LibroLord", lambda *a, **k: Falso())
    with pytest.raises(ValueError, match="K42"):
        HV._exigir_alfa_reservado("FAM", dict(tipo="fijo", alfa=0.05, potencia=0.9))
    HV._exigir_alfa_reservado("FAM", dict(tipo="fijo", alfa=0.0036, potencia=0.8))       # al nivel: pasa
    HV._exigir_alfa_reservado("OTRA", dict(tipo="fijo", alfa=0.05, potencia=0.9))        # otra familia sin reserva: pasa


def test_datos_ruta_exige_copia_verificada(tmp_path, monkeypatch):
    """Acceso a datos: una carpeta bajada a mano no alcanza; hace falta la PROCEDENCIA y que cada archivo tenga su tamaño."""
    import datos
    monkeypatch.setattr(datos, "BASE", tmp_path)
    with pytest.raises(SystemExit, match="traer M1NT8"):
        datos.ruta("M1NT8")
    d = tmp_path / "m1nt8"; d.mkdir(); (d / "NQ.parquet").write_bytes(b"abc")
    (d / "PROCEDENCIA.json").write_text(json.dumps(dict(archivos={"NQ.parquet": dict(bytes=3)})))
    assert datos.ruta("M1NT8") == str(d)
    (d / "NQ.parquet").write_bytes(b"abcd")                                               # alterada o a medio bajar
    with pytest.raises(SystemExit, match="alterada"):
        datos.ruta("M1NT8")


def test_tablas_no_interpreta_tablas_de_codigo_viejo(tmp_path, monkeypatch):
    """K41: `tablas.py traer` salteaba tablas ya bajadas sin revisar su código, y explorar/congelar/confirmar las leía igual."""
    import pandas as pd
    import tablas
    monkeypatch.setattr(tablas, "carpeta", lambda m: tmp_path)
    (tmp_path / "tablas").mkdir()
    pd.DataFrame(dict(ses=[1], x=[1.0])).to_csv(tmp_path / "tablas/TABLA_X_NQ_1_2.csv.gz", index=False)
    (tmp_path / "tablas/TABLA_X_NQ_1_2.json").write_text(json.dumps(dict(fuente="NQ", modulos={"tools/tablas.py": "0" * 64})))
    with pytest.raises(SystemExit, match="NO VIGENTE"):
        tablas._tablas("x", "tablas")
    (tmp_path / "tablas/TABLA_X_NQ_1_2.json").write_text(json.dumps(dict(fuente="NQ", modulos={})))
    assert len(tablas._tablas("x", "tablas")) == 1


def test_validacion_de_fuente_por_criterio_unico():
    """K43: el veredicto de una validación de fuente sale de `a5.calibrar_por_sesion`, no de una tabla a mano."""
    from edgelab.research import a5 as A5
    t = {s: 1.0 + (s % 3) for s in range(40)}; m = {s: v + 0.1 for s, v in t.items()}
    assert A5.calibrar_por_sesion(t, m)["calibra"]
    assert not A5.calibrar_por_sesion(t, {s: -v for s, v in t.items()})["calibra"]
    assert "validacion" in (ROOT / "tools/papel_m1.py").read_text(encoding="utf-8")


def test_a5_evalua_contraste_con_control_que_no_es_definicion():
    """Error del 18-nov: `a5.evaluar` perdía el contraste «definición − control» cuando el control no estaba entre las definiciones
    probadas (ESCALONADAS-M1 y su placebo)."""
    import numpy as np, pandas as pd
    from edgelab.research import a5 as A5
    rng = np.random.default_rng(0); n = 400
    T = pd.DataFrame(dict(ses=20100104 + np.arange(n) // 2, bloque="DESC", d=np.arange(n) % 2 == 0, pl=np.arange(n) % 2 == 1,
                          r_e=rng.normal(0.1, 1, n), k_e=1.0))
    res = A5.evaluar(T, "DESC", ["d"], ["e"], 0.0, control={"d": "pl"})
    assert "d|e" in res and "d-pl|e" in res and "pl|e" not in res


def test_ops_conserva_columnas_de_identidad():
    """K45: `a5_campana.correr` descartaba trig/base/conf y el análisis pareado del filtro de picos no podía emparejar gatillos."""
    import pandas as pd
    import a5_campana as AC
    O = pd.DataFrame(dict(k=[1], ses=[2], t=[3.0], inst=["NQ"], bloque=["DESC"], lado=[1], rg=[1.0], trig=["LUX:1:1"], base=["LUX"],
                          conf=["INM"], X__INM=[True], r_e=[0.1], k_e=[1.0], basura=[0.0]))
    c = AC.columnas_ops(O, dict(definiciones=["X__INM"], ejecuciones=["e"]))
    assert {"trig", "base", "conf", "X__INM", "r_e", "k_e"} <= set(c) and "basura" not in c and len(c) == len(set(c))


def test_ningun_factor_vivo_se_apoya_en_evidencia_descartada():
    """K46: F-ASIA-NQ-NOCHE-MOVIDA siguió como PISTA_VIVA apoyada en un largo DESCARTADO hasta que se revisó a mano. Una pista o
    palanca no puede citar como evidencia un documento cuyo Estado sea DESCARTADA."""
    import re
    malos = []
    for l in (ROOT / "docs/research/FACTORES.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(l)
        if e["estado"] not in ("PISTA_VIVA", "PALANCA_DE_DISENO"): continue
        for ev in e.get("evidencia", []):
            f = ROOT / ev
            if f.suffix == ".md" and f.exists() and re.search(r"^Estado:\s*DESCARTAD", f.read_text(encoding="utf-8")[:2000], re.M):
                malos.append((e["id"], ev))
    assert not malos, f"factor vivo con evidencia DESCARTADA (bajarlo o citar la versión vigente): {malos}"


def test_validacion_de_papel_usa_la_agregacion_de_la_ficha():
    """K47: la validación de papel M1 promediaba sólo las celdas que operan y la ficha suma y divide por el número de celdas; ASIA
    «duplicaba» a los ticks sin que el motor tuviera nada que ver. La serie de la ficha sale EXACTA de `canasta_por_sesion` sobre las
    operaciones en ticks, y `papel_m1.validacion` usa esa función."""
    from edgelab.cartera.papel import canasta_por_sesion
    F = {x["id"]: x for x in json.loads((ROOT / "config/cartera/altas.json").read_text(encoding="utf-8"))["fichas"]}["ASIA-NQ-CANASTA"]
    od = F["ops_desarrollo"]; od = json.loads(od) if isinstance(od, str) else od
    ficha = {}
    for s, v in od:
        if 20250801 <= int(s) <= 20260929: ficha[int(s)] = ficha.get(int(s), 0.0) + float(v)
    O = json.loads((ROOT / "docs/research/papel_m1_20261115/resultados/FUTNQ__ASIA-NQ-CANASTA_20250801_20260929.json").read_text())["operaciones"]
    mio = dict(canasta_por_sesion(zip(O["ses"], O["neto"]), len(F["regla"]["celdas"])))
    comunes = set(ficha) & set(mio)
    assert len(comunes) > 200 and max(abs(ficha[s] - mio[s]) for s in comunes) < 1e-3
    assert "canasta_por_sesion" in (ROOT / "tools/papel_m1.py").read_text(encoding="utf-8")


def test_variable_de_regimen_que_se_conoce_despues_de_la_entrada_no_se_usa():
    """K48: `noche` (18:00→09:00 de la misma sesión) se conoce a las 09:00; ASIA entra de noche y la variable miraba el futuro."""
    from edgelab.research import papel_regimen as PR
    asia = json.loads((ROOT / "docs/research/papel_m1_20261115/resultados/FUTNQ__ASIA-NQ-CANASTA_20250801_20260929.json").read_text())["operaciones"]["t"]
    otr = json.loads((ROOT / "docs/research/papel_m1_20261115/resultados/OTR930-NQ-CANASTA_20250801_20260929.json").read_text())["operaciones"]["t"]
    assert PR.causales(asia)["noche"] is False and PR.causales(asia)["vol20"] is True
    assert PR.causales(otr)["noche"] is True
    import pandas as pd
    s = pd.Series([1.0, -1.0], index=pd.to_datetime(["2025-08-04", "2025-08-05"]))
    V = pd.DataFrame(dict(vol20=[0, 1], tend60=[1.0, -1.0], noche=[0, 2], dst=[1, 1]), index=s.index)
    assert PR.mapa(s, V, t_entradas=asia[:2])["noche"] == "NO_CAUSAL"


def test_k49_potencia_de_la_lectura_en_dias():
    """K49: la potencia de una lectura se calcula con sesiones (días), y una lectura sin potencia se rechaza."""
    import numpy as np
    import pytest
    from edgelab.research import a5 as A5
    rng = np.random.default_rng(0)
    ses = np.repeat(np.arange(2000), 4); r = rng.normal(0.05, 1.0, len(ses)) + np.repeat(rng.normal(0, 1.0, 2000), 4)   # 4 filas por día, correlacionadas
    chico = A5.plan_lectura("FAM_TEST", ses, r, n_dias=100, nivel=0.01)
    grande = A5.plan_lectura("FAM_TEST", ses, r, n_dias=20000, nivel=0.01)
    assert chico["potencia"] < 0.8 <= grande["potencia"] and chico["n_dias"] == 100
    with pytest.raises(ValueError, match="K49"): A5.exigir_potencia(chico, "REP de prueba")
    A5.exigir_potencia(grande, "REP de prueba")
    assert "plan_lectura" in (ROOT / "tools/a5_campana.py").read_text(encoding="utf-8")


def test_jsonl_de_registros_parsean_linea_por_linea():
    """K50 (2026-11-19): un commit dejó LINAJES.jsonl con una línea vacía y dos objetos pegados en una línea; `antecedentes.py` se
    cayó y el alta siguiente quedó pegada a la anterior. Todo .jsonl versionado de docs/research parsea línea por línea."""
    r = subprocess.run(["git", "ls-files", "docs/research/*.jsonl"], cwd=ROOT, capture_output=True, text=True)
    malos = []
    for f in r.stdout.split():
        t = (ROOT / f).read_text(encoding="utf-8")
        if t and not t.endswith("\n"): malos.append(f"{f}: no termina en salto de línea (el próximo alta queda pegado; 2026-11-19 en FACTORES.jsonl)")
        for i, l in enumerate(t.splitlines(), 1):
            try: json.loads(l)
            except Exception as e: malos.append(f"{f}:{i}: {str(e)[:60]}")
    assert not malos, malos[:10]


def test_k51_corrida_ad_hoc_exige_estar_contada(tmp_path, monkeypatch):
    """K51 (2026-11-19): FRICCION-RQ arrancó aunque la guarda se había negado a contarla. `exigir_contada` frena antes de leer datos."""
    import registro_global as RG
    f = tmp_path / "g.jsonl"; f.write_text(json.dumps(dict(campaign_id="X", note="docs/research/x/PREREGISTRO.md")) + "\n")
    monkeypatch.setattr(RG, "GLOBAL", f)
    RG.exigir_contada("docs/research/x/PREREGISTRO.md")
    with pytest.raises(SystemExit, match="K51"):
        RG.exigir_contada("docs/research/y/PREREGISTRO.md")
    for t in ("tools/friccion_rq.py", "tools/t_regimen.py"):
        assert "exigir_contada" in (ROOT / t).read_text(encoding="utf-8")


def test_k54_ticks_sin_insumo_externo_no_calibran():
    """K54: FLUJOS-MACRO calibró FM7 con ticks sin VIX (el kernel de Kaggle no tenía el parquet de CBOE) contra M1 con VIX."""
    import sys
    from pathlib import Path
    import pandas as pd
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from a5_campana import insumos_distintos
    M = pd.DataFrame(dict(ses=[1, 2, 3], vix_prev=[17.0, 18.0, 19.0], FM7=[True, False, True], r_P=[0.1, 0.2, 0.3]))
    K = M.assign(vix_prev=float("nan"), r_P=float("nan"))
    assert insumos_distintos(K, M, ["FM7"]) == ["vix_prev"]
    assert insumos_distintos(M, M, ["FM7"]) == []
