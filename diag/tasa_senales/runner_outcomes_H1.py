# -*- coding: utf-8 -*-
"""Paso 6 — runner de outcomes de H1. **Dos fases, y la razón es la falsación.**

Ejecuta `docs/predictions/E-R1_v0.3.1_SELLO_2026-08-09.md`, el único documento
vigente. Los `v0.3` son historia y **no deben ejecutarse**.

## Por qué dos fases y no una

La regla del sello es dura y es la correcta: **después del primer outcome no se
retoca nada; si aparece un defecto, H1 muere.** Un runner mal especificado no
falsea la hipótesis — la mata por un error mío.

Entonces todo lo que se pueda verificar **sin mirar un solo resultado** tiene que
verificarse antes:

```
FASE 1  poblacion   outcomes_accessed = false
        reproduce 755 eventos y f = 2,11/sesion, publicados en el sello §1.1
        un desvio aca es un defecto DEL RUNNER, y H1 no corre riesgo

FASE 2  outcomes    outcomes_accessed = true   <- PRIMERA VEZ EN EL PROYECTO
        solo se habilita con --fase outcomes, y solo tiene sentido si la 1 cerro
```

Después de la fase 2 la puerta se cierra: un defecto encontrado ahí ya no se
repara.

## Lo que NO se reimplementa

La población sale de las **mismas primitivas** que `f_ambos_filtros.py`, no de una
copia: `extract_first_touch_events`, `decongest_first_touch_events` y su propio
`k_excursion`. Reimplementar la población sería fabricar la posibilidad de medir
otra cosa con el mismo nombre.

## La trampa de dirección, verificada en la fuente y no recordada

```
is_bull = True -> trapped_buyers -> agresion COMPRADORA que quedo por ENCIMA
                  del close (bigtrap2.py:265) -> zona ARRIBA -> operacion CORTA
```

El flag nombra **quién quedó atrapado**, no la dirección del trade. Invertirlo
invierte la hipótesis entera y **nada en el resultado lo delataría**: la
expectativa cambia de signo y sigue pareciendo un número legítimo.

## Frontera del firewall

Universo de la puerta research, `max ts <= 2026-06-30`. El holdout
`2026-07-01 -> 12-31` **no se lee ni se escanea**. Que este módulo toque outcomes
NO lo autoriza a tocar el holdout: son dos permisos distintos.

Uso:
    ./.venv/Scripts/python.exe diag/tasa_senales/runner_outcomes_H1.py
    ./.venv/Scripts/python.exe diag/tasa_senales/runner_outcomes_H1.py --fase outcomes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, pd, ticks_mod,
)
from diag.tasa_senales.f_ambos_filtros import k_excursion  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402
from edgelab.research.first_touch_decongestion import (  # noqa: E402
    FIRST_TOUCH_SEP_MINUTES, decongest_first_touch_events,
)
from edgelab.research.first_touch_population import (  # noqa: E402
    extract_first_touch_events,
)

SCHEMA_VERSION = "runner_outcomes_H1_v1"
INDICADOR = "BigTrap2"
T_OBJETIVO = 34

#: Del sello §2. La friccion se resta DENTRO de cada evento, no del lado derecho
#: de la comparacion: el umbral economico del estimando neto es 0.
FRICCION_TICKS = 2.768

#: Lo que la fase 1 tiene que reproducir. Publicado en el sello §1.1. No es una
#: meta a alcanzar: es un CONTROL. Si no da, el defecto es de este runner.
#:
#: LOS DOS SON CONTROLES DISTINTOS Y YO LOS CONFUNDI. El sello dice, en dos
#: renglones contiguos, "eventos con excursion valida 776 -> 755" y "f (orden B)
#: 2,13 -> 2,11". Puse 755 como poblacion orden B, y no lo es: 755 son los
#: eventos con excursion ANTES de descongestionar. Orden B son 424, y de ahi
#: sale f = 424/201 = 2,11.
#:
#: Es el error contra el que advierte el propio sello §7 -- tomar algo por cierto
#: sin abrir la fuente-, cometido sobre el renglon de al lado. Lo atrapo la fase
#: 1, que es exactamente para lo que existe. Ahora se controlan LAS DOS etapas,
#: que ademas es mas fuerte: verifica la poblacion antes y despues del filtro.
CONTROL_CON_EXCURSION = 755
CONTROL_ORDEN_B = 424
CONTROL_F = 2.11


def identidad_entorno():
    en_venv = sys.prefix != sys.base_prefix
    try:
        venv_repo = Path(sys.prefix).resolve() == (REPO_PATH / ".venv").resolve()
    except Exception:                                      # noqa: BLE001
        venv_repo = False
    paq = {}
    for n in ("numpy", "pandas", "pyarrow"):
        try:
            paq[n] = __import__(n).__version__
        except Exception as e:                             # noqa: BLE001
            paq[n] = "NO_IMPORTABLE: %s" % type(e).__name__
    return dict(python=sys.version.split()[0], ejecutable=str(Path(sys.executable)),
                en_venv=en_venv, es_el_venv_del_repo=venv_repo,
                plataforma=platform.platform(), paquetes=paq)



#: `end_reason` que el kernel puede emitir. Cualquier otro valor es un caso que
#: nadie previo, y se reporta en vez de caer en el `else`.
RAZONES_CONOCIDAS = ("close_through", "close_through_gap", "max_age",
                     "first_touch", "max_touches", None)


def resolver_salida(e, z, bar_end, n_barras):
    """Barra y motivo de salida. **Sin leer un solo precio.**

    Es la MISMA funcion que usa la fase de outcomes. Validarla con una copia no
    probaria nada: lo que se verifica tiene que ser lo que despues se ejecuta.

    Devuelve `(bar_salida, motivo, diagnostico)`. `bar_salida` es `None` si el
    evento no es ejecutable, y `diagnostico` dice por que -- nunca se descarta
    en silencio.
    """
    fb = int(e["first_touch_bar"])
    if not (0 <= fb < n_barras):
        return None, None, "barra_de_entrada_fuera_de_rango"

    kind = e.get("kind")
    if kind not in ("trapped_buyers", "trapped_sellers"):
        return None, None, "kind_desconocido:%s" % kind

    razon = (z or {}).get("end_reason")
    if razon not in RAZONES_CONOCIDAS:
        return None, None, "end_reason_no_previsto:%s" % razon

    # FIN DE SESION CT: ultima barra cuyo cierre cae en el mismo dia de sesion.
    dia = session_date_ct(e["first_touch_ms"])
    fin_sesion = n_barras - 1
    for j in range(fb, n_barras):
        if session_date_ct(int(bar_end[j]) // 1_000_000) != dia:
            fin_sesion = j - 1
            break
    if fin_sesion < fb:
        return None, None, "fin_de_sesion_anterior_a_la_entrada"

    bar_ct = None
    if razon in ("close_through", "close_through_gap") and (z or {}).get("ended_ms"):
        bar_ct = int(np.searchsorted(bar_end, int(z["ended_ms"]) * 1_000_000,
                                     side="left"))
        if bar_ct < fb:
            # CloseThrough ANTES del primer toque: la zona murio antes de que el
            # evento existiera. No se silencia -- se cuenta y se descarta.
            return None, None, "close_through_anterior_a_la_entrada"
        if bar_ct >= n_barras:
            bar_ct = None

    if bar_ct is not None and bar_ct <= fin_sesion:
        return bar_ct, "close_through", None
    return fin_sesion, "fin_de_sesion", None


def poblacion_y_outcomes(archivo, fechas, fase):
    """Población orden B del sello, y —sólo si `con_outcomes`— su resultado.

    La población se construye con las MISMAS primitivas que `f_ambos_filtros.py`.
    El bloque de outcomes está separado a propósito: en fase 1 no se ejecuta una
    sola línea suya.
    """
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_c = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
             + pd.Timedelta(days=1))
    fin = min(fin_c.tz_convert("UTC"), corte_del_sello())

    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
        return dict(estado="ABSTAIN", motivo="`sequence` no es orden total")

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    # `close_t`, NO `close_ticks`: es el nombre real del campo de BarSeries
    # (bars.py:38). Un arreglo anterior no matcheo y quedo la referencia muerta
    # -- la fase 1 lo habia detectado y el arreglo nunca llego al archivo-.
    bar_close = np.asarray(b.close_t).astype(np.float64) \
        if hasattr(b, "close_t") else None
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    eventos = extract_first_touch_events(r)
    setf = set(fechas)
    eventos = [e for e in eventos if session_date_ct(e["first_touch_ms"]) in setf]

    geo = {z["id"]: z for z in (r.get("zones") or [])
           if isinstance(z.get("id"), str) and z.get("top") is not None}

    n_sin_geo = n_sin_tramo = 0
    for e in eventos:
        e["excursion_ok"] = False
        z = geo.get(e["zone_id"])
        if z is None:
            n_sin_geo += 1
            continue
        cb = e["created_bar"]
        if not (0 <= cb < len(bar_end)):
            n_sin_tramo += 1
            continue
        lo_t, hi_t = z["bottom"] / tk.tick_size, z["top"] / tk.tick_size
        i0 = int(np.searchsorted(ts, int(bar_end[int(cb)]), side="right"))
        fin_ms = z.get("ended_ms")
        i1 = min(int(np.searchsorted(ts, int(fin_ms) * 1_000_000, side="right"))
                 if fin_ms else len(ts), len(ts))
        k = k_excursion(px, lo_t, hi_t, i0, i1, T_OBJETIVO)
        if k is None or k == 0:
            continue
        bar_de_k = int(np.searchsorted(bar_end, ts[i0 + k], side="left"))
        e["excursion_ok"] = bool(e["first_touch_bar"] > bar_de_k)

    # ORDEN B del sello: exigir validez, DESPUES decongestionar.
    con_exc = [e for e in eventos if e["excursion_ok"]]
    dB = decongest_first_touch_events(con_exc, session_date_of_ms=session_date_ct,
                                      sep_minutes=FIRST_TOUCH_SEP_MINUTES)
    sel = dB["events"]

    out = dict(estado="OK", sesiones=len(fechas), primeros_toques=len(eventos),
               con_excursion=len(con_exc), poblacion_orden_B=len(sel),
               zonas_sin_geometria=n_sin_geo, zonas_sin_tramo=n_sin_tramo)
    if fase == "poblacion":
        return out

    # ------------------------------------------------ FASE SALIDAS y OUTCOMES
    # `salidas` recorre la MISMA resolucion que `outcomes` y NO lee un precio.
    from collections import Counter
    motivos, diags = Counter(), Counter()
    orden_ok = True
    filas = []
    for e in sel:
        z = geo.get(e["zone_id"])
        bs, motivo, diag = resolver_salida(e, z, bar_end, len(bar_end))
        if bs is None:
            diags[diag] += 1
            continue
        fb = int(e["first_touch_bar"])
        if bs < fb:
            orden_ok = False
            diags["bar_salida_menor_que_entrada"] += 1
            continue
        motivos[motivo] += 1
        filas.append((e, z, fb, bs, motivo))

    out.update(salidas_por_motivo=dict(motivos), descartes=dict(diags),
               orden_salida_ok=orden_ok, ejecutables=len(filas),
               # str(): una zona sin cerrar tiene end_reason None, y una clave
               # None revienta json.dumps(sort_keys=True). No se filtra -- se
               # nombra: "None" ES un estado observado y tiene que verse.
               end_reason_observados={str(k): v for k, v in Counter(
                   (geo.get(e["zone_id"]) or {}).get("end_reason")
                   for e in sel).items()})
    if fase == "salidas":
        return out

    # ------------------------------------------------------------- OUTCOMES
    # A PARTIR DE ACA SE MIRAN RESULTADOS.
    if bar_close is None:
        # NO se descarta lo ya calculado. La version anterior devolvia un dict
        # NUEVO y perdia la poblacion, que era correcta: el artefacto mostraba
        # 0 eventos y 0 con excursion, como si hubiera fallado la medicion
        # cuando lo que faltaba era el precio. Un aborto que borra el
        # diagnostico convierte un defecto localizado en uno indistinguible.
        out.update(estado="ABORTA", precios_leidos=0,
                   motivo="las barras no exponen `close_t`: sin precio de "
                          "entrada no hay evento ejecutable")
        return out
    ev = []
    for e, z, fb, bs, motivo in filas:
        signo = -1 if e["kind"] == "trapped_buyers" else +1
        entrada = float(bar_close[fb])
        salida = float(bar_close[bs])
        bruto = signo * (salida - entrada)
        ev.append(dict(zone_id=e["zone_id"],
                       sesion=session_date_ct(e["first_touch_ms"]),
                       kind=e["kind"], signo=signo, bar_entrada=fb,
                       bar_salida=int(bs), motivo_salida=motivo,
                       entrada_ticks=entrada, salida_ticks=salida,
                       bruto_ticks=round(bruto, 4),
                       neto_ticks=round(bruto - FRICCION_TICKS, 4)))
    out.update(eventos=ev, n_eventos=len(ev), precios_leidos=2 * len(ev))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fase", choices=("poblacion", "salidas", "outcomes"),
                    default="poblacion",
                    help="`salidas` valida la mecanica de salida SIN leer un "
                         "precio. `outcomes` emite outcomes_accessed=true.")
    ap.add_argument("--limite-sesiones", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    ent = identidad_entorno()
    if not ent["es_el_venv_del_repo"]:
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        print("  ejecutable: %s" % ent["ejecutable"])
        print("\nEl 2026-08-09 toda una sesion de mediciones corrio con el "
              "interprete\nglobal porque un AVISO se paso por alto. Este es el "
              "runner de outcomes:\nno corre fuera del entorno declarado.")
        return 2

    con_outcomes = a.fase == "outcomes"
    dias, info = dias_research()
    if a.limite_sesiones:
        dias = dias[:a.limite_sesiones]
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("H1  BigTrap2  T=%d  |  %d sesiones  |  max %s <= %s"
          % (T_OBJETIVO, ns, peor, MAX_FECHA))
    print("FASE: %s   outcomes_accessed sera %s"
          % (a.fase.upper(), str(con_outcomes).lower()))
    print("entorno: python %s | venv del repo %s | numpy %s\n"
          % (ent["python"], ent["es_el_venv_del_repo"], ent["paquetes"]["numpy"]))

    t0 = time.time()
    crudo = {}
    for arch, fechas in plan:
        print("== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        crudo[arch] = poblacion_y_outcomes(arch, fechas, a.fase)
        r = crudo[arch]
        if r.get("estado") == "OK":
            print("   primeros toques %5d | con excursion %5d | orden B %5d"
                  % (r["primeros_toques"], r["con_excursion"],
                     r["poblacion_orden_B"]), flush=True)

    total_B = sum(r.get("poblacion_orden_B", 0) for r in crudo.values()
                  if r.get("estado") == "OK")
    total_X = sum(r.get("con_excursion", 0) for r in crudo.values()
                  if r.get("estado") == "OK")
    precios_leidos_total = sum(r.get("precios_leidos", 0) for r in crudo.values())
    f = total_B / ns if ns else 0.0

    # El control vale SOLO sobre el universo completo: 755 eventos son los de
    # las 201 sesiones. Compararlo contra un piloto reporta un desvio que no
    # existe -- y un control que da falso negativo es un control que se ignora.
    universo_completo = a.limite_sesiones is None
    print("\nCONTROL DE LA FASE 1 -- lo publicado en el sello §1.1")
    if not universo_completo:
        print("  PILOTO de %d sesiones: el control es del universo COMPLETO" % ns)
        print("  (%d con excursion, %d orden B, sobre 201 sesiones). No aplica aca."
              % (CONTROL_CON_EXCURSION, CONTROL_ORDEN_B))
        print("  eventos orden B   %5d   f por sesion %5.2f" % (total_B, f))
        control_ok = None
    else:
        ok_x = total_X == CONTROL_CON_EXCURSION
        ok_b = total_B == CONTROL_ORDEN_B
        ok_f = abs(f - CONTROL_F) < 0.005
        print("  con excursion     %5d   control %5d   %s"
              % (total_X, CONTROL_CON_EXCURSION,
                 "COINCIDE" if ok_x else "*** NO COINCIDE ***"))
        print("  orden B           %5d   control %5d   %s"
              % (total_B, CONTROL_ORDEN_B,
                 "COINCIDE" if ok_b else "*** NO COINCIDE ***"))
        print("  f por sesion      %5.2f   control %5.2f   %s"
              % (f, CONTROL_F, "COINCIDE" if ok_f else "*** NO COINCIDE ***"))
        control_ok = ok_x and ok_b and ok_f
    if control_ok is False:
        print("\n  Un desvio ACA es un defecto DE ESTE RUNNER, no de H1: la")
        print("  poblacion se construye con las mismas primitivas que la midio.")
        print("  H1 NO corre riesgo mientras no se toquen outcomes.")

    if a.fase in ("salidas", "outcomes"):
        from collections import Counter
        mot, dia, ejec = Counter(), Counter(), 0
        orden_ok = True
        razones = Counter()
        for r in crudo.values():
            if r.get("estado") != "OK":
                continue
            mot.update(r.get("salidas_por_motivo") or {})
            dia.update(r.get("descartes") or {})
            razones.update({str(k): v for k, v in
                            (r.get("end_reason_observados") or {}).items()})
            ejec += r.get("ejecutables", 0)
            orden_ok = orden_ok and r.get("orden_salida_ok", True)
        print("\nMECANICA DE SALIDA -- sin leer un solo precio")
        print("  poblacion orden B        %5d" % total_B)
        print("  ejecutables              %5d" % ejec)
        for k, v in sorted(mot.items()):
            print("    por %-22s %5d   (%.1f%%)" % (k, v, 100.0 * v / max(ejec, 1)))
        print("  bar_salida >= bar_entrada  %s"
              % ("SIEMPRE" if orden_ok else "*** VIOLADO ***"))
        print("  end_reason observados en la poblacion:")
        for k, v in sorted(razones.items(), key=lambda kv: -kv[1]):
            print("    %-24s %5d" % (k, v))
        if dia:
            print("  DESCARTES -- ninguno silencioso:")
            for k, v in sorted(dia.items()):
                print("    %-38s %5d" % (k, v))
        else:
            print("  descartes                    0")
        salidas_ok = orden_ok and ejec == total_B
        print("\n  CHEQUEO: %s"
              % ("LIMPIO -- los %d de la poblacion son ejecutables y el orden "
                 "se cumple" % ejec if salidas_ok
                 else "*** HAY DESCARTES O VIOLACIONES ***"))

    payload = dict(
        schema_version=SCHEMA_VERSION, hipotesis="H1", indicador=INDICADOR,
        T=T_OBJETIVO, fase=a.fase,
        sello="docs/predictions/E-R1_v0.3.1_SELLO_2026-08-09.md",
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        friccion_ticks=FRICCION_TICKS, sep_minutes=FIRST_TOUCH_SEP_MINUTES,
        composicion="orden B: exigir validez, despues decongestionar",
        direccion="trapped_buyers -> CORTO (-1) ; trapped_sellers -> LARGO (+1)",
        control_fase1=dict(con_excursion=total_X,
                           con_excursion_control=CONTROL_CON_EXCURSION,
                           orden_B=total_B, orden_B_control=CONTROL_ORDEN_B,
                           f=round(f, 4), f_control=CONTROL_F,
                           coincide=control_ok),
        identidad_entorno=ent, code_commit=git_head(),
        universe_filter_report=info,
        # `outcomes_accessed` registra un HECHO, no una intencion. La version
        # anterior lo derivaba de la fase pedida, asi que una corrida que
        # ABORTO antes de leer un solo precio declaraba `true`. Un campo que
        # dice "se miraron resultados" cuando no se miro ninguno es peor que no
        # tenerlo: es el unico registro de haber cruzado la puerta.
        outcomes_accessed=bool(precios_leidos_total > 0),
        fase_pedida=a.fase,
        precios_leidos=precios_leidos_total,
        segundos=round(time.time() - t0, 1),
        por_contrato=crudo)
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()

    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("runner_H1_%s__%s.json" % (a.fase, payload["payload_sha256"][:12])))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0 if control_ok is not False else 1


if __name__ == "__main__":
    sys.exit(main())
