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

#: WARMUP — POR CONTEO ACOTADO DE BARRAS, no por sesión.
#: La versión 1 usaba "la primera sesión completa". Medido contra el defecto
#: REAL de v2.2/K=25 (485 mismatch en las barras 1..2571 de 12.395), esa regla
#: borraba entre el 48 % y el 80 % de la evidencia y dejaba el veredicto a
#: 0,05 puntos del umbral con 4 sesiones: el resultado dependía de cuántas
#: sesiones tuviera la captura, no del defecto. Eso no es un criterio.
#:
#: Regla nueva, derivada del MECANISMO y no de los datos: el warm-up es la
#: región donde el ancla todavía no está establecida. El propio log lo declara:
#: `ANCLAJE_VERIFICADO` aparece recién cuando el anclaje acotado tuvo éxito
#: (`BigTrap2.cs:453`). Se excluyen las barras ANTERIORES al primer
#: `ANCLAJE_VERIFICADO`, con un tope duro como red de seguridad.
#: H2 (auditoria A2): el DENOMINADOR de P1/P2 NO EXISTIA en el log.
#: `ANCLAJE_VERIFICADO` se emite dentro de `if (!anclado)` (BigTrap2.cs:423) y
#: `anclado` solo vuelve a false en el roll de sesion (298) o cuando el OHLCV no
#: cierra (481): es UNA VEZ POR SESION, un marcador de ANCLAJE, no de barra
#: procesada. `nPares` contaba bien (398, 470) pero nunca se emitia.
#: Con K=25 sobre 12.395 barras y 4-5 sesiones el denominador valia 4-5, los
#: mismatch casi nunca caian sobre una barra de anclaje y P1/P2 daba PASS por
#: construccion. Mismo modo de falla que B2, por otra puerta.
#: v2.4 del .cs emite `BARRA_PROCESADA` por barra, SOLO en el camino de tick.
EVENTO_BARRA_PROCESADA = "BARRA_PROCESADA"
WARMUP_MODO = "hasta_primera_barra_procesada"
WARMUP_TOPE_BARRAS = 500        # red de seguridad; si se supera => ABSTAIN

#: MATURITY TAIL — declarado como DECISIÓN NUEVA post-oráculo.
#: `edgelab/bridge/parity.py` define su frontera de madurez por `max_age_bars`
#: (ciclo de vida de ZONAS). Acá el objeto es otro: una barra atribuida no tiene
#: ciclo de vida. Se excluyen las últimas `TAIL_BARRAS` barras porque su bloque
#: puede estar truncado por dónde terminó la captura. No hay antecedente que
#: reconcilie; queda registrado como decisión nueva.
TAIL_BARRAS = 0                 # 0 = sin exclusión de cola por defecto

#: frontera de sesión CME ETH: 17:00 hora de Chicago. El EventLog trae
#: `Time[0]` en la hora del CHART, así que hay que CONVERTIR antes de aplicar
#: el corte. En v1 esto no se hacía: se leía `d.hour` directo y `SESION_TZ`
#: entraba al hash sin que ningún código lo usara — el hash certificaba un
#: parámetro inerte. La tz del chart es argumento OBLIGATORIO, sin default.
SESION_HORA_CORTE = 17
SESION_TZ = "America/Chicago"

#: DENOMINADOR de P1/P2: barras PROCESADAS (con `BARRA_PROCESADA`, `.cs:481`)
#: del interior que NO abstuvieron. Una barra con `ANCLAJE_AMBIGUO` no fue
#: procesada: no entra al numerador ni al denominador, y se reporta aparte.
#: Denominador 0 => ABSTAIN, nunca PASS.
#: H-GROK-3: este comentario decía "con `ANCLAJE_VERIFICADO`", que es la
#: semántica vieja — la que produjo H2.
DENOMINADOR = "barras_procesadas_interior"

#: P3 sólo se pronuncia si el emisor entregó los CINCO pares. Con la regla vieja
#: bastaba `open_blk`/`open_bar` presentes, así que un mismatch con OHLC igual y
#: sin volumen daba PASS: certificaba igualdad OHLC-**V** sin haber visto la V
#: (H-GPT-6). Completitud del esquema = precondición del veredicto.
P3_PARES_REQUERIDOS = ("open_blk", "open_bar", "close_blk", "close_bar",
                       "low_blk", "low_bar", "high_blk", "high_bar",
                       "vol_blk", "vol_bar")

#: umbral de P1/P2 (del JSON pre-registrado)
UMBRAL_MISMATCH = 0.01

CONTRATO_SHA_CAMPOS = dict(
    p5_meta_ignorable=sorted(P5_META_IGNORABLE),
    p5_payload_ignorable=sorted(P5_PAYLOAD_IGNORABLE),
    p5_tipos_economicos=list(P5_TIPOS_ECONOMICOS),
    evento_barra_procesada=EVENTO_BARRA_PROCESADA,
    warmup_modo=WARMUP_MODO,
    warmup_tope_barras=WARMUP_TOPE_BARRAS,
    tail_barras=TAIL_BARRAS,
    sesion_hora_corte=SESION_HORA_CORTE,
    sesion_tz=SESION_TZ,
    denominador=DENOMINADOR,
    umbral_mismatch=UMBRAL_MISMATCH,
    p3_pares_requeridos=list(P3_PARES_REQUERIDOS),
    resolucion_obligatoria=True,
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

def sesion_de(ts_iso, tz_chart):
    """Índice de sesión CME ETH. CONVIERTE la tz del chart a America/Chicago.

    B1 de la auditoría: v1 leía `d.hour` directo del timestamp del chart. Con
    chart en ART y junio en CDT la frontera caía 2 h antes. `SESION_TZ` estaba
    en el hash del contrato sin que ningún código lo usara.

    `tz_chart` es obligatorio y sin default: si no se puede determinar, el modo
    devuelve ABSTAIN antes de llegar acá.
    """
    import datetime as _dt
    from zoneinfo import ZoneInfo
    s = ts_iso.strip()
    if s.endswith("Z"):
        s = s[:-1]
    try:
        d = _dt.datetime.fromisoformat(s)
    except ValueError:
        d = _dt.datetime.fromisoformat(s[:26])
    if d.tzinfo is None:
        d = d.replace(tzinfo=ZoneInfo(tz_chart))
    ct = d.astimezone(ZoneInfo(SESION_TZ))
    return ct.date().toordinal() + (1 if ct.hour >= SESION_HORA_CORTE else 0)


# ---------------------------------------------------------------------------
# MODO p5-time
# ---------------------------------------------------------------------------

def modo_p5(hist_path, nuevo_path, resolucion_esperada=None):
    """P5: el time:1 nuevo debe ser bit-idéntico al histórico salvo la metadata
    expresamente permitida. Cualquier otra diferencia = FAIL. Formatos no
    comparables = ABSTAIN, nunca PASS."""
    a = leer_log(hist_path)
    b = leer_log(nuevo_path)
    dif = []
    # menor 5 + H-GPT-2: sin esto nada impedia compararle un Tick25 contra el
    # historico de minuto y llamarlo P5. El "menor 5" agrego la OPCION pero la
    # dejo con `default=None` y guardada por `if resolucion_esperada:`, o sea
    # que omitirla salteaba el chequeo entero: agregar la opcion no hizo
    # obligatoria la precondicion.
    if not resolucion_esperada:
        return _res("p5-time", "ABSTAIN",
                    ["resolucion no acreditada: es precondicion, no opcion"], a, b)
    for lado, lg in (("historico", a), ("nuevo", b)):
        if resolucion_esperada.lower() not in os.path.basename(lg["path"]).lower():
            return _res("p5-time", "ABSTAIN",
                        ["el log %s (%s) no declara la resolucion %r"
                         % (lado, os.path.basename(lg["path"]), resolucion_esperada)], a, b)

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

def modo_p1p2(path, tz_chart, resolucion_esperada=None, exigir_version=None):
    """P1/P2/P3/P4 leyendo el EventLog de NT8. `tz_chart` OBLIGATORIO (B1)."""
    lg = leer_log(path)
    ev = lg["eventos"]
    if not ev:
        return _res("p1-p2-tick", "ABSTAIN", ["log sin eventos"], lg)
    if lg["meta"] is None:
        # N3: sin `# meta` no se puede verificar procedencia => ABSTAIN, nunca medir
        return _res("p1-p2-tick", "ABSTAIN",
                    ["el log no tiene linea `# meta`: procedencia no verificable"], lg)
    if not tz_chart:
        return _res("p1-p2-tick", "ABSTAIN", ["tz del chart no determinada"], lg)
    # H-GPT-2: la precondicion no puede ser opcional. Agregar la opcion no la
    # hacia obligatoria: `if resolucion_esperada:` dejaba pasar el None.
    if not resolucion_esperada:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["resolucion no acreditada: es precondicion, no opcion"], lg)
    base = os.path.basename(path)
    if resolucion_esperada.lower() not in base.lower():
        return _res("p1-p2-tick", "ABSTAIN",
                    ["el archivo %r no corresponde a la resolucion %r"
                     % (base, resolucion_esperada)], lg)
    # H-GROK-4 / H-KIMI-7 (K5): procedencia por VERSION. Un log 2.3 que trae
    # BARRA_PROCESADA -evento que solo existe en v2.4- se medía igual. Escenario
    # real: v2.4 mal instalada, o binario viejo cacheado por NT8.
    if exigir_version:
        v = (lg["meta"] or {}).get("version")
        if v != exigir_version:
            return _res("p1-p2-tick", "ABSTAIN",
                        ["procedencia: el log declara version=%r y el paquete "
                         "congelado exige %r" % (v, exigir_version)], lg)

    def bar_de(e):
        try:
            return int(e["campos"].get("bar"))
        except (TypeError, ValueError):
            return None

    # --- WARMUP por conteo acotado (B2): barras anteriores a la primera
    # BARRA_PROCESADA. H-GROK-3: este comentario decia "primer ANCLAJE_VERIFICADO",
    # que es la semantica VIEJA (una vez por sesion) y es justo el bug H2. Un
    # mensaje con la semantica vieja invita a reintroducirlo.
    primera_ok = None
    for e in ev:
        if e["tipo"] == EVENTO_BARRA_PROCESADA:
            primera_ok = bar_de(e)
            break
    if primera_ok is None:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["ningun %s en el log. Si es v2.3 o anterior, el log NO tiene "
                     "denominador y P1/P2 no es medible: hace falta v2.4."
                     % EVENTO_BARRA_PROCESADA], lg)
    if primera_ok > WARMUP_TOPE_BARRAS:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["la primera %s cae en la barra %d, sobre el tope de "
                     "warmup declarado (%d)"
                     % (EVENTO_BARRA_PROCESADA, primera_ok, WARMUP_TOPE_BARRAS)], lg)
    barras = [b for b in (bar_de(e) for e in ev) if b is not None]
    bmax = max(barras) if barras else 0
    lo_int, hi_int = primera_ok, bmax - TAIL_BARRAS

    def interior(b):
        return b is not None and lo_int <= b <= hi_int

    # PASADA 1: construir `amb` completo. v2.3 del analizador evaluaba `b in amb`
    # en la MISMA pasada en que `amb` se llenaba, asi que si el evento economico
    # precedia al ANCLAJE_AMBIGUO de esa barra la violacion de P4 se perdia.
    amb = {bar_de(e) for e in ev if e["tipo"] == "ANCLAJE_AMBIGUO" and bar_de(e) is not None}

    procesadas, mism = set(), set()
    mism_todas = set()
    cand0 = candN = 0
    anclajes = set()
    amb_con_economico = set()
    ohlc_desig_proc = set()
    excl_warmup = excl_tail = 0
    por_sesion = {}
    for e in ev:
        b = bar_de(e)
        t = e["tipo"]
        if b is not None and t in (EVENTO_BARRA_PROCESADA, "ANCLAJE_VERIFICADO",
                                   "ANCLAJE_AMBIGUO", "FOOTPRINT_MISMATCH"):
            ses = sesion_de(e["ts"], tz_chart)
            por_sesion.setdefault(ses, Counter())[t] += 1
        if t == EVENTO_BARRA_PROCESADA and b is not None:
            procesadas.add(b)
        elif t == "ANCLAJE_VERIFICADO" and b is not None:
            anclajes.add(b)
        elif t == "ANCLAJE_AMBIGUO" and b is not None:
            try:
                c = int(e["campos"].get("candidatos"))
                if c == 0:
                    cand0 += 1
                elif c > 1:
                    candN += 1
            except (TypeError, ValueError):
                pass
        elif t == "FOOTPRINT_MISMATCH" and b is not None:
            mism_todas.add(b)
            if interior(b):
                mism.add(b)
            elif b < lo_int:
                excl_warmup += 1
            else:
                excl_tail += 1
        elif t in P5_TIPOS_ECONOMICOS and b is not None and b in amb:
            amb_con_economico.add(b)

    # --- P4 (B3): la abstencion se VERIFICA, no se asume.
    # v1 hacia `proc -= amb`, que ocultaba justo la violacion que P4 vigila.
    # P4: violacion = barra que abstuvo y IGUAL fue procesada, o que abstuvo y
    # siguio emitiendo eventos economicos. Se verifica, no se asume.
    p4_violaciones = sorted((amb & procesadas) | amb_con_economico)
    p4_estado = "PASS" if not p4_violaciones else "FAIL"

    # --- denominador: verificadas del interior que NO abstuvieron
    proc = {b for b in procesadas if interior(b)} - amb
    denom = len(proc)
    mism_int = mism & proc

    # --- P3 (B4): veredicto propio, poblacion explicita = pares PROCESADOS
    for e in ev:
        if e["tipo"] != "FOOTPRINT_MISMATCH":
            continue
        b = bar_de(e)
        if b not in proc:
            continue
        cm = e["campos"]
        for a_, b_ in (("open_blk", "open_bar"), ("close_blk", "close_bar"),
                       ("low_blk", "low_bar"), ("high_blk", "high_bar"),
                       ("vol_blk", "vol_bar")):
            if a_ in cm and b_ in cm and cm[a_] != cm[b_]:
                ohlc_desig_proc.add(b)
                break
    # menor 4: en el camino de TIEMPO, `VerificarOHLC` no emite vol_blk/vol_bar y
    # el chequeo de abajo exige que AMBOS esten -> P3 daria PASS vacuo. Se declara
    # como NO_APLICA en vez de aprobar por ausencia de evidencia.
    # H-GPT-6: exigir los CINCO pares, no solo `open`. Con la regla vieja, un
    # mismatch con OHLC igual y SIN vol_blk/vol_bar daba p3_estado=PASS: estaba
    # certificando igualdad OHLC-V sin haber visto nunca la V. La completitud del
    # esquema es precondicion del veredicto, no un detalle del emisor.
    #
    # HALLAZGO PROPIO (no esta en ninguna de las tres iteraciones): hay DOS
    # emisores de FOOTPRINT_MISMATCH con ESQUEMAS DISTINTOS.
    #   .cs:541 (ReportarMismatch)  -> los 5 pares, CON vol_blk/vol_bar
    #   .cs:601 (rotura de bloque)  -> solo 4 pares, SIN volumen
    # GPT-6 dijo "ReportarMismatch parece emitir los cinco pares": es cierto y
    # es incompleto. Un log real trae los dos esquemas mezclados, asi que la
    # completitud se evalua POR EVENTO PROCESADO, no por el log entero.
    p3_completos, p3_incompletos = set(), set()
    for e in ev:
        if e["tipo"] != "FOOTPRINT_MISMATCH":
            continue
        b = bar_de(e)
        if b not in proc:
            continue
        (p3_completos if all(k in e["campos"] for k in P3_PARES_REQUERIDOS)
         else p3_incompletos).add(b)
    if p3_incompletos:
        # Basta UN par procesado sin el esquema entero para que P3 no pueda
        # certificar la poblacion. NO_APLICA, nunca PASS por ausencia de
        # evidencia. Si NO hubo ningun mismatch procesado, PASS es legitimo y no
        # vacuo: el mismatch es la evidencia de FALLA, y su ausencia sobre una
        # poblacion no vacia SI es evidencia de igualdad.
        p3_estado = "NO_APLICA"
    else:
        p3_estado = "PASS" if not ohlc_desig_proc else "FAIL"

    # --- CONTABILIDAD (H-KIMI-3, K2). Toda tasa declara su poblacion, y todo
    # contador que acompana a una tasa comparte su poblacion con ella. El
    # contrato v3 declaro el "menor 3" corregido habiendo corregido SOLO la
    # tasa: `footprint_mismatch_total` seguia contando barras que la tasa no
    # cuenta. Misma familia que H2 y B1: un numero cuyo denominador nadie puede
    # reconstruir.
    barras_todas = {b for b in (bar_de(e) for e in ev) if b is not None}
    tasa_total = (len(mism_todas & procesadas) / len(procesadas)
                  if procesadas else float("nan"))
    contab = dict(
        # universo
        barras_totales_en_log=len(barras_todas),
        barras_en_warmup=len({b for b in barras_todas if b < lo_int}),
        barras_en_tail=len({b for b in barras_todas if b > hi_int}),
        # poblacion "procesadas" — la de `tasa_mismatch_total`
        barras_procesadas_total=len(procesadas),
        mismatch_total_en_procesadas=len(mism_todas & procesadas),
        tasa_mismatch_total=tasa_total,
        # poblacion "todas las barras del log" — NO es el numerador de ninguna tasa
        mismatch_total_todas_las_barras=len(mism_todas),
        mismatch_excluidos_por_warmup_barras=len({b for b in mism_todas if b < lo_int}),
        mismatch_excluidos_por_tail_barras=len({b for b in mism_todas if b > hi_int}),
        # eventos, no barras (menor 2)
        excluidos_por_warmup_eventos=excl_warmup,
        excluidos_por_tail_eventos=excl_tail,
        anclajes_verificados=len(anclajes),
        barras_ambiguas=len(amb),
        barras_ambiguas_interior=len({b for b in amb if interior(b)}),
        candidatos_cero=cand0, candidatos_multiples=candN,
        p3_estado=p3_estado,
        p3_pares_procesados_sin_igualdad_ohlcv=len(ohlc_desig_proc),
        # dos emisores, dos esquemas: se publica cuantos pares procesados NO
        # traen los cinco, para que la cobertura de P3 sea visible y no haya que
        # inferirla del veredicto.
        p3_pares_procesados_esquema_completo=len(p3_completos),
        p3_pares_procesados_esquema_incompleto=len(p3_incompletos),
        p4_estado=p4_estado, p4_violaciones=p4_violaciones[:50],
        nota_poblaciones=(
            "mismatch_total_todas_las_barras NO es el numerador de "
            "tasa_mismatch_total. El numerador de esa tasa es "
            "mismatch_total_en_procesadas, sobre barras_procesadas_total."),
        desglose_por_sesion={str(k): dict(v) for k, v in sorted(por_sesion.items())})

    # H-GPT-1: `verif` NO estaba definido en el modulo -> esta rama tiraba
    # NameError, y el test que la nombraba abstenia antes de alcanzarla. Ademas
    # publicaba menos campos que la salida normal, asi que el consumidor no podia
    # distinguir un ABSTAIN de una salida truncada (H-KIMI, contabilidad).
    comunes = dict(tz_chart=tz_chart,
                   warmup_primera_barra_procesada=primera_ok,
                   interior_barras=[lo_int, hi_int],
                   barras_procesadas_interior=denom,
                   footprint_mismatch_interior=len(mism_int),
                   **contab)
    if denom == 0:
        return _res("p1-p2-tick", "ABSTAIN",
                    ["denominador 0: ninguna barra procesada en el interior"], lg,
                    tasa_mismatch_interior=float("nan"), **comunes)

    tasa_int = len(mism_int) / denom

    difs = []
    if tasa_int > UMBRAL_MISMATCH:
        difs.append("P1/P2: mismatch interior %.4f%% > umbral %.2f%%"
                    % (100 * tasa_int, 100 * UMBRAL_MISMATCH))
    if p3_estado == "FAIL":
        difs.append("P3: %d par(es) PROCESADO(s) sin igualdad OHLCV" % len(ohlc_desig_proc))
    if p4_estado == "FAIL":
        difs.append("P4: %d barra(s) ambigua(s) que igual fueron procesadas: %s"
                    % (len(p4_violaciones), p4_violaciones[:10]))
    estado = "PASS" if not difs else "FAIL"

    return _res("p1-p2-tick", estado, difs, lg,
                tasa_mismatch_interior=tasa_int, **comunes)


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
    if not resolucion_esperada:
        return _res("p6-file", "ABSTAIN",
                    ["resolucion no acreditada: es precondicion, no opcion"], lg)
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
    a.add_argument("--resolucion", required=True,
                   help="OBLIGATORIA (H-GPT-2). p.ej. Minute1. Sin esto se compara un Tick25 contra minuto.")

    b = sub.add_parser("p1-p2-tick", help="atribución sobre el EventLog de NT8")
    b.add_argument("--log", required=True)
    b.add_argument("--resolucion", required=True, help="OBLIGATORIA. p.ej. Tick25 / Tick10 / Minute1")
    b.add_argument("--exigir-version", dest="exigir_version", default=None,
                   help="modo captura (K5): meta con otra version => ABSTAIN de procedencia")
    b.add_argument("--tz-chart", dest="tz_chart", required=True,
                   help="OBLIGATORIO, sin default: tz del CHART de NT8")

    c = sub.add_parser("p6-file", help="integridad del archivo de EventLog")
    c.add_argument("--log", required=True)
    c.add_argument("--resolucion", required=True, help="OBLIGATORIA")

    # `--out` va en CADA subparser, no en el principal: argparse sólo acepta
    # opciones del parser padre ANTES del subcomando, y la forma natural de
    # invocarlo es `pred004_analyze.py p6-file --log X --out Y`.
    for p in (a, b, c):
        p.add_argument("--out", default=None, help="ruta del JSON de salida")
    args = ap.parse_args(argv)

    if args.modo == "p5-time":
        res = modo_p5(args.historico, args.nuevo, args.resolucion)
    elif args.modo == "p1-p2-tick":
        res = modo_p1p2(args.log, args.tz_chart, args.resolucion, args.exigir_version)
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
    # menor 6: abstencion NO es aprobacion. Todo el diseno insiste en eso; el
    # exit code las hacia indistinguibles.
    #   0 = PASS · 1 = FAIL · 2 = ABSTAIN
    return {"PASS": 0, "FAIL": 1}.get(res["estado"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
