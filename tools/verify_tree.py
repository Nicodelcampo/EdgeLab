#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/verify_tree.py@v1

Verificacion independiente del arbol fisico research-v2 contra el manifiesto de
ejecucion de tools/recut_holdout.py@v1 (recut_index.json con precheck=false).

Por que existe: los digestos de salida los calculo el mismo proceso que escribio
los archivos, asi que el manifiesto es auto-atestiguado. Esta herramienta los
recalcula desde cero, en otro momento, y ademas audita lo que un manifiesto no
puede atestiguar sobre si mismo:

  1. inventario exacto del arbol (nada de mas, nada de menos, sin ambiguedad),
  2. integridad de las fuentes inmutables DESPUES de la escritura,
  3. si los "limpios" son enlaces duros que comparten inodo con el origen,
  4. si los parquets quedaron con permiso de escritura,
  5. columnas redundantes delatadas por digestos identicos,
  6. con --maxts: que max(ts_utc_ns) medido EN DISCO caiga antes de la apertura
     de la sesion CME del primer trade date de holdout. Esta es la unica prueba
     fisica de "cero holdout" que no depende de lo que declaro el escritor.

Fail-closed: un chequeo que no se puede evaluar es una falla, salvo los que se
marcan explicitamente como [skip ] por falta de --base, --maxts o pyarrow.

No usa red. No lee datos de holdout (el arbol no deberia tenerlos; si los tiene,
esta herramienta lo reporta y sale con codigo 1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile

TOOL_ID = "tools/verify_tree.py@v1"
SCHEMA_VERSION = 1
EXPECTED_RECUT_TOOL = "tools/recut_holdout.py@v1"
CHUNK = 1 << 20
TS_COLUMN = "ts_utc_ns"

VERDICT_PRECEDENCE = (
    "FAIL_HOLDOUT",
    "FAIL_MANIFIESTO",
    "FAIL_INVENTARIO",
    "FAIL_FALTANTE",
    "FAIL_DIGESTO",
    "FAIL_FUENTE",
    "FAIL_COLUMNAS",
    "WARN_ENLACES",
    "WARN_ESCRITURA",
    "WARN_COLUMNAS",
    "PASS",
)

FAIL_FAMILY = {
    "holdout.max_ts_fisico": "FAIL_HOLDOUT",
    "manifiesto.herramienta": "FAIL_MANIFIESTO",
    "manifiesto.no_precheck": "FAIL_MANIFIESTO",
    "manifiesto.veredicto": "FAIL_MANIFIESTO",
    "manifiesto.estados": "FAIL_MANIFIESTO",
    "manifiesto.totales": "FAIL_MANIFIESTO",
    "manifiesto.particion": "FAIL_MANIFIESTO",
    "inventario.faltantes": "FAIL_FALTANTE",
    "inventario.extras": "FAIL_INVENTARIO",
    "inventario.sin_ambiguedad": "FAIL_INVENTARIO",
    "inventario.carpetas": "FAIL_INVENTARIO",
    "salidas.digestos": "FAIL_DIGESTO",
    "enlaces.digestos": "FAIL_DIGESTO",
    "fuente.intacta": "FAIL_FUENTE",
    "columnas.verificado_pyarrow": "FAIL_COLUMNAS",
}

WARN_FAMILY = {
    "enlaces.inodo": "WARN_ENLACES",
    "proteccion.escritura": "WARN_ESCRITURA",
    "columnas.digestos_duplicados": "WARN_COLUMNAS",
}


class Check:
    __slots__ = ("cid", "level", "detail")

    def __init__(self, cid: str, level: str, detail: str) -> None:
        self.cid = cid
        self.level = level
        self.detail = detail


# ---------------------------------------------------------------- utilidades


def digests_of(path: str):
    """Devuelve (bytes, sha256, git_blob_sha1, st) en una sola pasada."""
    st = os.stat(path)
    size = st.st_size
    h256 = hashlib.sha256()
    h1 = hashlib.sha1()
    h1.update(b"blob %d\0" % size)
    with open(path, "rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h256.update(block)
            h1.update(block)
    return size, h256.hexdigest(), h1.hexdigest(), st


def walk_files(root: str):
    """Devuelve (parquets: nombre -> [rutas], otros: [rutas])."""
    parquets: dict[str, list[str]] = {}
    otros: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if fn.lower().endswith(".parquet"):
                parquets.setdefault(fn, []).append(full)
            else:
                otros.append(full)
    return parquets, otros


def basename_of(declared: str) -> str:
    return os.path.basename(str(declared or "").replace("\\", "/"))


def parent_of(declared: str) -> str:
    return os.path.basename(os.path.dirname(str(declared or "").replace("\\", "/")))


def is_writable_mode(st) -> bool:
    return bool(stat.S_IMODE(st.st_mode) & 0o222)


def fmt(n: int) -> str:
    return "{:,}".format(n).replace(",", ".")


def evaluate_max_ts(medidos, boundary):
    """Logica pura de la prueba fisica de holdout, testeable sin pyarrow.

    medidos: nombre -> (min_ts, max_ts). Devuelve la lista de violaciones.
    """
    violaciones = []
    for nombre in sorted(medidos):
        _mn, mx = medidos[nombre]
        if mx is None:
            violaciones.append("%s: sin max(%s) medible" % (nombre, TS_COLUMN))
        elif mx >= boundary:
            violaciones.append("%s: max_ts %d >= frontera %d (HOLDOUT EN EL ARBOL)"
                               % (nombre, mx, boundary))
    return violaciones


def max_ts_of(pq, pc, path, column=TS_COLUMN):
    """(min, max) de una columna, por estadisticas del footer si estan; si no, escaneando."""
    pf = pq.ParquetFile(path)
    md = pf.metadata
    idx = pf.schema_arrow.get_field_index(column)
    if idx < 0:
        raise ValueError("sin columna %s" % column)
    mins, maxs, stats_ok = [], [], True
    for rg in range(md.num_row_groups):
        st = md.row_group(rg).column(idx).statistics
        if st is None or not st.has_min_max:
            stats_ok = False
            break
        mins.append(st.min)
        maxs.append(st.max)
    if stats_ok and maxs:
        return min(mins), max(maxs)
    mn = mx = None
    for batch in pf.iter_batches(batch_size=262144, columns=[column]):
        col = batch.column(0)
        b_mn = pc.min(col).as_py()
        b_mx = pc.max(col).as_py()
        if b_mn is not None:
            mn = b_mn if mn is None else min(mn, b_mn)
        if b_mx is not None:
            mx = b_mx if mx is None else max(mx, b_mx)
    if mx is None:
        raise ValueError("columna vacia")
    return mn, mx


# ------------------------------------------------------------- verificacion


def verify(index, out_base, base=None, hash_sources=True, want_columns=False,
           want_maxts=False):
    checks: list[Check] = []

    def add(cid, level, detail):
        checks.append(Check(cid, level, detail))

    # -- 1. el manifiesto describe un arbol real y es de la herramienta correcta
    tool = index.get("tool")
    add("manifiesto.herramienta", "ok" if tool == EXPECTED_RECUT_TOOL else "falla",
        "tool=%r" % (tool,))

    precheck = index.get("precheck")
    add("manifiesto.no_precheck", "ok" if precheck is False else "falla",
        "precheck=%r (un manifiesto de precheck no describe ningun arbol)" % (precheck,))

    verdict_in = index.get("verdict")
    add("manifiesto.veredicto", "ok" if verdict_in == "PASS" else "falla",
        "verdict=%r" % (verdict_in,))

    records = [r for r in (index.get("files") or []) if isinstance(r, dict)]
    linked = [r for r in (index.get("linked_clean") or []) if isinstance(r, dict)]

    incompletos = [
        r.get("file") for r in records
        if r.get("status") != "RECUT"
        or not r.get("output")
        or not r.get("output_sha256")
        or not r.get("output_blob_sha1")
        or not isinstance(r.get("output_bytes"), int)
    ]
    add("manifiesto.estados", "ok" if not incompletos else "falla",
        "registros sin RECUT/output/digesto: %s"
        % (", ".join(str(x) for x in incompletos[:5]) or "ninguno"))

    totals = index.get("totals") or {}
    calc = {
        "targets": len(records),
        "recut": sum(1 for r in records if r.get("status") == "RECUT"),
        "rows_total_source": sum(int(r.get("rows_total") or 0) for r in records),
        "rows_keep": sum(int(r.get("rows_keep") or 0) for r in records),
        "rows_drop": sum(int(r.get("rows_drop") or 0) for r in records),
        "rows_leaked_by_naive_utc_cut":
            sum(int(r.get("rows_leaked_by_naive_utc_cut") or 0) for r in records),
        "clean_linked": len(linked),
    }
    diffs = ["%s: declarado %r vs calculado %r" % (k, totals.get(k), v)
             for k, v in calc.items() if totals.get(k) != v]
    add("manifiesto.totales", "ok" if not diffs else "falla",
        "; ".join(diffs) or "los %d totales cierran" % len(calc))

    rotos = [r.get("file") for r in records
             if int(r.get("rows_keep") or 0) + int(r.get("rows_drop") or 0)
             != int(r.get("rows_total") or -1)]
    add("manifiesto.particion", "ok" if not rotos else "falla",
        "keep+drop != total en: %s" % (", ".join(str(x) for x in rotos[:5]) or "ninguno"))

    # -- 2. inventario del arbol
    esperados: dict[str, tuple[str, dict]] = {}
    for r in records:
        esperados[basename_of(r.get("output"))] = ("salida", r)
    for r in linked:
        esperados[str(r.get("file"))] = ("enlace", r)

    if not os.path.isdir(out_base):
        add("inventario.faltantes", "falla", "out_base inexistente: %s" % out_base)
        add("inventario.extras", "falla", "out_base inexistente")
        add("inventario.sin_ambiguedad", "falla", "out_base inexistente")
        found_pq, otros = {}, []
    else:
        found_pq, otros = walk_files(out_base)
        faltantes = sorted(n for n in esperados if n not in found_pq)
        extras = sorted(n for n in found_pq if n not in esperados)
        ambiguos = sorted(n for n, ps in found_pq.items() if len(ps) > 1)
        add("inventario.faltantes", "ok" if not faltantes else "falla",
            "esperados %d, encontrados %d, faltan: %s"
            % (len(esperados), len(found_pq), ", ".join(faltantes[:5]) or "ninguno"))
        add("inventario.extras", "ok" if not extras else "falla",
            "parquets no declarados en el manifiesto: %s"
            % (", ".join(extras[:5]) or "ninguno"))
        add("inventario.sin_ambiguedad", "ok" if not ambiguos else "falla",
            "mismo nombre en dos carpetas: %s"
            % (", ".join(ambiguos[:5]) or "ninguno"))

    add("inventario.no_parquet", "skip",
        "%d archivos no-parquet en el arbol%s"
        % (len(otros),
           (": " + ", ".join(os.path.basename(p) for p in otros[:5])) if otros else ""))

    malas_carpetas = []
    for r in records:
        name = basename_of(r.get("output"))
        rutas = found_pq.get(name) or []
        if len(rutas) == 1:
            decl = parent_of(r.get("output"))
            real = os.path.basename(os.path.dirname(rutas[0]))
            if decl != real:
                malas_carpetas.append("%s: declarada %s vs encontrada %s" % (name, decl, real))
    add("inventario.carpetas", "ok" if not malas_carpetas else "falla",
        "; ".join(malas_carpetas[:5]) or "cada salida esta en la carpeta declarada")

    # -- 3. digestos de las salidas re-cortadas (chequeo central)
    problemas, verificados, bytes_salida = [], 0, 0
    for r in records:
        name = basename_of(r.get("output"))
        rutas = found_pq.get(name) or []
        if len(rutas) != 1:
            problemas.append("%s: %s" % (name, "ausente" if not rutas else "ambiguo"))
            continue
        try:
            size, sha, blob, _st = digests_of(rutas[0])
        except OSError as exc:
            problemas.append("%s: ilegible (%s)" % (name, exc))
            continue
        if size != int(r.get("output_bytes") or -1):
            problemas.append("%s: bytes %d != %r" % (name, size, r.get("output_bytes")))
        elif sha != r.get("output_sha256"):
            problemas.append("%s: sha256 %s... != %s..."
                             % (name, sha[:12], str(r.get("output_sha256"))[:12]))
        elif blob != r.get("output_blob_sha1"):
            problemas.append("%s: blob %s... != %s..."
                             % (name, blob[:12], str(r.get("output_blob_sha1"))[:12]))
        else:
            verificados += 1
            bytes_salida += size
    add("salidas.digestos", "ok" if not problemas else "falla",
        ("bytes+sha256+blob recalculados y coincidentes en %d/%d salidas (%s B)"
         % (verificados, len(records), fmt(bytes_salida))) if not problemas
        else "; ".join(problemas[:5]))

    # -- 4. digestos de los limpios enlazados
    probl_link, ok_link, bytes_link = [], 0, 0
    for r in linked:
        name = str(r.get("file"))
        rutas = found_pq.get(name) or []
        if len(rutas) != 1:
            probl_link.append("%s: %s" % (name, "ausente" if not rutas else "ambiguo"))
            continue
        if r.get("sha256_matches_index") is not True:
            probl_link.append("%s: sha256_matches_index=%r"
                              % (name, r.get("sha256_matches_index")))
            continue
        try:
            size, sha, _blob, _st = digests_of(rutas[0])
        except OSError as exc:
            probl_link.append("%s: ilegible (%s)" % (name, exc))
            continue
        if isinstance(r.get("bytes"), int) and size != r["bytes"]:
            probl_link.append("%s: bytes %d != %d" % (name, size, r["bytes"]))
        elif sha != r.get("sha256"):
            probl_link.append("%s: sha256 %s... != %s..."
                              % (name, sha[:12], str(r.get("sha256"))[:12]))
        else:
            ok_link += 1
            bytes_link += size
    add("enlaces.digestos", "ok" if not probl_link else "falla",
        ("sha256 recalculado y coincidente en %d/%d limpios (%s B)"
         % (ok_link, len(linked), fmt(bytes_link))) if not probl_link
        else "; ".join(probl_link[:5]))

    # -- 5. las fuentes inmutables siguen intactas DESPUES de escribir
    if base is None or not os.path.isdir(str(base)):
        add("fuente.intacta", "skip", "sin --base valido: no se re-hashea el origen")
        add("enlaces.inodo", "skip", "sin --base valido: no se comparan inodos")
        src_pq = {}
    else:
        src_pq, _ = walk_files(str(base))
        probl_src, ok_src = [], 0
        for r in records:
            name = basename_of(r.get("source")) or str(r.get("file"))
            rutas = src_pq.get(name) or []
            sellado = r.get("source_sha256_index") or r.get("source_sha256")
            if len(rutas) != 1:
                probl_src.append("%s: %s en el origen"
                                 % (name, "ausente" if not rutas else "ambiguo"))
                continue
            if not hash_sources:
                ok_src += 1
                continue
            try:
                _size, sha, _blob, _st = digests_of(rutas[0])
            except OSError as exc:
                probl_src.append("%s: ilegible (%s)" % (name, exc))
                continue
            if sha != sellado:
                probl_src.append("%s: sha256 %s... != sellado %s..."
                                 % (name, sha[:12], str(sellado)[:12]))
            else:
                ok_src += 1
        detalle = ("%d/%d fuentes con sha256 identico al sellado" % (ok_src, len(records))
                   if hash_sources else
                   "%d/%d fuentes presentes (--no-source-hash: sin re-hashear)"
                   % (ok_src, len(records)))
        add("fuente.intacta", "ok" if not probl_src else "falla",
            detalle if not probl_src else "; ".join(probl_src[:5]))

        # -- 6. enlaces duros: mismo inodo que el origen?
        compartidos, copias, sin_par = 0, [], 0
        for r in linked:
            name = str(r.get("file"))
            a = (found_pq.get(name) or [None])[0]
            b = (src_pq.get(name) or [None])[0]
            if not a or not b:
                sin_par += 1
                continue
            sa, sb = os.stat(a), os.stat(b)
            if (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino):
                compartidos += 1
            else:
                copias.append(name)
        declara_hardlink = any(r.get("method") == "hardlink" for r in linked)
        if copias and declara_hardlink:
            add("enlaces.inodo", "aviso",
                "%d de %d limpios declarados hardlink NO comparten inodo (son copias): %s"
                % (len(copias), len(linked), ", ".join(copias[:5])))
        else:
            add("enlaces.inodo", "ok",
                "%d/%d limpios comparten inodo con el origen%s (hardlink: el arbol no es "
                "una copia fisica; un write in-place mutaria el origen inmutable)"
                % (compartidos, len(linked), ", %d sin par" % sin_par if sin_par else ""))

    # -- 7. permisos de escritura
    escribibles = []
    total_pq = sum(len(v) for v in found_pq.values())
    for rutas in found_pq.values():
        for p in rutas:
            try:
                if is_writable_mode(os.stat(p)):
                    escribibles.append(os.path.basename(p))
            except OSError:
                pass
    add("proteccion.escritura", "ok" if not escribibles else "aviso",
        "ningun parquet tiene bit de escritura" if not escribibles
        else "%d/%d parquets con permiso de escritura (con inodos compartidos, un write "
             "in-place contamina el origen): %s"
             % (len(escribibles), total_pq, ", ".join(sorted(escribibles)[:5])))

    # -- 8. prueba fisica de cero holdout
    boundary = (index.get("cut") or {}).get("session_open_utc_ns")
    medidos: dict[str, tuple] = {}
    if not want_maxts:
        add("holdout.max_ts_fisico", "skip",
            "sin --maxts: no se midio %s en disco" % TS_COLUMN)
    elif not isinstance(boundary, int):
        add("holdout.max_ts_fisico", "falla",
            "el manifiesto no declara cut.session_open_utc_ns")
    else:
        try:
            import pyarrow.parquet as pq  # type: ignore
            import pyarrow.compute as pc  # type: ignore
        except Exception as exc:  # pragma: no cover
            add("holdout.max_ts_fisico", "skip", "pyarrow no disponible (%s)" % exc)
        else:
            ilegibles = []
            for name, rutas in sorted(found_pq.items()):
                if len(rutas) != 1:
                    continue
                try:
                    medidos[name] = max_ts_of(pq, pc, rutas[0])
                except Exception as exc:
                    ilegibles.append("%s: %s" % (name, exc))
            violaciones = evaluate_max_ts(medidos, boundary) + ilegibles
            add("holdout.max_ts_fisico", "ok" if not violaciones else "falla",
                "max(%s) < apertura de sesion (%d) en %d/%d parquets, medido en disco"
                % (TS_COLUMN, boundary, len(medidos), total_pq) if not violaciones
                else "; ".join(violaciones[:5]))

    # -- 9. columnas redundantes delatadas por digestos identicos
    pares = None
    con_digestos = 0
    for r in records:
        dc = r.get("digest_columns") or {}
        if not dc:
            continue
        con_digestos += 1
        por_digesto: dict[str, list[str]] = {}
        for col, dig in dc.items():
            por_digesto.setdefault(dig, []).append(col)
        local = set()
        for cols in por_digesto.values():
            if len(cols) > 1:
                cols = sorted(cols)
                for i in range(len(cols)):
                    for j in range(i + 1, len(cols)):
                        local.add((cols[i], cols[j]))
        pares = local if pares is None else (pares & local)
    pares = sorted(pares or ())
    if not con_digestos:
        add("columnas.digestos_duplicados", "skip", "el manifiesto no trae digest_columns")
    elif not pares:
        add("columnas.digestos_duplicados", "ok",
            "ningun par de columnas comparte digesto en los %d archivos" % con_digestos)
    else:
        add("columnas.digestos_duplicados", "aviso",
            "%d par(es) con digesto identico en los %d archivos -> columna redundante: %s"
            % (len(pares), con_digestos, "; ".join("%s == %s" % p for p in pares)))

    # -- 10. verificacion directa de esos pares con pyarrow (opcional)
    if not want_columns:
        add("columnas.verificado_pyarrow", "skip", "sin --columns")
    elif not pares:
        add("columnas.verificado_pyarrow", "skip", "no hay pares que verificar")
    else:
        try:
            import pyarrow.parquet as pq2  # type: ignore
        except Exception as exc:  # pragma: no cover
            add("columnas.verificado_pyarrow", "skip", "pyarrow no disponible (%s)" % exc)
        else:
            malos, comprobados = [], 0
            for r in records:
                name = basename_of(r.get("output"))
                rutas = found_pq.get(name) or []
                if len(rutas) != 1:
                    continue
                try:
                    pf = pq2.ParquetFile(rutas[0])
                    for a, b in pares:
                        iguales = True
                        for batch in pf.iter_batches(batch_size=262144, columns=[a, b]):
                            if not batch.column(0).equals(batch.column(1)):
                                iguales = False
                                break
                        comprobados += 1
                        if not iguales:
                            malos.append("%s: %s != %s" % (name, a, b))
                except Exception as exc:
                    malos.append("%s: %s" % (name, exc))
            add("columnas.verificado_pyarrow", "ok" if not malos else "falla",
                "%d comparaciones columna-a-columna confirman igualdad byte a byte"
                % comprobados if not malos else "; ".join(malos[:5]))

    # -- veredicto
    familias = set()
    for c in checks:
        if c.level == "falla":
            familias.add(FAIL_FAMILY.get(c.cid, "FAIL_MANIFIESTO"))
        elif c.level == "aviso":
            familias.add(WARN_FAMILY.get(c.cid, "WARN_COLUMNAS"))
    verdict = "PASS"
    for v in VERDICT_PRECEDENCE:
        if v == "PASS" or v in familias:
            verdict = v
            break

    resumen = {
        "tool": TOOL_ID,
        "schema_version": SCHEMA_VERSION,
        "out_base": out_base,
        "base": base,
        "salidas_verificadas": verificados,
        "limpios_verificados": ok_link,
        "bytes_verificados": bytes_salida + bytes_link,
        "parquets_con_ts_medido": len(medidos),
        "pares_columnas_redundantes": [list(p) for p in pares],
        "ok": sum(1 for c in checks if c.level == "ok"),
        "fallas": sum(1 for c in checks if c.level == "falla"),
        "avisos": sum(1 for c in checks if c.level == "aviso"),
        "skips": sum(1 for c in checks if c.level == "skip"),
        "verdict": verdict,
    }
    return checks, resumen


def render(checks, resumen) -> str:
    marca = {"ok": "[ok   ]", "falla": "[FALLA]", "aviso": "[aviso]", "skip": "[skip ]"}
    lineas = ["%s %-34s %s" % (marca[c.level], c.cid, c.detail) for c in checks]
    lineas.append("")
    lineas.append("%d chequeos ok  |  %d fallas  |  %d avisos  |  %d omitidos"
                  % (resumen["ok"], resumen["fallas"], resumen["avisos"], resumen["skips"]))
    lineas.append("bytes re-hasheados: %s" % fmt(resumen["bytes_verificados"]))
    lineas.append("VEREDICTO: %s" % resumen["verdict"])
    return "\n".join(lineas)


# ------------------------------------------------------------------ selftest


def _write(path: str, data: bytes, ro: bool = True) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.chmod(path, 0o644)
        os.remove(path)
    with open(path, "wb") as fh:
        fh.write(data)
    os.chmod(path, 0o444 if ro else 0o644)


def _fixture(root: str, variant: str = "sano"):
    base = os.path.join(root, "nt8")
    out = os.path.join(root, "v2")
    src_cut = os.path.join(base, "6B_parquet", "6B_09-26_ticks.parquet")
    src_ok = os.path.join(base, "6B_parquet", "6B_03-26_ticks.parquet")
    out_cut = os.path.join(out, "6B_parquet", "6B_09-26_ticks.parquet")
    out_ok = os.path.join(out, "6B_parquet", "6B_03-26_ticks.parquet")

    _write(src_cut, b"FUENTE-6B-09-26\n" * 64)
    _write(src_ok, b"LIMPIO-6B-03-26\n" * 64)
    _write(out_cut, b"RECORTADO-6B-09-26\n" * 40)
    os.makedirs(os.path.dirname(out_ok), exist_ok=True)
    os.link(src_ok, out_ok)

    sz_o, sha_o, blob_o, _ = digests_of(out_cut)
    sz_l, sha_l, _b, _ = digests_of(out_ok)
    _sz_s, sha_s, _b2, _ = digests_of(src_cut)

    index = {
        "tool": EXPECTED_RECUT_TOOL,
        "schema_version": 1,
        "precheck": False,
        "base": base,
        "out_base": out,
        "cut": {"session_open_utc_ns": 1782856800000000000},
        "files": [{
            "file": "6B_09-26_ticks.parquet",
            "asset": "6B",
            "source": src_cut,
            "source_sha256": sha_s,
            "source_sha256_index": sha_s,
            "output": out_cut,
            "status": "RECUT",
            "rows_total": 1000,
            "rows_keep": 400,
            "rows_drop": 600,
            "rows_leaked_by_naive_utc_cut": 7,
            "output_sha256": sha_o,
            "output_blob_sha1": blob_o,
            "output_bytes": sz_o,
            "digest_columns": {"ts_utc_ns": "a" * 64, "ts_local_ns": "b" * 64,
                               "sequence": "c" * 64, "source_row": "d" * 64},
        }],
        "linked_clean": [{
            "file": "6B_03-26_ticks.parquet",
            "asset": "6B",
            "method": "hardlink",
            "sha256": sha_l,
            "sha256_matches_index": True,
            "bytes": sz_l,
        }],
        "quarantine": [],
        "problems": [],
        "totals": {"targets": 1, "recut": 1, "rows_total_source": 1000, "rows_keep": 400,
                   "rows_drop": 600, "rows_leaked_by_naive_utc_cut": 7, "clean_linked": 1},
        "verdict": "PASS",
    }

    if variant == "precheck":
        index["precheck"] = True
    elif variant == "falta_salida":
        os.chmod(out_cut, 0o644)
        os.remove(out_cut)
    elif variant == "tamano":
        index["files"][0]["output_bytes"] = sz_o + 1
    elif variant == "sha_salida":
        index["files"][0]["output_sha256"] = "0" * 64
    elif variant == "blob_salida":
        index["files"][0]["output_blob_sha1"] = "0" * 40
    elif variant == "fuente_cambiada":
        _write(src_cut, b"FUENTE-MUTADA\n" * 64)
    elif variant == "extra":
        _write(os.path.join(out, "6B_parquet", "6B_99-99_ticks.parquet"), b"intruso\n")
    elif variant == "ambiguo":
        _write(os.path.join(out, "otra", "6B_09-26_ticks.parquet"),
               b"RECORTADO-6B-09-26\n" * 40)
    elif variant == "enlace_roto":
        os.remove(out_ok)
        shutil.copy2(src_ok, out_ok)
    elif variant == "escribible":
        os.chmod(out_cut, 0o644)
    elif variant == "columnas_dup":
        index["files"][0]["digest_columns"] = {
            "ts_utc_ns": "a" * 64, "ts_local_ns": "a" * 64,
            "sequence": "c" * 64, "source_row": "c" * 64,
        }
    elif variant == "totales":
        index["totals"]["rows_keep"] = 1
    elif variant == "estado":
        index["files"][0]["status"] = "PRECHECK_ONLY"
    elif variant == "particion":
        index["files"][0]["rows_drop"] = 599
        index["totals"]["rows_drop"] = 599
    elif variant == "carpeta":
        index["files"][0]["output"] = os.path.join(out, "OTRA", "6B_09-26_ticks.parquet")
    elif variant == "veredicto":
        index["verdict"] = "ABSTAIN_BACKEND"
    elif variant == "limpio_ausente":
        os.remove(out_ok)
    elif variant == "sin_frontera":
        index["cut"] = {}
    elif variant != "sano":
        raise ValueError("variante desconocida: %s" % variant)

    return index, base, out


def _limpiar(root: str) -> None:
    for dirpath, _d, files in os.walk(root):
        for fn in files:
            try:
                os.chmod(os.path.join(dirpath, fn), 0o644)
            except OSError:
                pass
    shutil.rmtree(root, ignore_errors=True)


def selftest() -> int:
    casos = [
        ("S1  sano", "sano", "PASS", False),
        ("S2  manifiesto de precheck", "precheck", "FAIL_MANIFIESTO", False),
        ("S3  salida ausente", "falta_salida", "FAIL_FALTANTE", False),
        ("S4  bytes declarados != reales", "tamano", "FAIL_DIGESTO", False),
        ("S5  sha256 de salida distinto", "sha_salida", "FAIL_DIGESTO", False),
        ("S6  blob sha1 de salida distinto", "blob_salida", "FAIL_DIGESTO", False),
        ("S7  fuente mutada tras escribir", "fuente_cambiada", "FAIL_FUENTE", False),
        ("S8  parquet intruso en el arbol", "extra", "FAIL_INVENTARIO", False),
        ("S9  mismo nombre en dos carpetas", "ambiguo", "FAIL_INVENTARIO", False),
        ("S10 hardlink roto (es copia)", "enlace_roto", "WARN_ENLACES", False),
        ("S11 parquet con permiso de escritura", "escribible", "WARN_ESCRITURA", False),
        ("S12 columnas con digesto duplicado", "columnas_dup", "WARN_COLUMNAS", False),
        ("S13 totales que no cierran", "totales", "FAIL_MANIFIESTO", False),
        ("S14 estado que no es RECUT", "estado", "FAIL_MANIFIESTO", False),
        ("S15 keep+drop != total", "particion", "FAIL_MANIFIESTO", False),
        ("S16 salida en otra carpeta", "carpeta", "FAIL_INVENTARIO", False),
        ("S17 veredicto de origen no PASS", "veredicto", "FAIL_MANIFIESTO", False),
        ("S18 limpio enlazado ausente", "limpio_ausente", "FAIL_FALTANTE", False),
        ("S19 --maxts sin frontera en el manifiesto", "sin_frontera", "FAIL_HOLDOUT", True),
    ]
    fallas, ok = 0, 0
    for etiqueta, variant, esperado, maxts in casos:
        root = tempfile.mkdtemp(prefix="vtree_")
        try:
            index, base, out = _fixture(root, variant)
            _checks, resumen = verify(index, out, base=base, hash_sources=True,
                                      want_maxts=maxts)
            got = resumen["verdict"]
            if got != esperado:
                print("FALLA %s -> esperaba %s, obtuve %s" % (etiqueta, esperado, got))
                fallas += 1
            else:
                ok += 1
        finally:
            _limpiar(root)

    # el caso sano no debe emitir ninguna falla ni aviso, y debe re-hashear ambas clases
    root = tempfile.mkdtemp(prefix="vtree_")
    try:
        index, base, out = _fixture(root, "sano")
        checks, resumen = verify(index, out, base=base, hash_sources=True)
        if resumen["fallas"] or resumen["avisos"]:
            print("FALLA S1 sin fallas ni avisos -> %d fallas, %d avisos"
                  % (resumen["fallas"], resumen["avisos"]))
            for c in checks:
                if c.level in ("falla", "aviso"):
                    print("       %s %s: %s" % (c.level, c.cid, c.detail))
            fallas += 1
        else:
            ok += 1
        if resumen["salidas_verificadas"] != 1 or resumen["limpios_verificados"] != 1:
            print("FALLA S1 no re-hasheo las dos clases de archivo")
            fallas += 1
        else:
            ok += 1
    finally:
        _limpiar(root)

    # logica pura de la prueba fisica de holdout (no necesita pyarrow)
    frontera = 1782856800000000000
    if evaluate_max_ts({"a": (1, frontera - 1), "b": (1, frontera - 1000)}, frontera):
        print("FALLA S20 max_ts por debajo de la frontera no debe violar")
        fallas += 1
    else:
        ok += 1
    viol = evaluate_max_ts({"a": (1, frontera - 1), "b": (1, frontera)}, frontera)
    if len(viol) != 1 or "HOLDOUT EN EL ARBOL" not in viol[0]:
        print("FALLA S21 max_ts == frontera debe violar (el corte es estricto)")
        fallas += 1
    else:
        ok += 1
    if len(evaluate_max_ts({"a": (1, None)}, frontera)) != 1:
        print("FALLA S22 max_ts nulo debe contar como violacion (fail-closed)")
        fallas += 1
    else:
        ok += 1

    print("self-test: %d fallas, %d chequeos ok" % (fallas, ok))
    return 1 if fallas else 0


# ---------------------------------------------------------------------- main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Verifica el arbol fisico re-cortado contra su manifiesto.")
    ap.add_argument("--recut", help="ruta a recut_index.json de la corrida real (precheck=false)")
    ap.add_argument("--out-base", help="raiz del arbol re-cortado (por defecto: out_base del manifiesto)")
    ap.add_argument("--base", help="raiz del arbol de origen (por defecto: base del manifiesto)")
    ap.add_argument("--no-source-hash", action="store_true",
                    help="no re-hashear las fuentes (solo comprobar presencia)")
    ap.add_argument("--maxts", action="store_true",
                    help="medir max(ts_utc_ns) en disco y probar que no hay holdout (pyarrow)")
    ap.add_argument("--columns", action="store_true",
                    help="verificar con pyarrow las columnas con digesto duplicado")
    ap.add_argument("--json-out", help="escribir el informe en JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.recut:
        ap.error("--recut es obligatorio (o usa --selftest)")

    with open(args.recut, "r", encoding="utf-8") as fh:
        index = json.load(fh)

    out_base = args.out_base or index.get("out_base")
    base = args.base or index.get("base")
    if not out_base:
        ap.error("el manifiesto no declara out_base: pasa --out-base")

    print(TOOL_ID)
    print("  recut    = %s" % args.recut)
    print("  out_base = %s" % out_base)
    print("  base     = %s" % (base or "(omitido)"))
    print("")

    checks, resumen = verify(index, out_base, base=base,
                             hash_sources=not args.no_source_hash,
                             want_columns=args.columns,
                             want_maxts=args.maxts)
    print(render(checks, resumen))

    if args.json_out:
        payload = dict(resumen)
        payload["checks"] = [{"id": c.cid, "level": c.level, "detail": c.detail} for c in checks]
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        print("informe: %s" % args.json_out)

    return 1 if resumen["verdict"].startswith("FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
