# -*- coding: utf-8 -*-
"""Los manifiestos de identidad **no pueden angostarse en silencio**.

## El defecto que fija este archivo

`--emitir` reescribía el manifiesto entero con lo que hubiera en disco, y en
verificación los archivos de más eran «SIN DECLARAR» sin contar como error. Las
dos cosas juntas: **cada máquina que emite borra las declaraciones de la otra, y
nada lo marca.**

Pasó de verdad el 2026-08-09. Una máquina con sólo 6E emitió y:

```
datos     31 archivos -> 11
oraculos  28 archivos -> 19
```

Con eso **`ES` y `NQ` dejaron de estar declarados** — que son justamente los que
EXPLORE-001 §7 paso 7 exige para la replicación. La identidad de los datos de
replicación se perdió sin que nada fallara.

Es el modo de falla que este expediente persigue en todas partes: **un gate que
no puede detectar aquello para lo que existe.** Un manifiesto que se angosta en
silencio no protege de la deriva entre máquinas — la produce.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from tools._manifiesto_comun import emitir, fusionar, informar, verificar  # noqa: E402


def _e(sha, b=1):
    return dict(sha256=sha, bytes=b)


def test_emitir_CONSERVA_lo_que_esta_maquina_no_tiene(tmp_path):
    """El caso exacto del 2026-08-09: una máquina parcial emite y no debe
    borrar lo que declara la otra."""
    previo = {"data/6E.parquet": _e("a" * 64), "data/ES.parquet": _e("b" * 64),
              "data/NQ.parquet": _e("c" * 64)}
    actual = {"data/6E.parquet": _e("a" * 64)}          # esta maquina solo tiene 6E

    ruta = tmp_path / "m.json"
    fus, solo_previo, cambiados, retirados = emitir(ruta, {"x": 1}, actual, previo)

    assert set(fus) == set(previo), "el manifiesto se angosto: %s" % sorted(fus)
    assert solo_previo == ["data/ES.parquet", "data/NQ.parquet"]
    assert not cambiados and not retirados
    assert json.loads(ruta.read_text(encoding="utf-8"))["n_archivos"] == 3


def test_emitir_ACTUALIZA_lo_que_cambio_en_este_disco(tmp_path):
    """Un archivo reexportado gana sobre la declaración vieja: lo que vale es
    lo que hay. Pero el cambio se REPORTA, no pasa callado."""
    previo = {"data/6E.parquet": _e("a" * 64)}
    actual = {"data/6E.parquet": _e("z" * 64)}
    fus, _sp, cambiados, _r = emitir(tmp_path / "m.json", {}, actual, previo)
    assert fus["data/6E.parquet"]["sha256"] == "z" * 64
    assert cambiados == ["data/6E.parquet"]


def test_retirar_es_EXPLICITO_y_por_ruta(tmp_path):
    """Sacar una declaración tiene que costar un acto deliberado. Es la única
    salida legítima; re-emitir NO lo es."""
    previo = {"a.parquet": _e("a" * 64), "b.parquet": _e("b" * 64)}
    fus, _sp, _c, retirados = emitir(tmp_path / "m.json", {}, {}, previo,
                                     retirar=["b.parquet"])
    assert retirados == ["b.parquet"]
    assert set(fus) == {"a.parquet"}


def test_el_control_de_ANGOSTAMIENTO_dispara():
    """Comparar contra el disco no alcanza: una máquina parcial se ve idéntica
    a un conjunto que encogió. Por eso se compara contra la versión commiteada."""
    prev = {"a.parquet": _e("a" * 64)}
    assert informar(prev, prev, "archivos", []) == 0
    assert informar(prev, prev, "archivos", ["ES.parquet", "NQ.parquet"]) == 1


def test_DIFIERE_es_error_y_SIN_DECLARAR_no():
    """Mismo nombre y otros bytes es el caso grave —dos máquinas midiendo sobre
    archivos distintos creyendo que son el mismo—. Un archivo nuevo todavía sin
    declarar no pone en riesgo ninguna medición."""
    decl = {"a.parquet": _e("a" * 64)}

    distinto = {"a.parquet": _e("z" * 64)}
    faltan, sobran, distintos = verificar(decl, distinto)
    assert distintos == ["a.parquet"] and not faltan and not sobran
    assert informar(decl, distinto, "archivos", []) == 1

    de_mas = {"a.parquet": _e("a" * 64), "nuevo.parquet": _e("n" * 64)}
    faltan, sobran, distintos = verificar(decl, de_mas)
    assert sobran == ["nuevo.parquet"] and not faltan and not distintos
    assert informar(decl, de_mas, "archivos", []) == 0, \
        "un archivo nuevo sin declarar no deberia ser error"


def test_FALTA_no_falla_por_defecto_pero_si_con_exigir_completo():
    """`FALTA` dejo de ser error, y es un cambio deliberado.

    Tratarlo como error dejaba el gate en ROJO PERMANENTE en un setup de dos
    maquinas donde ninguna tiene todo -- una tiene ES/NQ, la otra el archivo
    6E_dirty-. Un gate que siempre falla es un gate que alguien va a dejar de
    mirar: el mismo defecto que ya aparecio cuando la re-verificacion de la
    sonda abortaba siempre porque `sys.modules` crece.

    El trabajo de este gate es "los archivos que tengo son los correctos", no
    "tengo todos". La segunda pregunta se contesta donde SI se sabe cuales
    hacen falta.
    """
    decl = {"a.parquet": _e("a" * 64), "b.parquet": _e("b" * 64)}
    solo_a = {"a.parquet": _e("a" * 64)}
    assert informar(decl, solo_a, "archivos", []) == 0
    assert informar(decl, solo_a, "archivos", [], exigir_completo=True) == 1

    # pero un DIFIERE falla igual, con o sin el flag
    distinto = {"a.parquet": _e("z" * 64)}
    assert informar(decl, distinto, "archivos", []) == 1


def test_fusionar_es_idempotente():
    """Emitir dos veces seguidas sobre el mismo disco no debe cambiar nada."""
    previo = {"a.parquet": _e("a" * 64), "b.parquet": _e("b" * 64)}
    actual = {"a.parquet": _e("a" * 64)}
    f1, _s, _c = fusionar(previo, actual)
    f2, _s2, _c2 = fusionar(f1, actual)
    assert f1 == f2


@pytest.mark.parametrize("herramienta,manifiesto", [
    ("tools/manifiesto_datos.py", "docs/datos_manifiesto.json"),
    ("tools/manifiesto_oraculos.py", "docs/oraculos_manifiesto.json"),
])
def test_las_dos_herramientas_usan_la_logica_COMPARTIDA(herramienta, manifiesto):
    """Cuatro veces en esta sesión un cambio se aplicó en un lado y no en el
    otro. Dos copias de esta lógica sería esa apuesta otra vez."""
    src = open(os.path.join(REPO, herramienta), encoding="utf-8").read()
    assert "from tools._manifiesto_comun import" in src
    assert "informar(" in src and "emitir(" in src
    assert "--retirar" in src, "sin salida explicita, la unica forma de sacar "\
                               "una declaracion vuelve a ser re-emitir"
    assert os.path.exists(os.path.join(REPO, manifiesto))


def test_los_manifiestos_vigentes_no_perdieron_ES_ni_NQ():
    """Regresión concreta del 2026-08-09: `ES` y `NQ` son los de la replicación
    de EXPLORE-001 §7 paso 7. Si vuelven a desaparecer, esto lo caza."""
    d = json.load(open(os.path.join(REPO, "docs", "datos_manifiesto.json"),
                       encoding="utf-8"))["archivos"]
    for inst in ("ES", "NQ"):
        assert any("/%s_parquet/" % inst in k for k in d), \
            "%s dejo de estar declarado -- es dato de replicacion" % inst
