"""K55/K56 (2026-11-19): la práctica correcta del caso Z como paso obligatorio de la cadena.

1. Todo pre-registro nuevo declara «Diagnóstico de mecanismo:» (preflight.validar_preregistro; sin eso no se cuentan pruebas ni se corre).
2. Todo RESULTADO nuevo que lea una meseta, un PBO o «N/N variantes» lleva la línea «Diagnóstico de grilla:» (edgelab.research.diagnostico_grilla,
   tools/diagnostico_grilla.py), y todo RESULTADO nuevo que declare una regla «apagada»/«se apaga» lleva «Episodios:».
Las listas de excepción (documentos anteriores) son cerradas: config/preregistros_sin_diagnostico.json y config/resultados_sin_diagnostico.json."""
import json, re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LEE_GRILLA = re.compile(r"\bPBO\b|meseta|\b\d+\s*/\s*\d+\s+variantes", re.I)
APAGADA = re.compile(r"apagad|se apag|muri[oó]", re.I)


def test_resultados_nuevos_llevan_diagnostico_y_episodios():
    base = set(json.loads((ROOT / "config/resultados_sin_diagnostico.json").read_text(encoding="utf-8")))
    mal = []
    for p in ROOT.glob("docs/research/**/RESULTADO*.md"):
        rel = p.relative_to(ROOT).as_posix()
        if rel in base: continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if LEE_GRILLA.search(t) and "Diagnóstico de grilla:" not in t: mal.append(f"{rel}: lee meseta/PBO/variantes sin «Diagnóstico de grilla:»")
        if APAGADA.search(t) and "Episodios:" not in t: mal.append(f"{rel}: declara una regla apagada sin «Episodios:»")
    assert not mal, "K55/K56 — correr tools/diagnostico_grilla.py y pegar sus líneas:\n" + "\n".join(mal)


def test_las_listas_de_excepcion_son_cerradas():
    pre = json.loads((ROOT / "config/preregistros_sin_diagnostico.json").read_text(encoding="utf-8"))
    res = json.loads((ROOT / "config/resultados_sin_diagnostico.json").read_text(encoding="utf-8"))
    assert len(pre) <= 171 and len(res) <= 202, "las excepciones de K55/K56 no crecen: un documento nuevo cumple la regla"


def test_preregistro_nuevo_sin_diagnostico_falla(tmp_path):
    from edgelab.research.preflight import validar_preregistro, north_star_sha256
    p = tmp_path / "docs/research/x/PREREGISTRO.md"; p.parent.mkdir(parents=True)
    (tmp_path / "docs").mkdir(exist_ok=True); (tmp_path / "docs/NORTH_STAR.md").write_text((ROOT / "docs/NORTH_STAR.md").read_text(encoding="utf-8"), encoding="utf-8")
    base = (f"Estado: PRE-REGISTRO\n{north_star_sha256(ROOT)}\nJustificación económica\nCómo podría refutarse\nEF3\nAntecedentes: x\n"
            "Potencia previa: x\nLectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §7\n")
    p.write_text(base, encoding="utf-8")
    assert any("Diagnóstico de mecanismo" in e for e in validar_preregistro(p, tmp_path, exigir_commit=False))
    p.write_text(base + "Diagnóstico de mecanismo: no aplica — una sola regla sin grilla\n", encoding="utf-8")
    assert not any("Diagnóstico de mecanismo" in e for e in validar_preregistro(p, tmp_path, exigir_commit=False))


def test_diagnostico_detecta_celda_vacia_copias_y_episodios():
    from edgelab.research.diagnostico_grilla import diagnostico, episodios
    rng = np.random.default_rng(0); meses = [f"2020-{m:02d}" for m in range(1, 13)]; filas = []
    for v, n in [("Z_10_10_1", 4), ("Z_15_20_1", 300), ("Z_15_20_2", 300), ("Z_30_30_1", 600)]:
        base = rng.normal(0, 1, 600)                      # Z_15_20_* comparten serie: casi-copias
        for i in range(n): filas.append(dict(variante=v, R=(base[i] if v.startswith("Z_15_20") else rng.normal(0, 1)), mes=meses[i % 12]))
    d = diagnostico(pd.DataFrame(filas))
    assert "Z_10_10_1" in d["degeneradas"] and d["numero_efectivo"] < 4 and d["linea"].startswith("Diagnóstico de grilla:")
    o = pd.DataFrame(dict(R=[-5, -5, 1, 1, 1, 1], mes=["a", "b", "c", "d", "e", "f"]))
    e = episodios(o, k=2); assert e["media"] < 0 < e["media_sin_peores"] and e["linea"].startswith("Episodios:")
