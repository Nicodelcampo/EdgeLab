# -*- coding: utf-8 -*-
"""Lógica compartida de los manifiestos de identidad. **Un solo lugar.**

## El defecto que cierra

`manifiesto_datos.py` y `manifiesto_oraculos.py` tenían el mismo `main()`
duplicado, y los dos el mismo agujero:

```
--emitir  reescribía el manifiesto ENTERO con lo que hubiera en disco
verify    los archivos de más eran «SIN DECLARAR» y NO contaban como error
```

Las dos cosas juntas: **cada máquina que emite borra las declaraciones de la
otra, y nada lo marca.** Pasó de verdad el 2026-08-09 —una máquina con sólo 6E
emitió y el manifiesto de datos cayó de **31 archivos a 11**, el de oráculos de
**28 a 19**— y con eso **`ES` y `NQ` dejaron de estar declarados**, que son los
que EXPLORE-001 §7 paso 7 exige para la replicación.

Es el mismo modo de falla que este expediente persigue en todas partes: **un
gate que no puede detectar aquello para lo que existe.** Un manifiesto que se
angosta en silencio no protege de la deriva entre máquinas — la produce.

## Las dos reglas nuevas

1. **`--emitir` FUSIONA, no reemplaza.** Lo que estaba declarado y no está en
   este disco se **conserva** y se informa: casi siempre significa «lo tiene la
   otra máquina», no «ya no existe». Retirar una declaración exige `--retirar`,
   explícito y de a una.

2. **Se distingue lo benigno de lo grave.** Un archivo nuevo sin declarar es
   benigno —alguien capturó algo y todavía no lo declaró—. Que un archivo
   declarado **no esté** o que **tenga otros bytes** no lo es.

> **Nunca «arregles» un `FALTA` re-emitiendo.** Eso borra la declaración en vez
> de conseguir el archivo, y es exactamente cómo se perdieron `ES` y `NQ`.

## Por qué el código vive acá y no duplicado

Cuatro veces en esta sesión un cambio se aplicó en un lado y no en el otro
—campos renombrados, referencias muertas— y las cuatro reventaron al primer uso
real, ninguna a la lectura. Dos copias de esta lógica es esa apuesta otra vez.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def sha_de(p, bloque=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for trozo in iter(lambda: fh.read(bloque), b""):
            h.update(trozo)
    return h.hexdigest()


def declarado_en_git(repo, rel_manifiesto):
    """Lo que declara la versión COMMITEADA del manifiesto.

    Es el control que detecta el angostamiento: comparar contra el disco no
    alcanza —una máquina parcial se ve idéntica a un conjunto que encogió—.
    """
    try:
        out = subprocess.run(["git", "show", "HEAD:" + rel_manifiesto],
                             cwd=str(repo), capture_output=True, timeout=60)
        if out.returncode != 0:
            return {}
        return json.loads(out.stdout.decode("utf-8"))["archivos"]
    except Exception:
        return {}


def fusionar(previo, actual):
    """`(fusionado, solo_previo, cambiados)`.

    Las entradas de este disco **ganan** sobre las viejas con la misma ruta: si
    un archivo se reexportó, lo que vale es lo que hay. Las que no están en este
    disco se **conservan**: la otra máquina las tiene.
    """
    fusionado = dict(previo)
    cambiados = [k for k in actual
                 if k in previo and previo[k].get("sha256") != actual[k].get("sha256")]
    fusionado.update(actual)
    solo_previo = sorted(set(previo) - set(actual))
    return fusionado, solo_previo, cambiados


def emitir(ruta, cabecera, actual, previo, retirar=()):
    """Escribe el manifiesto FUSIONADO. Devuelve `(fusionado, solo_previo,
    cambiados, retirados)`."""
    fusionado, solo_previo, cambiados = fusionar(previo, actual)
    retirados = []
    for r in retirar:
        if r in fusionado:
            del fusionado[r]
            retirados.append(r)
    cuerpo = dict(cabecera)
    cuerpo.update(n_archivos=len(fusionado),
                  bytes_totales=sum(v.get("bytes", 0) for v in fusionado.values()),
                  archivos=fusionado)
    Path(ruta).write_text(
        json.dumps(cuerpo, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    return fusionado, solo_previo, cambiados, retirados


def verificar(esperado, actual):
    """`(faltan, sobran, distintos)` — tres categorías, no dos."""
    faltan = sorted(set(esperado) - set(actual))
    sobran = sorted(set(actual) - set(esperado))
    distintos = sorted(k for k in set(esperado) & set(actual)
                       if esperado[k]["sha256"] != actual[k]["sha256"])
    return faltan, sobran, distintos


def informar(esperado, actual, etiqueta, perdidas=()):
    """Imprime el veredicto y devuelve el exit code.

    `DIFIERE` y `FALTA` son error. `SIN DECLARAR` no: alguien capturó algo nuevo
    y todavía no lo declaró, y eso no pone en riesgo ninguna medición.
    """
    faltan, sobran, distintos = verificar(esperado, actual)
    print("manifiesto: %d %s | en disco: %d" % (len(esperado), etiqueta, len(actual)))
    for k in distintos:
        print("  DIFIERE      %s\n    manifiesto %s...\n    en disco   %s..."
              % (k, esperado[k]["sha256"][:16], actual[k]["sha256"][:16]))
    for k in faltan:
        print("  FALTA        %s  (sha %s...)" % (k, esperado[k]["sha256"][:16]))
    for k in sobran:
        print("  SIN DECLARAR %s  (sha %s...)" % (k, actual[k]["sha256"][:16]))
    if perdidas:
        print("\n  *** LA VERSION COMMITEADA DECLARABA %d ARCHIVO(S) QUE ESTE "
              "MANIFIESTO YA NO ***" % len(perdidas))
        for k in perdidas:
            print("      %s" % k)
        print("  Una declaracion que desaparece NO es un archivo que falta: es")
        print("  identidad que se perdio. Restaurar con --emitir (fusiona) o")
        print("  retirar explicitamente con --retirar.")

    if not (faltan or sobran or distintos or perdidas):
        print("  todo coincide")
        return 0
    if distintos:
        print("\n  DIFIERE es el caso grave: mismo nombre, otros bytes. Dos "
              "maquinas\n  midiendo sobre archivos distintos y creyendo que son "
              "el mismo.")
    if faltan:
        print("\n  FALTA puede ser simplemente que esta maquina no tenga ese "
              "archivo.\n  NO se arregla re-emitiendo: eso BORRA la declaracion "
              "en vez de\n  conseguir el archivo, y es exactamente como se "
              "perdieron ES y NQ.")
    return 1 if (faltan or distintos or perdidas) else 0
