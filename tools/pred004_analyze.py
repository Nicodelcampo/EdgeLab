#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pred004_analyze.py — el instrumento que mide PRED-004 COMO FUE ESCRITA.

## Por qué existe

El preflight (`e8f187a`) proponía medir PRED-004 con `run_nt8_bridge.py` y
`correr_gates.py`. **Los dos miden otra cosa.** Verificado en el código:

1. `run_nt8_bridge.py:233` hace `oracle.parse_nt8_log(...)` + `match_zones(...)`:
   compara **zonas del kernel Python contra zonas de NT8**. Pasarle el EventLog
   nuevo como `--oracle` mide paridad Python↔NT8 v2.3. **No compara el EventLog
   histórico v2.1 contra el nuevo v2.3**, que es lo que P5 exige.

2. `correr_gates.py:55` sí referencia el CSV histórico, pero lo consume por el
   mismo matcher, con tolerancia temporal, geometría y ciclo de vida. Eso no es
   igualdad bit a bit.

3. El `FOOTPRINT_MISMATCH` que reporta `run_nt8_bridge.py:300` viene de
   `bars.p1a_gate(ticks, bars, fps)` — **los tres argumentos son objetos
   Python**. `footprint_volume_mismatches` compara Σ(ask+bid) del footprint
   Python contra el volumen de la barra Python: **consistencia interna del lado
   Python**. No toca la atribución de NT8.

**Hay DOS cosas distintas llamadas `FOOTPRINT_MISMATCH`** y el propio repo lo
dice en `edgelab/bridge/bars.py:116`: *"no lo mide FOOTPRINT_MISMATCH (que
compara NT8 contra sí mismo)"*. La colisión de nombres es la razón por la que el
instrumento equivocado habría devuelto un número con la etiqueta correcta.

| nombre | quién lo emite | qué compara | ¿mide P1/P2? |
|---|---|---|---|
| `FOOTPRINT_MISMATCH` (EventLog) | `BigTrap2.cs:529,589` | bloque atribuido vs barra primaria, **dentro de NT8** | **SÍ** |
| `FOOTPRINT_MISMATCH` (p1a_gate) | `bars.py:221` | footprint Python vs volumen de barra Python | no |

Este módulo lee **el EventLog de NT8 directamente**. No usa el matcher, no usa
el kernel Python, no abre outcomes.

## Formato del EventLog (BigTrap2.cs v2.3, verificado en el .cs)

    # meta indicator=BigTrap2,version=2.3,attribution=...,instrument=...
    {seq}|{Time[0]:o}|{TYPE}|{k=v;k=v;...}

`LogEvent` (línea 879): `"{0}|{1:o}|{2}|{3}", eventSeq++, Time[0], type, payload`.

Tipos emitidos por v2.3 (los diez): `ANCLAJE_AMBIGUO`, `ANCLAJE_VERIFICADO`,
`ERROR`, `FOOTPRINT_MISMATCH`, `SESION_RESINCRONIZADA`, `TRAP`, `ZONE_CREATED`,
`ZONE_EXPIRED`, `ZONE_INVALIDATED`, `ZONE_TOUCHED`.

Nombre de archivo (línea 852):
`BarsPeriod.BarsPeriodType.ToString() + BarsPeriod.Value`
→ para barras de minuto es **`Minute1`**, NO `time1`. El preflight decía
`__time1.csv` y era incorrecto: la API de NT8 identifica minuto por
`BarsPeriodType.Minute`. Este módulo **nunca asume el nombre**: se le pasa la
ruta real y verifica la resolución contra la metadata.

Salida: JSON content-addressed (incluye el sha256 de cada entrada). El veredicto
no se redacta a mano.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# CONTRATO CONGELADO — se fija ANTES de producir ningún log nuevo.
# Cambiar cualquiera de estas constantes después de una captura invalida la
# medición: el porcentaje se podría mover sin tocar el .cs.
# ---------------------------------------------------------------------------

#: metadata que PUEDE diferir entre el log histórico v2.1 y el nuevo v2.3 sin
#: que P5 falle. Lista CERRADA. Cualquier otra clave que difiera => FAIL.
P5_META_IGNORABLE = frozenset({
    "version",          # 2.1 -> 2.3 es justamente lo que se está probando
    "attribution",      # clave nueva en v2.3, ausente en v2.1
    "anchor",           # idem
})

#: campos del payload que NO participan de la comparación económica de P5.
#: Vacío a propósito: en v2.3 el payload de los eventos económicos no incorpora
#: campos de diagnóstico. Si alguna vez hiciera falta agregar uno, se agrega
#: ACÁ y en el mismo commit que lo introduce, nunca después de ver un log.
P5_PAYLOAD_IGNORABLE = frozenset()

#: tipos de evento con contenido ECONÓMICO. Son los que P5 compara.
#: Los diagnósticos quedan fuera porque v2.3 los introduce o los cambia por
#: diseño (es el cambio autorizado), y compararlos haría fallar P5 por el
#: cambio que P5 no está evaluando.
P5_TIPOS_ECONOMICOS = ("TRAP", "ZONE_CREATED", "ZONE_TOUCHED",
                       "ZONE_INVALIDATED", "ZONE_EXPIRED")

#: WARMUP — regla del contrato de paridad (`docs/nt8_indicator_parity_contract.md`:
#: "Ninguna barra de la primera sesión posterior a la carga del chart entra a una
#: comparación de paridad"). Operacionalizado: TODA barra cuya sesión sea la
#: PRIMERA presente en el log queda excluida.
WARMUP_SESIONES = 1

#: MATURITY TAIL — simétrico y por el mismo motivo estructural: la ÚLTIMA sesión
#: del log está truncada por donde terminó la captura, así que sus bloques de
#: atribución pueden estar incompletos por la ventana, no por el kernel.
TAIL_SESIONES = 1

#: frontera de sesión CME ETH: 17:00 hora de Chicago. Un evento a las >= 17:00
#: pertenece a la sesión que cierra al día siguiente. Misma convención que
#: `edgelab/bridge/bars.py:session_ids`.
SESION_HORA_CORTE = 17
SESION_TZ = "America/Chicago"

#: DENOMINADOR de la tasa interior de P1/P2:
#:   barras PROCESADAS (atribuidas) dentro del interior.
#: Una barra con ANCLAJE_AMBIGUO **no fue procesada**: no entra al numerador ni
#: al denominador, y se reporta por separado como abstención. Contarla como
#: procesada convertiría una abstención fail-closed en un acierto.
#: Denominador 0 => ABSTAIN, nunca PASS.
DENOMINADOR = "barras_procesadas_interior"

#: umbral de P1/P2 (del JSON pre-registrado)
UMBRAL_MISMATCH = 0.01

CONTRATO_SHA_CAMPOS = dict(
    p5_meta_ignorable=sorted(P5_META_IGNORABLE),
    p5_payload_ignorable=sorted(P5_PAYLOAD_IGNORABLE),
    p5_tipos_economicos=list(P5_TIPOS_ECONOMICOS),
    warmup_sesiones=WARMUP_SESIONES,
    tail_sesiones=TAIL_SESIONES,
    sesion_hora_corte=SESION_HORA_CORTE,
    sesion_tz=SESION_TZ,
    denominador=DENOMINADOR,
    umbral_mismatch=UMBRAL_MISMATCH,
)


def contrato_sha() -> str:
    """Hash del contrato congelado. Si cambia entre dos corridas, los números
    no son comparables y el reporte lo tiene que gritar."""
    s = json.dumps(CONTRATO_SHA_CAMPOS, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# parseo
# ---------------------------------------------------------------------------

_RE_META = re.compile(r"^#\s*meta\s+(.*)$")


class LogInvalido(Exception):
    """El archivo no se puede interpretar como un EventLog de una sola corrida."""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_meta(linea):
    m = _RE_META.match(linea)
    if not m:
        return None
    out = {}
    for parte in m.group(1).split(","):
        if "=" in parte:
            k, v = parte.split("=", 1)
            out[k.strip()] = v.strip()
        elif parte.strip():
            out[parte.strip()] = ""
    return out


def parse_payload(s):
    out = {}
    for parte in (s or "").split(";"):
        if "=" in parte:
            k, v = parte.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def leer_log(path):
    """Devuelve dict(meta, eventos, metas_encontradas, reinicios_seq, sha256).

    NO levanta si el archivo tiene defectos: los reporta. Es el modo `p6-file`
    el que decide si un defecto es FAIL.
    """
    with open(path, "rb") as fh:
        crudo = fh.read()
    texto = crudo.decode("utf-8", errors="replace")
    metas, eventos, malformadas = [], [], 0
    for ln in texto.splitlines():
        if not ln.strip():
            continue
        if ln.startswith("#"):
            mm = parse_meta(ln)
            if mm is not None:
                metas.append(mm)
            continue
        partes = ln.split("|", 3)
        if len(partes) < 4:
            malformadas += 1
            continue
        try:
            seq = int(partes[0])
        except ValueError:
            malformadas += 1
            continue
        eventos.append(dict(seq=seq, ts=partes[1], tipo=partes[2],
                            payload=partes[3], campos=parse_payload(partes[3])))
    reinicios = 0
    for i, e in enumerate(eventos):
        if e["seq"] == 0 and i > 0:
            reinicios += 1
    if eventos and eventos[0]["seq"] == 0:
        reinicios += 1          # el inicio legítimo cuenta como "un inicio"
    return dict(path=os.path.abspath(path), sha256=hashlib.sha256(crudo).hexdigest(),
                bytes=len(crudo), meta=(metas[0] if metas else None),
                metas_encontradas=len(metas), eventos=eventos,
                inicios_seq=reinicios, malformadas=malformadas)


# ---------------------------------------------------------------------------
# sesiones
# ---------------------------------------------------------------------------

def sesion_de(ts_iso):
    """Índice de sesión CME ETH a partir del timestamp ISO del evento.

    El EventLog trae `Time[0]` en la hora del CHART. Se interpreta con la
    convención de `bars.py:session_ids`: trade-date = día del cierre, y un
    evento a las >= 17:00 pertenece a la sesión que cierra al día siguiente.
    """
    import datetime as _dt
    s = ts_iso.strip()
    if s.endswith("Z"):
        s = s[:-1]
    if "+" in s[10:]:
        s = s[:s.rindex("+")]
    try:
        d = _dt.datetime.fromisoformat(s)
    except ValueError:
        d = _dt.datetime.fromisoformat(s[:26])
    dia = d.date().toordinal()
    return dia + (1 if d.hour >= SESION_HORA_CORTE else 0)


# ---------------------------------------------------------------------------
# MODO p5-time
# ---------------------------------------------------------------------------

def modo_p5(hist_path, nuevo_path):
    """P5: el time:1 nuevo debe ser bit-idéntico al histórico salvo la metadata
    expresamente permitida. Cualquier otra diferencia = FAIL. Formatos no
    comparables = ABSTAIN, nunca PASS."""
    a = leer_log(hist_path)
    b = leer_log(nuevo_path)
    dif = []

    if a["meta"] is None or b["meta"] is None:
        return _res("p5-time", "ABSTAIN", ["alguno de los dos logs no tiene línea # meta: formatos no comparables"],
                    a, b)

    # --- metadata: sólo puede diferir lo de la lista cerrada
    claves = set(a["meta"]) | set(b["meta"])
    for k in sorted(claves):
        va, vb = a["meta"].get(k), b["meta"].get(k)
        if va != vb and k not in P5_META_IGNORABLE:
            dif.append("meta[%s]: %r vs %r" % (k, va, vb))

    ea = [e for e in a["eventos"] if e["tipo"] in P5_TIPOS_ECONOMICOS]
    eb = [e for e in b["eventos"] if e["tipo"] in P5_TIPOS_ECONOMICOS]

    if not ea or not eb:
        return _res("p5-time", "ABSTAIN",
                    ["uno de los logs no tiene eventos económicos (%d vs %d): no comparable" % (len(ea), len(eb))],
                    a, b)

    if len(ea) != len(eb):
        dif.append("cantidad de eventos económicos: %d vs %d" % (len(ea), len(eb)))

    for i, (x, y) in enumerate(zip(ea, eb)):
        if x["tipo"] != y["tipo"]:
            dif.append("evento %d: tipo %s vs %s" % (i, x["tipo"], y["tipo"]))
        if x["ts"] != y["ts"]:
            dif.append("evento %d (%s): ts %s vs %s" % (i, x["tipo"], x["ts"], y["ts"]))
        if x["seq"] != y["seq"]:
            dif.append("evento %d (%s): seq %d vs %d" % (i, x["tipo"], x["seq"], y["seq"]))
        ca, cb = x["campos"], y["campos"]
        for k in sorted(set(ca) | set(cb)):
            if k in P5_PAYLOAD_IGNORABLE:
                continue
            if ca.get(k) != cb.get(k):
                dif.append("evento %d (%s) campo %s: %r vs %r" % (i, x["tipo"], k, ca.get(k), cb.get(k)))
        if len(dif) > 200:
            dif.append("... (truncado a 200 diferencias)")
            break

    estado = "PASS" if not dif else "FAIL"
    return _res("p5-time", estado, dif, a, b,
                n_eventos_economicos=[len(ea), len(eb)])


def _res(modo, estado, difs, *logs, **extra):
    d = dict(modo=modo, estado=estado, contrato_sha=contrato_sha(),
             contrato=CONTRATO_SHA_CAMPOS, diferencias=difs,
             n_diferencias=len([x for x in difs if not x.startswith("...")]),
             entradas=[dict(path=l["path"], sha256=l["sha256"], bytes=l["bytes"],
                            eventos=len(l["eventos"]), meta=l["meta"]) for l in logs])
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# MODO p1-p2-tick
# ---------------------------------------------------------------------------

def modo_p1p2(path, resolucion_esperada=None):
    """P1/P2: mide la atribución LEYENDO EL EVENTLOG DE NT8, no el kernel Python.

    Numerador  : FOOTPRINT_MISMATCH en barras procesadas del interior.
    Denominador: barras PROCESADAS del interior (contrato: `DENOMINADOR`).
    Abstención : ANCLAJE_AMBIGUO, contado y reportado APARTE, fuera de ambos.
    """
    lg = leer_log(path)
    ev = lg["eventos"]
    if not ev:
        return _res("p1-p2-tick", "ABSTAIN", ["log sin eventos"], lg)

    if resolucion_esperada and lg["meta"]:
        # la resolución no viene en la meta: se verifica contra el nombre real
        # del archivo, que el .cs compone con BarsPeriodType+Value.
        base = os.path.basename(path)
        if resolucion_esperada.lower() not in base.lower():
            return _res("p1-p2-tick", "ABSTAIN",
                        ["el archivo %r no corresponde a la resolución esperada %r"
                         % (base, resolucion_esperada)], lg)

    sesiones = sorted({sesion_de(e["ts"]) for e in ev})
    if len(sesiones) <= WARMUP_SESIONES + TAIL_SESIONES:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["sólo %d sesión(es) en el log: warmup(%d)+tail(%d) no dejan interior"
                     % (len(sesiones), WARMUP_SESIONES, TAIL_SESIONES)], lg)
    interior = set(sesiones[WARMUP_SESIONES:len(sesiones) - TAIL_SESIONES])

    def bar_de(e):
        b = e["campos"].get("bar")
        try:
            return int(b)
        except (TypeError, ValueError):
            return None

    proc, mism, amb, cand0, candN, ohlc_desigual = set(), set(), set(), 0, 0, 0
    fuera_interior = Counter()
    for e in ev:
        ses = sesion_de(e["ts"])
        b = bar_de(e)
        clave = (ses, b)
        dentro = ses in interior
        t = e["tipo"]
        if t == "ANCLAJE_VERIFICADO":
            if dentro and b is not None:
                proc.add(clave)
            elif b is not None:
                fuera_interior["ANCLAJE_VERIFICADO"] += 1
        elif t == "ANCLAJE_AMBIGUO":
            if dentro and b is not None:
                amb.add(clave)
            c = e["campos"].get("candidatos")
            try:
                c = int(c)
                if c == 0:
                    cand0 += 1
                elif c > 1:
                    candN += 1
            except (TypeError, ValueError):
                pass
        elif t == "FOOTPRINT_MISMATCH":
            if dentro and b is not None:
                mism.add(clave)
            elif b is not None:
                fuera_interior["FOOTPRINT_MISMATCH"] += 1
            cm = e["campos"]
            for a_, b_ in (("open_blk", "open_bar"), ("close_blk", "close_bar"),
                           ("low_blk", "low_bar"), ("high_blk", "high_bar"),
                           ("vol_blk", "vol_bar")):
                if a_ in cm and b_ in cm and cm[a_] != cm[b_]:
                    ohlc_desigual += 1
                    break

    # una barra ambigua NO fue procesada: no puede estar en el denominador
    proc -= amb
    mism_interior = mism & proc
    denom = len(proc)

    if denom == 0:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["denominador 0: ninguna barra procesada en el interior"], lg,
                    sesiones_totales=len(sesiones), sesiones_interior=len(interior),
                    barras_ambiguas=len(amb))

    tasa = len(mism_interior) / denom
    estado = "PASS" if tasa <= UMBRAL_MISMATCH else "FAIL"
    difs = [] if estado == "PASS" else [
        "FOOTPRINT_MISMATCH interior %.4f%% > umbral %.2f%%" % (100 * tasa, 100 * UMBRAL_MISMATCH)]
    return _res("p1-p2-tick", estado, difs, lg,
                sesiones_totales=len(sesiones), sesiones_interior=len(interior),
                barras_procesadas_interior=denom,
                footprint_mismatch_interior=len(mism_interior),
                tasa_mismatch_interior=tasa,
                barras_ambiguas_interior=len(amb),
                candidatos_cero=cand0, candidatos_multiples=candN,
                pares_procesados_sin_igualdad_ohlcv=ohlc_desigual,
                excluidos_por_warmup_o_tail=dict(fuera_interior))


# ---------------------------------------------------------------------------
# MODO p6-file
# ---------------------------------------------------------------------------

def modo_p6(path, resolucion_esperada=None):
    """P6: una corrida por archivo, meta propia, seq inicia una vez."""
    lg = leer_log(path)
    fallas = []
    if lg["metas_encontradas"] != 1:
        fallas.append("líneas `# meta`: %d (debe ser exactamente 1)" % lg["metas_encontradas"])
    if lg["inicios_seq"] != 1:
        fallas.append("inicios de seq: %d (debe ser exactamente 1) -> evidencia de append"
                      % lg["inicios_seq"])
    seqs = [e["seq"] for e in lg["eventos"]]
    if seqs and seqs != sorted(seqs):
        fallas.append("la secuencia no es monótona: hay reinicios o desorden")
    if lg["malformadas"]:
        fallas.append("filas malformadas: %d" % lg["malformadas"])
    if resolucion_esperada:
        base = os.path.basename(path)
        if resolucion_esperada.lower() not in base.lower():
            fallas.append("el nombre %r no declara la resolución esperada %r "
                          "(el .cs compone BarsPeriodType+Value)" % (base, resolucion_esperada))
    estado = "PASS" if not fallas else "FAIL"
    return _res("p6-file", estado, fallas, lg,
                metas=lg["metas_encontradas"], inicios_seq=lg["inicios_seq"],
                eventos=len(lg["eventos"]), malformadas=lg["malformadas"],
                tipos=dict(Counter(e["tipo"] for e in lg["eventos"])))


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Analizador de PRED-004 sobre EventLogs de BigTrap2 v2.3")
    sub = ap.add_subparsers(dest="modo", required=True)

    a = sub.add_parser("p5-time", help="histórico v2.1 vs nuevo v2.3, bit-identidad")
    a.add_argument("--historico", required=True)
    a.add_argument("--nuevo", required=True)

    b = sub.add_parser("p1-p2-tick", help="atribución sobre el EventLog de NT8")
    b.add_argument("--log", required=True)
    b.add_argument("--resolucion", default=None, help="p.ej. Tick25 / Tick10 / Minute1")

    c = sub.add_parser("p6-file", help="integridad del archivo de EventLog")
    c.add_argument("--log", required=True)
    c.add_argument("--resolucion", default=None)

    # `--out` va en CADA subparser, no en el principal: argparse sólo acepta
    # opciones del parser padre ANTES del subcomando, y la forma natural de
    # invocarlo es `pred004_analyze.py p6-file --log X --out Y`.
    for p in (a, b, c):
        p.add_argument("--out", default=None, help="ruta del JSON de salida")
    args = ap.parse_args(argv)

    if args.modo == "p5-time":
        res = modo_p5(args.historico, args.nuevo)
    elif args.modo == "p1-p2-tick":
        res = modo_p1p2(args.log, args.resolucion)
    else:
        res = modo_p6(args.log, args.resolucion)

    txt = json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True)
    res["resultado_sha256"] = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    txt = json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(txt)
    print(txt)
    return 0 if res["estado"] in ("PASS", "ABSTAIN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
