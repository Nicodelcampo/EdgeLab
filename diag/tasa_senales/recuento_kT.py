# -*- coding: utf-8 -*-
"""Paso 1 de EXPLORE-001 v0.3 §7: el recuento con `k_T > 0` y `j > k_T`.

## Qué corrige respecto de la curva de diseño

`curva_excursion_ticks.py` cuenta como `retorno[T]` cualquier vuelta a la banda
posterior a `k_T = min(rup_up[T], rup_dn[T])`, **incluido `k_T == 0`**. Y
`k_T == 0` significa que el precio **ya estaba** a `T` ticks o más del borde en
el primer tick de la ventana: el alejamiento no lo produjo el precio después de
que la zona existiera — lo produjo la zona, que nació detrás.

v0.3 §3.2 lo define así, y este módulo lo implementa:

```
k_T > 0   ->  excursion valida para la hipotesis primaria
k_T == 0  ->  estado inicial ya externo: NO es ruptura, NO habilita retorno
retorno valido  <=>  k_T > 0  y  j_retorno > k_T
```

## Predicción registrada ANTES de correr esto

De `sonda_alejamiento_cero__6E_09-26_08s.json`, la fracción de zonas con
`k_T == 0` en las celdas candidatas es:

    BigTrap2      T=34   0,14 %
    aVolCellPOI2  T=21   0,00 %
    Gaps2         T=34   0,00 %

**Predicción: la frecuencia corregida no se mueve más de ~0,2 % en esas
celdas.** Queda escrito acá, antes de medir. Si el resultado difiere mucho de
eso, la lectura correcta es **buscar un defecto en este código**, no anunciar un
hallazgo: dos mediciones outcome-free de la misma población no deberían
discrepar.

## La segunda pregunta, que es de MECANISMO y no de estadística

`Gaps2` es el tercer candidato condicional de v0.3 §6.4. Su mecanismo enunciable
sin outcomes es «un gap es un rango que el trading salteó, y el precio vuelve a
llenarlo».

**Pero el 75 % de las zonas de `Gaps2` contienen al precio en el instante en que
quedan disponibles.** Si el precio ya está adentro, el gap **no es un vacío**, y
no hay nada a lo que volver: el mecanismo no aplica, aunque el evento se cuente
igual.

Por eso, para cada retorno válido se registra si su zona **contenía al precio en
`i0`**. Si la fracción de retornos que vienen de zonas genuinamente vacías es
alta, el mecanismo aplica; si es baja, `Gaps2` cae **por razones de mecanismo,
no de estadística** — que es un motivo mejor y se decide antes de outcomes.

## Frontera

Outcome-free, igual que la curva: conteos, cobertura y descartes. **Ningún
retorno posterior, P&L, TP/SL, expectativa ni «mejor T».** Mismo firewall, misma
puerta de universo, mismo orden `(ts_ns, sequence)`.

Uso:
    python diag/tasa_senales/recuento_kT.py --workers 4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, T_DESIGN,
    TZ_CHART, bars_mod, corte_del_sello, dias_research, git_head,
    huella_del_codigo, pd, sesion_ct, ticks_mod,
)

SCHEMA_VERSION = "recuento_kT_v1"
SALIDA = Path(__file__).resolve().parent / "recuento_kT.json"

#: Los candidatos de v0.3 §6.3. `HFTZones2` es reserva y NO entra: es el 40 % del
#: costo de computo y la spec dice que no entra por defecto si `Gaps2` pasa.
#: `VolTicksPOC2` tampoco: no alcanza el regimen operativo dentro de la grilla.
CANDIDATOS = ("BigTrap2", "aVolCellPOI2", "Gaps2")

#: Se computa la GRILLA ENTERA, no solo el `T` candidato. Cuesta casi nada -el
#: recorrido de zonas fue el 0,7 % del costo, los kernels son el resto- y v0.3
#: §7 paso 3 exige **estabilidad entre puntos adyacentes**: con un solo punto no
#: se puede evaluar.
#:
#: ADVERTENCIA QUE HAY QUE LEER: `T=34` es el ULTIMO punto de `T_DESIGN`, asi que
#: para `BigTrap2` y `Gaps2` **no hay vecino superior**. La regla de banda
#: contigua no se puede evaluar completa en ese borde. O se extiende la grilla,
#: o se acepta el borde declarandolo. No lo decide este script.
T_GRID = T_DESIGN


def eventos_kT(px, lo_t, hi_t, i0, i1, umbrales):
    """Por umbral: `(k_T, j_retorno)` con la semántica de v0.3 §3.2.

    Devuelve `(por_T, dentro_en_i0)` donde `por_T[T] = (k_T, j)`; `k_T` es
    `None` si el precio nunca se aleja `T`, y `j` es `None` si no vuelve.

    `k_T` sale de la acumulada monótona, igual que en la curva: `runmax[j]` es
    no decreciente, así que el primer índice con `px >= hi + T` es un
    `searchsorted`. **La diferencia con la curva no está acá sino en el uso:**
    acá `k_T == 0` se reporta aparte y no habilita retorno.
    """
    if i1 <= i0:
        return None, None
    p = px[i0:i1]
    if not len(p):
        return None, None

    dentro_en_i0 = bool(lo_t <= p[0] <= hi_t)
    rmax = np.maximum.accumulate(p)
    rmin = np.minimum.accumulate(p)
    dentro = np.flatnonzero((p >= lo_t) & (p <= hi_t))

    por_T = {}
    for T in umbrales:
        ku = int(np.searchsorted(rmax, hi_t + T, side="left"))
        kd = int(np.searchsorted(-rmin, -(lo_t - T), side="left"))
        cand = [k for k in (ku, kd) if k < len(p)]
        if not cand:
            por_T[T] = (None, None)
            continue
        k = min(cand)
        # RETORNO VALIDO: exige k_T > 0 **y** j > k_T. Un k_T == 0 no habilita
        # retorno primario -- el alejamiento no lo produjo el precio.
        j = None
        if k > 0 and len(dentro):
            q = int(np.searchsorted(dentro, k, side="right"))
            if q < len(dentro):
                j = int(dentro[q])
        por_T[T] = (k, j)
    return por_T, dentro_en_i0


def medir(archivo, fechas, indicadores, verbose=True):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())

    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    sq = np.asarray(tk.sequence)
    if not bool((np.diff(sq) > 0).all()):
        return {n: dict(estado="ABSTAIN",
                        motivo="`sequence` no es orden total: el orden intrabar "
                               "no es demostrable")
                for n in indicadores}

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = None
    setf = set(fechas)

    res = {}
    for nombre in indicadores:
        t1 = time.time()
        clase = CLASE_KERNEL.get(nombre)
        if clase is None:
            res[nombre] = dict(estado="DESCARTADO", motivo="sin clase de kernel")
            continue
        mod = REGISTRY[nombre]
        if nombre in BAR_DRIVEN:
            if fp is None:
                fp = bars_mod.build_footprints(tk, b)
            r = mod.run(tk, b, fp, chart_tz=TZ_CHART)
        else:
            r = mod.run(tk, b, chart_tz=TZ_CHART)

        # Conteos POR SESION: es el grano que despues permite N_eff y DEFF sin
        # volver a correr. Agregado global no alcanza.
        val = {t: Counter() for t in T_GRID}      # retornos validos
        cero = {t: Counter() for t in T_GRID}     # k_T == 0
        nunca = {t: Counter() for t in T_GRID}    # nunca se aleja T
        sin_volver = {t: Counter() for t in T_GRID}
        # MECANISMO: de los retornos validos, cuantos vienen de una zona que NO
        # contenia al precio al quedar disponible -- o sea, un vacio de verdad.
        val_vacio = {t: Counter() for t in T_GRID}
        n_zonas = n_sin_campos = n_sin_cb = n_sin_tramo = 0
        n_dentro_i0 = 0

        for z in r.get("zones") or []:
            if z.get("created_ms") is None or z.get("top") is None:
                n_sin_campos += 1
                continue
            cb = z.get("created_bar")
            if cb is None or not isinstance(cb, (int, np.integer)) \
                    or cb < 0 or cb >= len(bar_end):
                n_sin_cb += 1
                continue
            lo_t, hi_t = z["bottom"] / tk.tick_size, z["top"] / tk.tick_size
            disp = (int(bar_end[int(cb)]) if clase == "bar_close"
                    else (int(z["created_ms"]) + 1) * 1_000_000)
            i0 = int(np.searchsorted(ts, disp, side="right"))
            fin_ms = z.get("ended_ms")
            i1 = (int(np.searchsorted(ts, int(fin_ms) * 1_000_000, side="right"))
                  if fin_ms else len(ts))
            por_T, dentro_i0 = eventos_kT(px, lo_t, hi_t, i0, min(i1, len(ts)),
                                          T_GRID)
            if por_T is None:
                n_sin_tramo += 1
                continue
            n_zonas += 1
            if dentro_i0:
                n_dentro_i0 += 1

            for T, (k, j) in por_T.items():
                if k is None:
                    nunca[T][""] += 1
                    continue
                if k == 0:
                    cero[T][""] += 1
                    continue
                if j is None:
                    sin_volver[T][""] += 1
                    continue
                # la sesion se atribuye al instante del RETORNO
                d = sesion_ct(int(ts[i0 + j]))
                if d not in setf:
                    continue
                val[T][d] += 1
                if not dentro_i0:
                    val_vacio[T][d] += 1

        res[nombre] = dict(
            estado="OK", clase_kernel=clase, zonas=n_zonas,
            zonas_sin_campos=n_sin_campos, zonas_sin_created_bar=n_sin_cb,
            zonas_sin_tramo=n_sin_tramo,
            zonas_dentro_en_i0=n_dentro_i0,
            frac_dentro_en_i0=(round(n_dentro_i0 / n_zonas, 4) if n_zonas else None),
            retornos_validos={str(t): dict(val[t]) for t in T_GRID},
            retornos_validos_desde_vacio={str(t): dict(val_vacio[t]) for t in T_GRID},
            k_cero={str(t): cero[t][""] for t in T_GRID},
            nunca_se_aleja={str(t): nunca[t][""] for t in T_GRID},
            no_vuelve={str(t): sin_volver[t][""] for t in T_GRID},
            segundos=round(time.time() - t1, 1))
        if verbose:
            print("   %-14s zonas=%6d  retornos T=34: %5d  k0=%4d  (%.0fs)"
                  % (nombre, n_zonas, sum(val[34].values()), cero[34][""],
                     time.time() - t1), flush=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limite-sesiones", type=int, default=None)
    ap.add_argument("--indicadores", nargs="+", default=list(CANDIDATOS))
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    dias, info = dias_research()
    if a.limite_sesiones:
        dias = dias[:a.limite_sesiones]
    # mismo armado que la curva: agrupar por contrato y ordenar. No se
    # reutiliza una funcion porque la curva lo hace inline en `main()`.
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    peor = max(f for _arch, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _a, fs in plan)
    print("universo: %d sesiones | max %s <= %s | indicadores %s | workers %d"
          % (ns, peor, MAX_FECHA, a.indicadores, a.workers), flush=True)

    crudo = {}
    for arch, fechas in plan:
        print("== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        crudo[arch] = medir(arch, fechas, a.indicadores)

    # AGREGADO por indicador y umbral: senales/sesion corregidas
    curvas = {}
    for n in a.indicadores:
        tot = {str(t): 0 for t in T_GRID}
        tot_v = {str(t): 0 for t in T_GRID}
        k0 = {str(t): 0 for t in T_GRID}
        for arch, r in crudo.items():
            x = r.get(n) or {}
            if x.get("estado") != "OK":
                continue
            for t in T_GRID:
                tot[str(t)] += sum((x["retornos_validos"].get(str(t)) or {}).values())
                tot_v[str(t)] += sum(
                    (x["retornos_validos_desde_vacio"].get(str(t)) or {}).values())
                k0[str(t)] += x["k_cero"].get(str(t), 0)
        curvas[n] = dict(
            retornos_validos_por_sesion={t: round(v / ns, 2) for t, v in tot.items()},
            retornos_totales=tot, retornos_desde_vacio=tot_v,
            frac_desde_vacio={t: (round(tot_v[t] / tot[t], 4) if tot[t] else None)
                              for t in tot},
            k_cero=k0)

    print("\nRETORNOS VALIDOS por sesion (k_T > 0 y j > k_T)")
    print("  %-14s %s" % ("indicador", " ".join("%7d" % t for t in T_GRID)))
    for n in a.indicadores:
        c = curvas[n]["retornos_validos_por_sesion"]
        print("  %-14s %s" % (n, " ".join("%7.2f" % c[str(t)] for t in T_GRID)))

    print("\nFRACCION que viene de una zona VACIA (no contenia al precio en i0)")
    print("  la pregunta de MECANISMO: un gap con el precio adentro no es un vacio")
    print("  %-14s %s" % ("indicador", " ".join("%7d" % t for t in T_GRID)))
    for n in a.indicadores:
        f = curvas[n]["frac_desde_vacio"]
        print("  %-14s %s" % (n, " ".join("%7s" % f[str(t)] for t in T_GRID)))

    payload = dict(
        schema_version=SCHEMA_VERSION,
        que_es="recuento con k_T > 0 y j > k_T -- v0.3 §3.2 y §7 paso 1",
        prediccion_registrada="la frecuencia corregida no se mueve mas de ~0,2 % "
                              "en las celdas candidatas; si difiere mucho, buscar "
                              "un defecto en este codigo antes que un hallazgo",
        indicadores=list(a.indicadores), umbrales=list(T_GRID),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        clase_kernel={k: v for k, v in CLASE_KERNEL.items() if k in a.indicadores},
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo(sorted(a.indicadores)),
        universe_filter_report=info,
        outcomes_accessed=False,
        curvas=curvas, por_contrato=crudo)
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("\n-> %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
