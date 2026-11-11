from edgelab.bridge.indicators.bandas_concentracion import detectar, VIDA_S


def _z(t0, bottom, top, vida=VIDA_S):
    return {"t0": t0, "t1": t0 + vida, "bottom": bottom, "top": top}


def test_nace_al_llegar_al_umbral_y_no_antes():
    zonas = [_z(60 * i, 1.0 + i * 0.0001, 1.0 + i * 0.0001 + 0.00005) for i in range(3)]
    b = detectar(zonas, [0, 60, 120, 180], alto=0.0008, umbral=3)
    assert len(b) == 1 and b[0].t0 == 120 and b[0].n0 == 3       # causal: recién con la tercera zona nacida


def test_zona_que_no_entra_completa_no_cuenta():
    zonas = [_z(0, 1.0, 1.0001), _z(0, 1.0002, 1.0003), _z(0, 1.0007, 1.0010)]
    assert detectar(zonas, [0], alto=0.0008, umbral=3) == []


def test_encadenada_se_alarga_en_vez_de_duplicarse():
    zonas = [_z(0, 1.0, 1.0001), _z(0, 1.0001, 1.0002), _z(VIDA_S - 60, 1.0, 1.0001), _z(VIDA_S - 60, 1.0001, 1.0002)]
    b = detectar(zonas, list(range(0, 2 * VIDA_S, 60)), alto=0.0008, umbral=2)
    assert len(b) == 1 and b[0].t0 == 0 and b[0].t1 == (2 * VIDA_S - 120) + VIDA_S


def test_bandas_en_otro_precio_son_distintas():
    zonas = [_z(0, 1.0, 1.0001), _z(0, 1.0001, 1.0002), _z(0, 1.01, 1.0101), _z(0, 1.0101, 1.0102)]
    assert len(detectar(zonas, [0, 60], alto=0.0008, umbral=2)) == 2


def test_paridad_js(tmp_path):
    import json, random, shutil, subprocess
    from dataclasses import asdict
    from pathlib import Path
    import pytest
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    rnd = random.Random(7)
    zonas = []
    for i in range(600):                                   # zonas chicas y apiladas alrededor de dos precios que derivan
        base = (1.10 if i % 2 else 1.103) + rnd.gauss(0, 0.0004) + i * 0.000002
        h = rnd.choice([0.00002, 0.00005, 0.0001, 0.0002])
        zonas.append(_z(60 * rnd.randrange(0, 3000), round(base, 5), round(base + h, 5)))
    tiempos = list(range(0, 3200 * 60, 60))
    py = [asdict(b) for b in detectar(zonas, tiempos, alto=0.0008, umbral=12)]
    (tmp_path / "in.json").write_text(json.dumps(dict(z=zonas, t=tiempos)))
    js_mod = Path(__file__).resolve().parents[2] / "viewer" / "nt8_bridge" / "bandas_concentracion.js"
    script = (f"const B=require({json.dumps(str(js_mod))});const d=require({json.dumps(str(tmp_path / 'in.json'))});"
              "process.stdout.write(JSON.stringify(B.detectar(d.z,d.t,0.0008,12)));")
    js = json.loads(subprocess.run([node, "-e", script], capture_output=True, text=True, check=True).stdout)
    assert len(py) >= 3
    assert [(b["t0"], b["t1"], round(b["piso"], 6), b["n"], b["n0"]) for b in py] == \
           [(b["t0"], b["t1"], round(b["piso"], 6), b["n"], b["n0"]) for b in js]
