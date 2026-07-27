# -*- coding: utf-8 -*-
"""Universo de datos admisibles para estudios. **Módulo separado a propósito.**

No vive dentro de `sessions.py`: ése es superficie de paridad ya validada (7/7
fronteras contra el oráculo real) y no se toca. El universo es responsabilidad de
los *estudios*, va a crecer con cada instrumento nuevo, y sus reglas se relajan o
endurecen sin que eso deba poder romper la paridad NT8.

## Por qué existe — el defecto que lo motivó (2026-07-26)

El parquet `6E_09-26` tiene, en **9 días** (2026-06-22 → 2026-07-02), la ventana
de mantenimiento 16:00–17:00 CT **rellena con una copia literal** de la hora
13:00–14:00 del mismo día: 3577 ticks contra 3577, secuencia `(precio, volumen)`
idéntica, ninguna otra hora duplicada. **31.491 ticks** en total.

Se demostró que el defecto es del **parquet**, no del feed: el oráculo NT8 de
esos mismos 9 días tiene **0 eventos** en esa ventana. NT8 no puede haber emitido
una copia de una hora anterior.

Lo que lo hace peligroso no es el tamaño sino que **se encontró por accidente**:
cayó en la ventana de mantenimiento, donde no debía haber nada. La misma
duplicación en una hora activa habría sido invisible — el precio es continuo, el
volumen plausible, y ninguna regla de sesión la delata. De ahí el censo por
hashes de bloque de `tools/censo_integridad.py`.

## Reglas (6E 09-26)

1. **Front month** desde **2026-06-12**: primer día en que el volumen de 09-26
   supera al de 06-26 (139.367 vs 19.280). Criterio estándar, medido, no elegido.
2. **Integridad diaria**, batería completa — un día entra sólo si pasa **todas**.
3. Los 9 días caen por la **regla general** (hueco de mantenimiento ausente), no
   por una lista negra. Una lista se desactualiza; una regla no.
4. Dentro de un día APTO, un tick en la ventana cerrada es **fail-loud**.
5. **Los parquets son inmutables.** Los días defectuosos se excluyen y se
   documentan; la readmisión exige regenerar F2 y volver a pasar la batería.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000

# ---------------------------------------------------------------------------
# Front month por volumen. Fecha medida, no estipulada.
FRONT_MONTH = {
    # Todos MEDIDOS con el mismo criterio: primer dia en que el volumen del
    # contrato supera al del front month anterior. Ninguno estipulado a ojo.
    "6E 12-25": dict(desde="2025-09-12", criterio="volumen(12-25) > volumen(09-25)",
                     evidencia="2025-09-12: 99836 vs 16312"),
    "6E 03-26": dict(desde="2025-12-12", criterio="volumen(03-26) > volumen(12-25)",
                     evidencia="2025-12-12: 122590 vs 15060"),
    "6E 06-26": dict(desde="2026-03-13", criterio="volumen(06-26) > volumen(03-26)",
                     evidencia="2026-03-13: 201738 vs 25082"),
    "6E 09-26": dict(desde="2026-06-12", criterio="volumen(09-26) > volumen(06-26)",
                     evidencia="2026-06-12: 139367 vs 19280"),
    # 6E 09-25 NO se declara: no hay contrato anterior en los datos contra el cual
    # medir el cruce. Fail-closed: sin medicion, no entra al universo.
}

# Cierres tempranos declarados (CME): el viernes cierra 15:00 CT en vez de 16:00.
CIERRES_TEMPRANOS = {
    "2026-06-19": 15,   # Juneteenth observado
    "2026-07-03": 15,   # Independence Day observado
}

VENTANA_CERRADA = (16, 17)      # [16:00, 17:00) CT — mantenimiento diario
HUECO_MIN_MINUTOS = 55          # tolerancia: el hueco real es 60, se admite 55+


class IntegridadError(AssertionError):
    """Fail-loud: dato incompatible con el universo declarado."""


def _ct(ns):
    return datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).astimezone(CT)


def _trade_date(ns):
    """Fecha CT del día calendario del tick (no el trade-date de sesión).

    Deliberadamente el día CALENDARIO: la batería evalúa la forma del día tal
    como se ve en el reloj local del mercado, que es donde el defecto se
    manifiesta.
    """
    return _ct(ns).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# La batería
# ---------------------------------------------------------------------------
def chequeo_hueco_mantenimiento(ts_ns):
    """(ver docstring abajo) — la busqueda del hueco se hace con numpy sobre los
    diffs y solo se convierte a datetime el candidato, no los millones de ticks."""
    """Existe un hueco >= 55 min que CONTIENE la ventana 16:00–17:00 CT.

    Es el chequeo que atrapa la duplicación de bloque: si alguien rellena la
    ventana cerrada, el hueco desaparece.
    """
    import numpy as _np
    t = _np.asarray(ts_ns, dtype="int64")
    if len(t) < 2:
        return dict(ok=False, code="SIN_DATOS")
    d = _np.diff(t)
    cand = _np.flatnonzero(d >= int(HUECO_MIN_MINUTOS * 6e10))
    hueco = None
    for i in cand:
        a, b = int(t[i]), int(t[i + 1])
        dt = (b - a) / 6e10
        ca, cb = _ct(a), _ct(b)
        # el hueco tiene que cubrir el instante de las 16:00 CT
        cierre = ca.replace(hour=VENTANA_CERRADA[0], minute=0, second=0, microsecond=0)
        if ca <= cierre <= cb:
            hueco = (ca, cb, dt)
            break
    if hueco is None:
        return dict(ok=False, code="SIN_HUECO_DE_MANTENIMIENTO",
                    detalle=("no hay hueco >= %d min cubriendo las 16:00 CT. "
                             "Firma tipica de la ventana cerrada RELLENADA."
                             % HUECO_MIN_MINUTOS))
    return dict(ok=True, inicio=hueco[0].strftime("%H:%M"),
                fin=hueco[1].strftime("%H:%M"), minutos=round(hueco[2], 1))


def chequeo_ventana_cerrada_vacia(ts_ns, horas=None):
    """Fail-loud (regla 4): ningún tick dentro de [16:00, 17:00) CT.

    `horas` permite pasar las horas CT ya convertidas en bloque: convertir tick a
    tick cuesta ~15 us cada uno y sobre millones de ticks domina el censo entero.
    """
    if horas is not None:
        import numpy as _np
        h = _np.asarray(horas)
        n = int(((h >= VENTANA_CERRADA[0]) & (h < VENTANA_CERRADA[1])).sum())
    else:
        n = sum(1 for t in ts_ns if VENTANA_CERRADA[0] <= _ct(t).hour < VENTANA_CERRADA[1])
    if n:
        return dict(ok=False, code="TICKS_EN_VENTANA_CERRADA", n=n)
    return dict(ok=True, n=0)


def chequeo_cierre_semanal(ts_ns, fecha, dow=None):
    """Viernes: el último tick no pasa la hora de cierre (16:00, o 15:00 si es
    cierre temprano declarado)."""
    d = _ct(ts_ns[-1])
    if (dow if dow is not None else d.weekday()) != 4:
        return dict(ok=True, code="NO_ES_VIERNES")
    limite = CIERRES_TEMPRANOS.get(fecha, 16)
    if d.hour >= limite:
        return dict(ok=False, code="CIERRE_SEMANAL_TARDIO",
                    ultimo=d.strftime("%H:%M"), limite="%02d:00" % limite)
    return dict(ok=True, ultimo=d.strftime("%H:%M"))


def chequeo_apertura_dominical(ts_ns, dow=None):
    """Domingo: el primer tick no es anterior a las 17:00 CT."""
    d = _ct(ts_ns[0])
    if (dow if dow is not None else d.weekday()) != 6:
        return dict(ok=True, code="NO_ES_DOMINGO")
    if d.hour < 17:
        return dict(ok=False, code="APERTURA_DOMINICAL_TEMPRANA",
                    primero=d.strftime("%H:%M"))
    return dict(ok=True, primero=d.strftime("%H:%M"))


def chequeo_monotonia(ts_ns):
    import numpy as _np
    t = _np.asarray(ts_ns, dtype="int64")
    malos = int((_np.diff(t) < 0).sum()) if len(t) > 1 else 0
    return (dict(ok=True) if not malos
            else dict(ok=False, code="TIMESTAMPS_NO_MONOTONOS", n=malos))


def chequeo_timestamps_posibles(ts_ns, lo="2020-01-01", hi="2035-01-01"):
    a = int(datetime.fromisoformat(lo).replace(tzinfo=timezone.utc).timestamp() * NS)
    b = int(datetime.fromisoformat(hi).replace(tzinfo=timezone.utc).timestamp() * NS)
    import numpy as _np
    tt = _np.asarray(ts_ns, dtype="int64")
    malos = int(((tt < a) | (tt > b)).sum())
    return (dict(ok=True) if not malos
            else dict(ok=False, code="TIMESTAMP_IMPOSIBLE", n=malos))


def chequeo_precios_en_grilla(price_ticks):
    """Los precios ya vienen como ENTEROS de tick en el schema canónico. Que
    alguno no lo sea significa que el parquet se generó fuera de contrato."""
    import numpy as _np
    pp = _np.asarray(price_ticks)
    malos = int((pp != pp.astype("int64")).sum())
    return (dict(ok=True) if not malos
            else dict(ok=False, code="PRECIO_FUERA_DE_GRILLA", n=malos))


def es_front_month(contrato, fecha):
    reg = FRONT_MONTH.get(contrato)
    if reg is None:
        return dict(ok=False, code="CONTRATO_SIN_FRONT_MONTH_DECLARADO",
                    detalle="no se admite un contrato cuyo front month no se midió")
    return (dict(ok=True) if fecha >= reg["desde"]
            else dict(ok=False, code="PRE_FRONT_MONTH", desde=reg["desde"]))


BATERIA = ("front_month", "monotonia", "timestamps_posibles", "precios_en_grilla",
           "hueco_mantenimiento", "ventana_cerrada_vacia", "cierre_semanal",
           "apertura_dominical")


def evaluar_dia(contrato, fecha, ts_ns, price_ticks=None, horas=None, dow=None):
    """Aplica la batería completa. Devuelve APTO / DEFECTUOSO / INDETERMINADO.

    **Fail-closed**: sin datos suficientes no se declara apto. Un día que no se
    puede evaluar no es un día limpio.
    """
    if not len(ts_ns):
        return dict(fecha=fecha, estado="INDETERMINADO", motivos=[
            dict(chequeo="datos", ok=False, code="SIN_TICKS")])

    res = {
        "front_month": es_front_month(contrato, fecha),
        "monotonia": chequeo_monotonia(ts_ns),
        "timestamps_posibles": chequeo_timestamps_posibles(ts_ns),
        "precios_en_grilla": (chequeo_precios_en_grilla(price_ticks)
                              if price_ticks is not None
                              else dict(ok=True, code="NO_EVALUADO")),
        "hueco_mantenimiento": chequeo_hueco_mantenimiento(ts_ns),
        "ventana_cerrada_vacia": chequeo_ventana_cerrada_vacia(ts_ns, horas),
        "cierre_semanal": chequeo_cierre_semanal(ts_ns, fecha, dow),
        "apertura_dominical": chequeo_apertura_dominical(ts_ns, dow),
    }
    fallos = [dict(chequeo=k, **v) for k, v in res.items() if not v["ok"]]
    estado = "APTO" if not fallos else "DEFECTUOSO"
    return dict(fecha=fecha, contrato=contrato, estado=estado,
                n_ticks=len(ts_ns), motivos=fallos, detalle=res)


def exigir_apto(rep):
    """Fail-loud para el camino de consumo: levanta si el día no es apto."""
    if rep["estado"] != "APTO":
        raise IntegridadError(
            "dia %s (%s) NO pertenece al universo: %s"
            % (rep["fecha"], rep.get("contrato"),
               "; ".join("%s/%s" % (m["chequeo"], m.get("code")) for m in rep["motivos"])))
    return rep
