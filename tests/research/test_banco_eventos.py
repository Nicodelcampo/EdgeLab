"""Banco de eventos: contrato, partición honesta, efecto plantado que se encuentra, ruido que no, y libro de usos de la mitad B."""
import json

import numpy as np
import pandas as pd
import pytest

from edgelab.research import banco_eventos as BE


def _tabla(efecto=0.0, n_dias=160, por_dia=30, seed=1):
    rng = np.random.default_rng(seed); filas = []
    dias = pd.bdate_range("2025-07-01", periods=n_dias)
    for inst in ("NQ", "ES"):
        for d in dias:
            f = int(d.strftime("%Y%m%d"))
            for p in (0, 0, 0, 1):
                for _ in range(por_dia // 4):
                    a, b, c = rng.normal(size=3); k = int(rng.integers(0, 3))
                    pr = 0.5 + (efecto if (p == 0 and a > 0.43) else 0.0)       # tercio alto de `a`: rompe más (sólo en los reales)
                    y = 1.0 if rng.random() < pr else -1.0
                    filas.append(dict(inst=inst, fecha=f, placebo=p, a=a, b=b, c=c, k=k, rompe=y, avance=y * 0.5 + rng.normal()))
    return pd.DataFrame(filas)


SPEC = dict(nombre="TEST_banco", familia="TEST_BANCO", tabla="x.csv", ventana=[20250701, 20260331], desenlace="rompe",
            columnas_desenlace=["rompe", "avance"], justificacion_economica="prueba", como_refutar="prueba", n_boot=400, tabla_no_mirada=True, cortes_fijos={"k": [0.5, 1.5]})


def test_contrato_detecta_fugas_holdout_y_campos():
    T = _tabla(n_dias=30)
    assert BE.validar(BE.especificacion(SPEC), T) == []
    assert any("fuga" in e for e in BE.validar(BE.especificacion(dict(SPEC, rasgos=["a", "avance"])), T))
    assert any("holdout" in e for e in BE.validar(BE.especificacion(dict(SPEC, ventana=[20250701, 20261015])), T))
    assert any("justificacion" in e for e in BE.validar(BE.especificacion({k: v for k, v in SPEC.items() if k != "justificacion_economica"}), T))
    T2 = T.copy(); T2.loc[0, "fecha"] = 20261005
    assert any("holdout" in e for e in BE.validar(BE.especificacion(SPEC), T2))
    assert "avance" not in BE.rasgos_de(BE.especificacion(SPEC), T)
    assert any("tabla_no_mirada" in e for e in BE.validar(BE.especificacion(dict(SPEC, tabla_no_mirada=False)), T))


def test_particion_solo_depende_de_la_fecha_y_es_balanceada():
    f = pd.bdate_range("2025-07-01", periods=200).strftime("%Y%m%d").astype(int).to_numpy()
    m = BE.mitad(f, "X"); assert 0.4 < m.mean() < 0.6
    assert (BE.mitad(f, "X") == m).all() and (BE.mitad(f[::-1], "X") == m[::-1]).all()
    sem = pd.to_datetime(f.astype(str)).isocalendar().week.to_numpy()
    assert all(len(set(m[sem == w])) == 1 for w in set(sem))                      # una semana entera cae en la misma mitad


def test_efecto_plantado_se_nomina_y_el_ruido_no():
    out = BE.correr(SPEC, _tabla(efecto=0.12), ensayo=True)
    celdas = [r for r in out["resultados"] if r["tipo"] == "celda"]
    assert celdas[0]["nombre"].startswith("a=2") or any(r["nombre"].startswith("a=2") and r["nominada"] for r in celdas)
    assert any(r["nominada"] for r in out["resultados"])
    assert out["pruebas_en_b"] <= SPEC.get("k", 3) + 1 and out["celdas_exploradas"] > 50   # se exploró mucho y se probó poco
    ruido = BE.correr(SPEC, _tabla(efecto=0.0, seed=5), ensayo=True)
    assert ruido["nominadas"] == []


def test_las_hipotesis_no_dependen_de_la_mitad_b():
    T = _tabla(efecto=0.12); s = BE.especificacion(SPEC)
    A, B, _ = BE.partir(s, T)
    h1 = BE.explorar(A, s, BE.rasgos_de(s, T))["hipotesis"]
    T2 = T.copy(); mb = (T2.placebo == 0) & (BE.mitad(T2.fecha, s["familia"]) == 1)
    T2.loc[mb, "rompe"] = -T2.loc[mb, "rompe"]; T2.loc[mb, "a"] = 0.0           # cambiar B entero no cambia lo congelado
    A2, _, _ = BE.partir(s, T2)
    assert json.dumps(BE.explorar(A2, s, BE.rasgos_de(s, T2))["hipotesis"], default=float) == json.dumps(h1, default=float)


def test_calibracion_y_preflight():
    T = _tabla(efecto=0.0, n_dias=100, seed=3)
    c = BE.calibrar(SPEC, T, n=8, seed=3)
    assert c["corridas"] == 8 and c["tasa"] <= 0.4
    p = BE.preflight(SPEC, T, n_calibracion=20); assert p["ok"], p


def test_la_mitad_b_se_usa_una_sola_vez(tmp_path):
    T = _tabla(efecto=0.12, n_dias=80)
    out = BE.correr(SPEC, T, raiz=tmp_path, registro=tmp_path / "reg.jsonl")
    d = tmp_path / "TEST_banco"
    assert (d / "HIPOTESIS_CONGELADAS.json").exists() and (d / "RESULTADO.json").exists() and (d / "RECOMENDACIONES.md").exists()
    reg = [json.loads(l) for l in (tmp_path / "reg.jsonl").read_text().splitlines()]
    assert {r["campaign_id"] for r in reg} == {"banco/TEST_banco/A", "banco/TEST_banco/B"} and reg[1]["n_trials"] == out["pruebas_en_b"]
    with pytest.raises(ValueError, match="ya se usó"):
        BE.correr(dict(SPEC, nombre="TEST_banco_otra_idea"), T, raiz=tmp_path, registro=tmp_path / "reg.jsonl")


def test_calibracion_mide_la_tasa_de_falsos():
    """La calibración distingue: con q = 0,9 la tasa de falsos se dispara; con q = 0,2 el método sano no se bloquea."""
    c = BE.calibrar(dict(SPEC, q=0.9), _tabla(efecto=0.0, n_dias=60, seed=2), n=10)
    assert c["tasa"] > 0.5
    c = BE.calibrar(dict(SPEC, q=0.2), _tabla(efecto=0.0, n_dias=60, seed=2), n=10)   # sano: no bloquea
    assert c["ok"]


def test_hipotesis_previa_se_prueba_en_toda_la_tabla():
    """Una hipótesis elegida en otros datos se prueba con A ∪ B y su propio BH. La prueba es «la celda paga» (media > nulo): una
    celda sin mecanismo propio puede heredar la media positiva del evento; `vs_resto` separa el mecanismo de esa herencia."""
    T = _tabla(efecto=0.12, n_dias=100)
    s = dict(SPEC, hipotesis_previas=[dict(rasgos=["a"], estratos=[2], signo=1, origen="NQ/ES"), dict(rasgos=["b"], estratos=[2], signo=1)])
    out = BE.correr(s, T, ensayo=True)
    p = {r["nombre"]: r for r in out["previas"]}
    assert p["a=2"]["nominada"]
    za = p["a=2"]["vs_resto"]["estimacion"] / p["a=2"]["vs_resto"]["se"]; zb = p["b=2"]["vs_resto"]["estimacion"] / p["b=2"]["vs_resto"]["se"]
    assert za > 3 and abs(zb) < 2.5                                               # el mecanismo está en `a`, no en `b`
    assert p["a=2"]["n_b"] > max(r["n_b"] for r in out["resultados"] if r["tipo"] == "celda")   # usa toda la tabla, no sólo B


def test_preflight_frena_sin_potencia_para_celdas():
    """K21: una tabla donde ningún estrato de A llega a min_n no gasta la mitad B."""
    p = BE.preflight(dict(SPEC, min_n=2000), _tabla(n_dias=60), n_calibracion=2)
    assert not p["ok"] and any("sin potencia para celdas" in e for e in p["errores"])


def test_generadores_cumplen_el_contrato():
    """Acotación de F9: todo generador (propio o no) declara mecanismo y refutación y apunta a un test de causalidad que existe."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    for n, g in BE.GENERADORES.items():
        assert {"funcion", "tabla", "eventos", "desenlaces", "test_causalidad", "mecanismo", "como_refutar"} <= set(g), n
        archivo, test = g["test_causalidad"].split("::")
        assert f"def {test}(" in (root / archivo).read_text(encoding="utf-8"), f"{n}: falta {g['test_causalidad']}"
