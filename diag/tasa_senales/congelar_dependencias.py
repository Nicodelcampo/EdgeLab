# -*- coding: utf-8 -*-
"""Congela el conjunto de dependencias. **Representa al productor final.**

## El defecto que cierra

La versión anterior de la sonda **registraba** las dependencias importadas
después del arranque y **no bloqueaba**. Eso es fail-open: un módulo importado a
mitad de la medición pudo cambiar entre el arranque y su primer uso, y el hash
tomado al inicio no lo cubría. «El conjunto creció» se había convertido en
«registro el crecimiento», que no es lo mismo que «el conjunto estaba
congelado».

`sys.modules` creciendo no significa que haya que ignorar las adiciones:
significa que **el conjunto todavía no estaba congelado**.

## Las dos fases, y por qué el manifiesto no sale sólo de los artefactos

1. **Descubrimiento** — la sonda corre normalmente sobre la muestra más amplia
   posible y observa qué se importa de verdad durante la **medición**. Esas
   corridas son *dependency-discovery runs* y **no son evidencia canónica**,
   aunque el comparador les dé exit 0.

2. **Congelado** — este script toma la unión de eso **más lo que importa el
   código final**, que es la parte que los artefactos de descubrimiento no
   pueden conocer: fueron producidos por una versión anterior. Congelar sólo lo
   observado por ellos dejaría afuera los imports que introduce el propio
   parche, y la primera corrida canónica abortaría por una dependencia «nueva»
   que en realidad es infraestructura.

   Por eso este script **importa el módulo de la sonda ya parcheado** y observa
   `sys.modules`. No mide nada: sólo carga.

```
deps de MEDICIÓN (8s + 40s)  +  deps de INICIALIZACIÓN (código final)
        +  inputs explícitos  =  manifiesto congelado
```

Después, la corrida canónica **prehashea** ese conjunto sin importarlo, mide con
el **orden natural** de imports, y exige `new_unfrozen_dependency_files == []`.
Si aparece cualquier archivo adicional, **aborta**: no amplía el manifiesto y
sigue. La ampliación exige una discovery nueva y otro commit.

## El hash del manifiesto NO va adentro del manifiesto

Sería una referencia circular imposible de satisfacer: el archivo tendría que
contener el hash de sus propios bytes, que dependen de ese hash. La forma
correcta es la separación de responsabilidades:

```
el manifiesto contiene   schema + entradas congeladas
el ARTEFACTO calcula     dependency_manifest_sha256 = sha256(bytes del manifiesto)
el agregado de repo      incluye los bytes del manifiesto como una dependencia más
```

## Alcance de lo que esto sostiene

Con el conjunto congelado y la superficie residual declarada, la afirmación
defendible es **«equivalencia bajo el mismo runtime observado»**. No es
«reproducibilidad bit a bit garantizada en cualquier máquina», y decirlo así
sería sobreafirmar: ver `known_uncovered_runtime_surface` en la sonda.

Uso:
    python diag/tasa_senales/congelar_dependencias.py descubrimiento1.json ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
SALIDA = Path(__file__).resolve().parent / "dependencias_congeladas.json"

#: Los artefactos de descubrimiento se emitieron con rutas SIN prefijo de
#: ámbito (`diag/...` para repo, `.venv/...` para entorno). El código final usa
#: identificadores canónicos con prefijo. Se convierte explícitamente en vez de
#: asumir que coinciden: dos formatos que se parecen es como se cuelan los
#: conjuntos mal unidos.
def _normalizar(ruta_vieja):
    if ruta_vieja.startswith(".venv/"):
        return "venv:" + ruta_vieja[len(".venv/"):]
    return "repo:" + ruta_vieja


def deps_de_inicializacion():
    """Lo que importa el CÓDIGO FINAL con sólo cargarse. No mide nada."""
    import importlib
    m = importlib.import_module("diag.tasa_senales.sonda_alejamiento_cero")
    ident = getattr(m, "_ident", None)
    if ident is None:
        raise SystemExit("la sonda no expone `_ident`: aplicar el parche antes "
                         "de congelar")
    vistos = set()
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f or "__pycache__" in str(f):
            continue
        par = ident(f)
        if par:
            vistos.add(par[1])
    return vistos, m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("descubrimientos", nargs="+",
                    help="artefactos de las corridas de descubrimiento")
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    medicion, fuentes = set(), []
    for p in a.descubrimientos:
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception as e:
            print("no se pudo leer %s: %s" % (p, e))
            return 2
        i = d.get("identidad") or {}
        rep = i.get("dependency_set_repo") or {}
        ent = i.get("dependency_set_entorno") or {}
        # el mapa de entorno del CIERRE incluye lo importado tarde: congelar el
        # del arranque dejaria afuera justo lo que hay que cubrir.
        tard = i.get("entorno_importado_durante_la_corrida") or []
        nuevas = {_normalizar(r) for r in list(rep) + list(ent) + list(tard)}
        medicion |= nuevas
        fuentes.append(dict(archivo=Path(p).name, contrato=d.get("contrato"),
                            sesiones=d.get("sesiones"),
                            payload_sha256=d.get("payload_sha256"),
                            n_repo=len(rep), n_entorno=len(ent),
                            n_tardios=len(tard)))
        print("  medicion   %-40s %4d rutas" % (Path(p).name, len(nuevas)))

    inicial, mod = deps_de_inicializacion()
    print("  inicializacion  codigo final                    %4d rutas" % len(inicial))

    # EL MANIFIESTO SE INCLUYE A SI MISMO en la lista de dependencias -- no su
    # hash, que seria circular, sino su RUTA. `conjunto_de_dependencias` lo
    # cuenta como dependencia de repo -y con razon: cambiarlo cambia que se
    # congela-, asi que si no estuviera en la lista apareceria como "archivo no
    # congelado" en la primera corrida canonica y abortaria.
    propio = "repo:" + (Path(a.out).resolve()
                        .relative_to(REPO).as_posix())
    congelado = sorted(medicion | inicial | {propio})
    solo_inicial = sorted(inicial - medicion)
    solo_medicion = sorted(medicion - inicial)
    print("\n  union                                          %4d rutas" % len(congelado))
    print("  solo en el codigo final (las que el parche agrega)  %4d" % len(solo_inicial))
    print("  solo en medicion (se cargan al medir, no al importar) %4d" % len(solo_medicion))

    cuerpo = dict(
        schema_version="dependencias_congeladas_v1",
        que_es="conjunto CONGELADO de dependencias: union de lo observado al "
               "MEDIR (corridas de descubrimiento) y lo que importa el CODIGO "
               "FINAL al cargarse. La corrida canonica lo PREHASHEA sin "
               "importarlo y exige new_unfrozen_dependency_files == [].",
        como_se_verifica="el sha256 de ESTE archivo se calcula AFUERA y se "
                         "publica en el artefacto como dependency_manifest_sha256. "
                         "No se embebe aca: seria una referencia circular.",
        dependencias=congelado,
        n=len(congelado),
        procedencia=dict(fuentes_de_medicion=fuentes,
                         n_solo_inicializacion=len(solo_inicial),
                         n_solo_medicion=len(solo_medicion),
                         solo_inicializacion=solo_inicial),
        no_cubre=list(getattr(mod, "SUPERFICIE_NO_CUBIERTA", [])),
    )
    Path(a.out).write_text(json.dumps(cuerpo, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("\nCONGELADO -> %s" % a.out)
    print("el sha256 de este archivo lo calcula y publica el ARTEFACTO, no el "
          "archivo mismo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
