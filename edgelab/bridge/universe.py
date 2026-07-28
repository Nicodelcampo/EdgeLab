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

    # ── ES y NQ (medidos 2026-07-27 sobre los parquets canonicos nuevos) ──────
    #
    # Mismo criterio, misma evidencia: primer dia en que el volumen del contrato
    # nuevo supera al del anterior. NO se estipula ninguna fecha.
    #
    # Hallazgo: **ES y NQ rollan los LUNES; 6E rolla los VIERNES.** Es una
    # diferencia real de convencion entre productos, no un error de medicion --
    # por eso el criterio se mide por instrumento y no se hereda.
    "ES 12-25": dict(desde="2025-09-15", criterio="volumen(12-25) > volumen(09-25)",
                     evidencia="2025-09-15: 709355 vs 430032"),
    "ES 03-26": dict(desde="2025-12-15", criterio="volumen(03-26) > volumen(12-25)",
                     evidencia="2025-12-15: 1013952 vs 591339"),
    "ES 06-26": dict(desde="2026-03-16", criterio="volumen(06-26) > volumen(03-26)",
                     evidencia="2026-03-16: 1037563 vs 733991"),
    "ES 09-26": dict(desde="2026-06-15", criterio="volumen(09-26) > volumen(06-26)",
                     evidencia="2026-06-15: 917332 vs 543911"),

    "NQ 12-25": dict(desde="2025-09-15", criterio="volumen(12-25) > volumen(09-25)",
                     evidencia="2025-09-15: 223514 vs 214326 (margen 4%, el mas fino)"),
    "NQ 03-26": dict(desde="2025-12-15", criterio="volumen(03-26) > volumen(12-25)",
                     evidencia="2025-12-15: 324064 vs 233961"),
    "NQ 06-26": dict(desde="2026-03-16", criterio="volumen(06-26) > volumen(03-26)",
                     evidencia="2026-03-16: 283359 vs 226772"),
    "NQ 09-26": dict(desde="2026-06-14", criterio="volumen(09-26) > volumen(06-26)",
                     # El cruce cae un DOMINGO y con volumen fino (31916 vs 20821),
                     # donde un cruce podria ser casual. Se verifico que se SOSTIENE:
                     # 06-15 341582 vs 133431, 06-16 479498 vs 71278, 06-17 647825
                     # vs 35129, con margen creciente todos los dias. Es un roll
                     # real que ocurrio en la apertura dominical, no un artefacto.
                     evidencia="2026-06-14: 31916 vs 20821; sostenido 06-15 a 06-19"),
    # ── MES (micro del ES) ───────────────────────────────────────────────────
    # Los micros NO heredan la fecha del grande: MES y NQ 09-26 rollan el 14-jun
    # y ES el 15-jun. Un dia de diferencia, pero medido. Por eso cada contrato
    # tiene su propia medicion y ninguna se estipula por analogia.
    "MES 12-25": dict(desde="2025-09-14", criterio="volumen(12-25) > volumen(09-25)",
                      # cruce en un dia MUY fino (20734 vs 18316). Verificado que
                      # se sostiene: 09-15 530577 vs 242613 ... 09-18 1133708 vs
                      # 116596, con margen creciente.
                      evidencia="2025-09-14: 20734 vs 18316; sostenido hasta 09-19"),
    "MES 03-26": dict(desde="2025-12-15", criterio="volumen(03-26) > volumen(12-25)",
                      evidencia="2025-12-15: 997678 vs 518764"),
    "MES 06-26": dict(desde="2026-03-16", criterio="volumen(06-26) > volumen(03-26)",
                      evidencia="2026-03-16: 1122174 vs 836207"),
    "MES 09-26": dict(desde="2026-06-14", criterio="volumen(09-26) > volumen(06-26)",
                      evidencia="2026-06-14: 108370 vs 71644"),

    # ── GC (oro) ─────────────────────────────────────────────────────────────
    # Convencion distinta de los indices: el oro rolla ~2 MESES antes del
    # vencimiento (el Feb-26 toma el liderazgo el 25-nov). Los meses activos son
    # feb, abr, jun, ago y dic; octubre es menor y la cadena lo saltea.
    "GC 02-26": dict(desde="2025-11-25", criterio="volumen(02-26) > volumen(12-25)",
                     evidencia="2025-11-25: 146945 vs 45243"),
    "GC 04-26": dict(desde="2026-01-28", criterio="volumen(04-26) > volumen(02-26)",
                     evidencia="2026-01-28: 401758 vs 37813"),
    "GC 06-26": dict(desde="2026-03-27", criterio="volumen(06-26) > volumen(04-26)",
                     evidencia="2026-03-27: 129285 vs 16094"),
    "GC 08-26": dict(desde="2026-05-27", criterio="volumen(08-26) > volumen(06-26)",
                     evidencia="2026-05-27: 158458 vs 23161"),

    # ── MNQ (micro del NQ) — INCOMPLETO por falta de datos en NT8 ────────────
    "MNQ 12-25": dict(desde="2025-09-15", criterio="volumen(12-25) > volumen(09-25)",
                      # margen del 2% en el cruce; verificado que se sostiene:
                      # 09-16 763175 vs 215002 ... 09-19 1028708 vs 9533.
                      evidencia="2025-09-15: 493068 vs 485476; sostenido hasta 09-19"),
    "MNQ 03-26": dict(desde="2025-12-15", criterio="volumen(03-26) > volumen(12-25)",
                      evidencia="2025-12-15: 971821 vs 894660; sostenido hasta 12-19"),
    # MNQ 06-26 y MNQ 09-26 NO se declaran, y NO es una omision:
    # NT8 no tiene los dias donde cae el cruce. Reexportados el 2026-07-28 dieron
    # EXACTAMENTE el mismo rango -- 06-26 arranca 2026-04-06 (NQ arranca 03-12) y
    # 09-26 arranca 2026-06-25 (NQ arranca 06-08). Faltan 25 y 17 dias al inicio,
    # justo donde ocurre el roll.
    #
    # Se podria inferir la fecha de NQ, que es el mismo subyacente. NO se hace:
    # los micros rollan distinto que los grandes (NQ 09-26 el 14-jun, ES el 15) y
    # copiar la fecha seria estipular. Fail-closed: sin medicion, no entra.

    # ES 09-25, NQ 09-25, MES 09-25, MNQ 09-25 y GC 12-25 NO se declaran:
    # sin contrato anterior en los datos contra el cual medir el cruce.
}

# Cierres tempranos declarados (CME): el viernes cierra 15:00 CT en vez de 16:00.
CIERRES_TEMPRANOS = {
    "2026-06-19": 15,   # Juneteenth observado
    "2026-07-03": 15,   # Independence Day observado
}

VENTANA_CERRADA = (16, 17)      # [16:00, 17:00) CT — mantenimiento diario
HUECO_MIN_MINUTOS = 55          # tolerancia: el hueco real es 60, se admite 55+

# ---------------------------------------------------------------------------
# TIPO DE DÍA (2026-07-27) — corrección de un defecto de la propia batería
#
# `chequeo_hueco_mantenimiento` exige un hueco que cubra las 16:00 CT. En un
# VIERNES la sesión cierra 16:00 y no reabre; en un DOMINGO abre 17:00. Ninguno
# de los dos **puede** tener ese hueco dentro de su día calendario, así que el
# chequeo los rechazaba a los dos por construcción: **0 de 56 viernes y 0 de 60
# domingos APTO**, contra 69–77 % de lunes a jueves.
#
# El efecto no era inocuo: los 163 días efectivos del atlas nulo eran
# exactamente los 163 lun-jue APTO. El nulo estaba estimado **sin un solo
# viernes**, o sea sobre una población distinta de la que cualquier estrategia
# operaría.
#
# Y tenía el error simétrico: el sábado 2025-09-13 con **10 ticks** salió APTO,
# porque con 10 ticks repartidos en 7 horas *cualquier* hueco cubre las 16:00.
#
# La corrección: el tipo de día se DERIVA DE LOS DATOS (no del día de la semana,
# así los feriados y cierres tempranos salen solos) y cada chequeo se aplica
# donde tiene sentido. La batería queda MÁS estricta, no menos: se agregan tres
# chequeos que antes no existían (consistencia de tipo, cobertura horaria, y
# sábado como fallo duro).
#
# Cotas MEDIDAS sobre los 5 parquets de 6E, no estipuladas:
#   lun-jue  mediana 23 horas con ticks (p05 = 22)   -> se exige >= 20
#   viernes  mediana 16 (p05 = 13)                   -> se exige >= 12
#   domingo  mediana  7 (minimo 6)                   -> se exige >=  5
#   sabado   mediana  1 hora, 2 ticks                -> CME no tiene sesion
COMPLETO         = "COMPLETO"          # lun-jue: opera antes y despues del corte
CIERRE_SEMANAL   = "CIERRE_SEMANAL"    # vie: opera hasta el cierre y no reabre
APERTURA_SEMANAL = "APERTURA_SEMANAL"  # dom: abre 17:00 y sigue en el dia siguiente
SIN_ESTRUCTURA   = "SIN_ESTRUCTURA"    # ni una cosa ni la otra

HORAS_MINIMAS = {COMPLETO: 20, CIERRE_SEMANAL: 12, APERTURA_SEMANAL: 5}

# Qué día de la semana puede tener cada tipo. Fail-closed: un martes sin su
# tarde NO es un viernes, es un dia al que le faltan 7 horas.
DOW_ESPERADO = {COMPLETO: {0, 1, 2, 3}, CIERRE_SEMANAL: {4}, APERTURA_SEMANAL: {6}}


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


def _horas_ct(ts_ns, horas=None):
    import numpy as _np
    if horas is not None:
        return _np.asarray(horas)
    return _np.array([_ct(t).hour for t in ts_ns])


def clasificar_dia(ts_ns, horas=None):
    """Tipo de día DERIVADO DE LOS DATOS, no del día de la semana.

    Derivarlo del dato y no del calendario hace que feriados, cierres tempranos
    y medias sesiones se clasifiquen solos, sin lista que mantener.
    """
    import numpy as _np
    h = _horas_ct(ts_ns, horas)
    antes   = bool((h < VENTANA_CERRADA[0]).any())
    despues = bool((h >= VENTANA_CERRADA[1]).any())
    if antes and despues:
        return COMPLETO
    if antes:
        return CIERRE_SEMANAL
    if despues:
        return APERTURA_SEMANAL
    return SIN_ESTRUCTURA


def chequeo_tipo_de_dia(tipo, dow):
    """El tipo derivado tiene que ser posible en ese día de la semana.

    Es el chequeo que atrapa dos cosas que antes pasaban:
    - un **sábado** con ticks (CME no tiene sesión los sábados: 7 casos, de 1 a
      10 ticks, uno de ellos declarado APTO);
    - un lun-jue al que le falta la tarde, que se veria igual que un viernes.
    """
    if dow == 5:
        return dict(ok=False, code="SABADO_SIN_SESION", tipo=tipo,
                    detalle="CME no opera los sabados; cualquier tick aca es un defecto")
    if tipo == SIN_ESTRUCTURA:
        return dict(ok=False, code="DIA_SIN_ESTRUCTURA", tipo=tipo,
                    detalle="sin ticks ni antes de las 16:00 ni despues de las 17:00 CT")
    esperado = DOW_ESPERADO.get(tipo, set())
    if dow is not None and dow not in esperado:
        return dict(ok=False, code="TIPO_DE_DIA_IMPOSIBLE", tipo=tipo, dow=int(dow),
                    detalle="el tipo derivado del dato no corresponde a ese dia de la semana")
    return dict(ok=True, tipo=tipo)


def chequeo_cobertura_horaria(ts_ns, tipo, horas=None):
    """Horas distintas con ticks, contra la cota MEDIDA para ese tipo de día.

    Sin esto, el sabado 2025-09-13 con **10 ticks** salia APTO: con tan pocos
    ticks cualquier hueco cubre las 16:00 y `hueco_mantenimiento` pasa. Un
    chequeo de forma sin uno de densidad se deja enganar por un dia vacio.
    """
    import numpy as _np
    h = _horas_ct(ts_ns, horas)
    n = int(len(_np.unique(h)))
    minimo = HORAS_MINIMAS.get(tipo)
    if minimo is None:
        return dict(ok=False, code="COBERTURA_NO_EVALUABLE", horas=n, tipo=tipo)
    if n < minimo:
        return dict(ok=False, code="COBERTURA_HORARIA_INSUFICIENTE",
                    horas=n, minimo=minimo, tipo=tipo)
    return dict(ok=True, horas=n, minimo=minimo, tipo=tipo)


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
           "tipo_de_dia", "cobertura_horaria",
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

    if dow is None:
        dow = _ct(ts_ns[0]).weekday()
    tipo = clasificar_dia(ts_ns, horas)

    res = {
        "front_month": es_front_month(contrato, fecha),
        "monotonia": chequeo_monotonia(ts_ns),
        "timestamps_posibles": chequeo_timestamps_posibles(ts_ns),
        "precios_en_grilla": (chequeo_precios_en_grilla(price_ticks)
                              if price_ticks is not None
                              else dict(ok=True, code="NO_EVALUADO")),
        "tipo_de_dia": chequeo_tipo_de_dia(tipo, dow),
        "cobertura_horaria": chequeo_cobertura_horaria(ts_ns, tipo, horas),
        # SOLO donde la ventana de mantenimiento EXISTE. En un viernes la sesion
        # cierra 16:00 y no reabre; en un domingo abre 17:00. Exigirles un hueco
        # que cubra las 16:00 los rechazaba a los dos por construccion.
        "hueco_mantenimiento": (chequeo_hueco_mantenimiento(ts_ns) if tipo == COMPLETO
                                else dict(ok=True, code="NO_APLICA", tipo=tipo)),
        "ventana_cerrada_vacia": chequeo_ventana_cerrada_vacia(ts_ns, horas),
        "cierre_semanal": chequeo_cierre_semanal(ts_ns, fecha, dow),
        "apertura_dominical": chequeo_apertura_dominical(ts_ns, dow),
    }
    fallos = [dict(chequeo=k, **v) for k, v in res.items() if not v["ok"]]
    estado = "APTO" if not fallos else "DEFECTUOSO"
    return dict(fecha=fecha, contrato=contrato, estado=estado, tipo_de_dia=tipo,
                n_ticks=len(ts_ns), motivos=fallos, detalle=res)


def exigir_apto(rep):
    """Fail-loud para el camino de consumo: levanta si el día no es apto."""
    if rep["estado"] != "APTO":
        raise IntegridadError(
            "dia %s (%s) NO pertenece al universo: %s"
            % (rep["fecha"], rep.get("contrato"),
               "; ".join("%s/%s" % (m["chequeo"], m.get("code")) for m in rep["motivos"])))
    return rep
