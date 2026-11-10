"""Recomendador (2026-11-10, pedido de Nico): convierte un resultado en una LECTURA y un PRÓXIMO ANÁLISIS, no en un 0/1.

Las reglas están fijadas antes de ver resultados (pre-registros de `docs/research/hft_clusters_u1_20261110/`) y son genéricas: sirven
para cualquier contraste «A contra B» con bootstrap por sesión. Ninguna categoría promueve nada: CONFIRMAR sólo manda a la réplica
congelada que cada pre-registro ya prevé; INDAGAR propone qué mirar después y con qué análisis.

Entrada: lista de ítems con
  nombre, diferencia, ic90, se, mde80, nominada (BH), n_min (estrato más chico), compuerta_ok,
  por_activo {inst: diferencia o {diferencia, se}}, control_diferencia (opcional), media_a (desenlace medio del grupo de interés),
  monotono (opcional, dosis-respuesta en 3 estratos), sugerencia (texto específico del ítem),
  signo_esperado (+1 la hipótesis espera A > B, −1 A < B, 0 sin dirección; por defecto +1).
Corrección 2026-11-10 (con el primer resultado real): antes se ignoraba el signo (un efecto en contra salía «INDAGAR») y la
inconsistencia entre activos usaba el error estándar combinado (un activo chico y ruidoso la disparaba). Ahora: signo esperado y error
estándar de cada activo.
Salida: por ítem, categoría, lectura, próximo paso y prioridad; más la lista ordenada de «qué hacer después».
"""
from __future__ import annotations

UMBRAL_ECONOMICO = 0.08          # fricción / X: el desenlace medio bruto que paga los costos con stop = X
MDE_UTIL = 0.10                  # un nulo con MDE ≤ 0,10 ya descarta efectos que importen

CATEGORIAS = {
    "CONFIRMAR": "Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.",
    "INDAGAR": "Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.",
    "ESTRUCTURA_DE_PRECIO": "El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.",
    "INCONSISTENTE": "Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.",
    "EN_CONTRA": "El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.",
    "SIN_MUESTRA": "No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.",
    "DESCARTAR": "Sin efecto con potencia: no repetir con esta definición.",
    "NO_CONCLUYENTE": "Ni efecto relevante ni potencia para descartarlo: dejar en espera.",
}


def clasificar(it: dict) -> dict:
    d, se, mde = it.get("diferencia"), it.get("se") or 0.0, it.get("mde80")
    ic = it.get("ic90") or [None, None]; cd = it.get("control_diferencia"); sg = it.get("signo_esperado", 1)
    pa_raw = it.get("por_activo") or {}
    pa = {k: (v.get("diferencia") if isinstance(v, dict) else v) for k, v in pa_raw.items()}
    pa_se = {k: (v.get("se") if isinstance(v, dict) else None) for k, v in pa_raw.items()}
    firmes = {k: v for k, v in pa.items() if v is not None and pa_se.get(k) and abs(v) >= 1.64 * pa_se[k]}   # cada activo con su propio error
    ds = d * sg if (d is not None and sg) else (abs(d) if d is not None else None)                            # efecto en la dirección esperada
    if not it.get("compuerta_ok", True) or d is None or mde is None or mde > 0.25:
        n = it.get("n_min") or 0; fac = (mde / MDE_UTIL) ** 2 if mde else None
        cat = "SIN_MUESTRA"
        paso = (f"Hoy {n} eventos en el estrato más chico" + (f"; para MDE {MDE_UTIL} harían falta ≈ {fac:.1f}× más" if fac else "")
                + ". Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.")
    elif sg and d * sg < 0 and ic[0] is not None and (ic[1] < 0 if sg > 0 else ic[0] > 0):
        cat = "EN_CONTRA"
        paso = (f"Diferencia {d:+.3f} con IC90 [{ic[0]:+.3f}, {ic[1]:+.3f}], opuesta a lo esperado. La hipótesis contraria se pre-registra "
                "aparte y se prueba en datos no usados; ésta queda NO_REPETIR.")
    elif cd is not None and d * cd > 0 and abs(cd) >= 0.5 * abs(d) and abs(d) >= mde / 2:
        cat = "ESTRUCTURA_DE_PRECIO"
        paso = (f"Reales {d:+.3f}, control {cd:+.3f}: el efecto no depende del cluster. Medir directamente la variable de precio que lo "
                "explica (hora, volatilidad reciente, tendencia de la sesión) como familia aparte.")
    elif len(firmes) >= 2 and min(firmes.values()) * max(firmes.values()) < 0:
        cat = "INCONSISTENTE"; paso = f"Por activo: {', '.join(f'{k} {v:+.3f}' for k, v in pa.items() if v is not None)}. " + (it.get("sugerencia") or "")
    elif it.get("nominada"):
        cat = "CONFIRMAR"; paso = "Réplica congelada abr → sep 2026, mismo código. " + (it.get("sugerencia") or "")
    elif ds >= mde / 2 or (ic[0] is not None and sg and (ic[0] > 0 if sg > 0 else ic[1] < 0)) or (not sg and ic[0] is not None and (ic[0] > 0 or ic[1] < 0)):
        cat = "INDAGAR"; paso = it.get("sugerencia") or "Definir la indagación más barata que confirme o mate el efecto en datos no usados."
    elif mde <= MDE_UTIL:                                                  # incluye efectos chicos en contra: con potencia, no hay lo esperado
        cat = "DESCARTAR"; paso = "Asentar como NO_REPETIR con su MDE."
    else:
        cat = "NO_CONCLUYENTE"; paso = "Sin acción salvo que otro resultado lo vuelva relevante."
    z = abs(d) / se if (d is not None and se) else 0.0
    econ = (it.get("media_a") or -9) > UMBRAL_ECONOMICO
    peso = {"CONFIRMAR": 3.0, "INDAGAR": 2.0, "EN_CONTRA": 0.8, "INCONSISTENTE": 1.2, "ESTRUCTURA_DE_PRECIO": 1.0, "SIN_MUESTRA": 0.5, "NO_CONCLUYENTE": 0.3, "DESCARTAR": 0.0}[cat]
    prioridad = round(peso * z * (1.5 if econ else 1.0) * (1.3 if it.get("monotono") else 1.0), 2)
    lectura = CATEGORIAS[cat] + (f" El grupo de interés ya rinde {it['media_a']:+.3f} en bruto, por encima del umbral económico {UMBRAL_ECONOMICO}."
                                 if econ else "")
    if cat == "DESCARTAR" and d is not None and sg and d * sg < 0:
        paso = f"Con MDE {mde:.3f} no aparece el efecto esperado (diferencia {d:+.3f}, en contra pero sin separarse de 0). Asentar como NO_REPETIR."
    return dict(nombre=it["nombre"], categoria=cat, lectura=lectura, proximo_paso=paso, prioridad=prioridad,
                diferencia=d, ic90=ic, mde80=mde, media_a=it.get("media_a"), por_activo=pa, control_diferencia=cd)


def recomendar(items: list) -> dict:
    rs = [clasificar(i) for i in items]
    orden = sorted([r for r in rs if r["categoria"] not in ("DESCARTAR",)], key=lambda r: -r["prioridad"])
    return dict(items=rs, que_hacer_despues=[f"{r['nombre']} ({r['categoria']}, prioridad {r['prioridad']}): {r['proximo_paso']}" for r in orden])


def markdown(titulo: str, rec: dict, fuente: str) -> str:
    L = [f"# {titulo}", "", f"Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `{fuente}`; reglas fijadas antes de ver resultados).",
         "", "## Qué hacer después (ordenado por prioridad)", ""]
    L += [f"{k + 1}. {x}" for k, x in enumerate(rec["que_hacer_despues"])] or ["Nada con prioridad: todo descartado o sin datos."]
    L += ["", "## Detalle", "", "| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |", "|---|---|---|---|---|---|---|---|---|"]
    f = lambda x: "—" if x is None else f"{x:+.3f}"
    for r in rec["items"]:
        ic = r["ic90"] or [None, None]
        L.append(f"| {r['nombre']} | {r['categoria']} | {f(r['diferencia'])} | [{f(ic[0])}, {f(ic[1])}] | {f(r['mde80'])} | {f(r['media_a'])} | "
                 f"{', '.join(f'{k} {f(v)}' for k, v in (r['por_activo'] or {}).items() if v is not None) or '—'} | {f(r['control_diferencia'])} | {r['prioridad']} |")
    L += ["", "Categorías: " + "; ".join(f"**{k}**: {v}" for k, v in CATEGORIAS.items()), ""]
    return "\n".join(L)
