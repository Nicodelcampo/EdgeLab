"""Paquete de contexto y creatividad para el proponente (pedido de Nico, 2026-10-16).

Cada llamada al proponente recibe, armado por código y no por el LLM:
  1. prioridades fijas (mandato + referente) — lo importante se recuerda en TODOS los ciclos;
  2. tablero: qué se midió, qué murió y por qué, alfa restante;
  3. vacíos abiertos y fichas de literatura (del bibliotecario: Brain + SSRN);
  4. una LENTE que rota, para forzar diversidad;
  5. lo prohibido (familias retiradas, holdout, P&L sin pre-registro publicado y doble revisión).
Después, un filtro de novedad descarta propuestas que repiten algo existente o retirado.
Lo que sale es un BORRADOR: no entra a candidates.json sin pre-registro committeado y promote humano.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

PRIORIDADES = [
    "Objetivo: edges netos (después de costos), robustos fuera de muestra y operables; útiles para challenges y combinables.",
    "Cadena obligatoria: geometría -> información -> P&L bruto -> edge neto replicado. No saltar a P&L.",
    "Preferir lo que más reduce la distancia a un edge operable por unidad de cómputo. Evitar refinamientos triviales.",
    "Toda prueba cuenta para la multiplicidad de por vida. Proponer de más infla N_eff.",
    "Holdout desde la sesión CME del 2026-10-01: prohibido para diseñar o elegir.",
    "Mirar hacia atrás para encontrar el patrón es válido sólo para proponer; confirmar exige datos que no se usaron para encontrarlo. Cada vuelta sobre los mismos datos suma pruebas.",
    "Principio de Nico (2026-10-19) — macro antes que micro: preferir horizontes y movimientos grandes (minutos a días, decenas de ticks) sobre microestructura; la fricción se come los efectos chicos.",
    "Principio de Nico (2026-10-19) — régimen: una estrategia puede no ser rentable siempre pero sí ahora; es válido proponer edges condicionados a un régimen identificable en tiempo real, con la regla de detección del régimen pre-registrada y su estabilidad medida fuera de muestra.",
    "Principio de Nico (2026-10-19) — cartera: varias estrategias rentables y poco correlacionadas diversifican más que una sola mejor; valorar la baja correlación con lo ya vivo tanto como el rendimiento propio.",
    "Principio de Nico (2026-10-22) — edges ACTUALES: queremos lo que funciona ahora aunque en el pasado no haya funcionado. Que algo haya fallado en datos viejos no lo mata; que funcione sólo en lo reciente no lo descalifica. La confirmación de «ahora» sale de datos posteriores (réplica en lo más reciente sin usar y luego forward/holdout con seguimiento secuencial), y la ventana «reciente» se declara antes de mirar: elegirla después de ver el P&L es data snooping. Un edge actual se vigila por decaimiento en vivo.",
    "Modalidad de barrido (2026-10-23): diseñar barridos propios de millones de escenarios con el conductor genérico (edgelab/research/grilla_generica.py; guía §6) sobre indicadores PASS de config/autopilot/indicadores.json o indicadores propios causales; filtrar con tamiz + Romano-Wolf + réplica; antes de un P&L básico de una variante buena, indagarla con marginales (ATJ-26). Lo que no cubre millones de variantes con poco costo no es prioridad. Un experimento propio se lanza escribiendo su campaña en config/autopilot/grillas/campanas/ con embudo=true: el embudo automático (guía §8) lo lleva solo hasta la decisión del holdout, en cualquier activo (señal y ejecución pueden ser distintos).",
    "Fricción primero: elegir escenarios (instrumento, horario, régimen, horizonte) donde el movimiento esperado sea al menos 3 veces la fricción por viaje; no proponer análisis donde la fricción probablemente gana.",
    "Grilla masiva (AREAS-EXP-1, 2026-10-22): para explorar miles o millones de variantes de una idea, perillas ordinales + tensor de sumas acumuladas + tamiz FDR + E2 por sesiones + réplica congelada (docs/research/GUIA_GRILLA_MASIVA.md). Las variantes se cambian sin código con la variable GRILLA; un experimento nuevo trae controles de ruido y plantado.",
    "Régimen (Nico 2026-11-07): la unidad de evidencia es el DÍA; un régimen corto con muchas operaciones y días estables tiene potencia. Toda regla de régimen se prueba en el motor offline de cubos (edgelab/research/regimen_offline.py) en walk-forward contra azar, calidad estática (que le ganó a la racha en H-REG-1) y nulo de signo por sesión; todo filtro común se juzga también en bruto (marginales_globales_bruto: si sólo mejora en neto es fricción). Leer corridas anteriores inspira; confirmar exige datos nuevos. Guía: docs/research/GUIA_REGIMEN_PARA_AGENTE_20261107.md.",
    "Fills pasivos sólo por replay tick a tick con máquina de estados causal (espera acotada, cancelación si el precio escapa, excursiones medidas después del fill, stop primero): el modelo 'tocó el precio en la ventana' infló ~0,6 ticks/op en ES (k32). Una partición es réplica sólo si el registro de la familia la declara sin usar. Un gate diseñado después de ver la pérdida es una prueba nueva.",
]
LENTES = {
    "indagar_factor": "Elegí UNA entrada PISTA_VIVA o PALANCA_DE_DISENO de nucleo_proyecto.factores_con_ventaja y proponé su `siguiente` indagación tal como está escrita (o una más barata que responda lo mismo): qué mide, en qué datos no usados, y qué resultado la pasa a NO_REPETIR. No abras una familia nueva.",
    "puente_mecanismo": "Llevá un hallazgo de información ya medido a un mecanismo económico publicado que lo explique y predecí algo nuevo.",
    "replica_debil": "Tomá una pista débil y diseñá su réplica en una muestra que todavía no se usó.",
    "artefacto": "Buscá el artefacto más probable detrás del resultado más sospechoso del tablero (microestructura, rebote bid-ask, look-ahead).",
    "otro_instrumento": "Trasladá el efecto más robusto a otro instrumento o escala sin cambiar a la vez la métrica.",
    "abogado_del_diablo": "Formulá la hipótesis que, si es cierta, explicaría el éxito más fuerte SIN que sea un edge. Que sea refutable.",
    "costo_y_ejecucion": "Diseñá la medición que decide si el mejor efecto vivo puede pagar costos reales (spread, comisión, slippage).",
    "ingenieria_inversa": "Tomá un resultado ya medido (ganadoras vs. perdedoras, o eventos que el detector descartó) y preguntá qué estado previo lo habría anticipado. Lo que encuentres es una HIPÓTESIS nueva: debe probarse en una muestra que no participó del hallazgo, nunca en la misma.",
    "hueco_gramatica": "Tomá UNA de las cartas_gramatica (coordenadas lejos de lo ya medido, elegidas sin mirar resultados) y convertila en familia: mecanismo económico, espacio de eventos enumerado, régimen declarado ex ante y perillas del barrido. Si ninguna tiene un mecanismo plausible, decilo y proponé la variante más cercana que sí lo tenga.",
    "regimen_declarado": "Tomá una lectura viva o una carta y proponé su versión condicionada a un régimen detectable en tiempo real (edgelab/research/agente/regimen.py como perilla, o regimen.definicion/actual_desde en la campaña), escrito ANTES de mirar el OOS: qué régimen, por qué el mecanismo depende de él y qué resultado lo refuta.",
    "regimen_cubos": "Tomá las corridas ya medidas (RESULTADO*.md, MEDIDO.md, cubos en data/cubos) y proponé UNA definición de régimen nueva (ventana, días mínimos, estabilidad entre días) para probar en el motor offline contra azar, calidad estática y nulo de signo; escribí antes qué resultado la refuta y qué familia nueva alimentaría la rotación.",
    "meta_etiquetado": "Sobre una señal primaria viva, proponé un filtro secundario (meta-labeling) entrenado sólo con predicciones fuera de pliegue, con su partición de evaluación declarada antes y su conteo de pruebas.",
}


def elegir_lente(historial: list, pistas_vivas: int | None = None) -> str:
    """Rotación con memoria: la lente menos usada; a igualdad, la que más hallazgos dio. historial = [{'lente','hit'}].
    Criterio de Nico (2026-11-09): lo ya descubierto va primero. Mientras haya pistas vivas en el registro de factores, uno de cada dos
    ciclos es `indagar_factor`; el otro sigue la rotación (para no dejar de explorar)."""
    if pistas_vivas is None:
        try:
            from edgelab.research import factores as _F
            pistas_vivas = sum(e["estado"] in ("PISTA_VIVA", "PALANCA_DE_DISENO") for e in _F.cargar())
        except Exception: pistas_vivas = 0
    if pistas_vivas and (not historial or historial[-1].get("lente") != "indagar_factor"): return "indagar_factor"
    uso = {k: 0 for k in LENTES}; hits = {k: 0 for k in LENTES}
    for h in historial:
        if h.get("lente") in uso:
            uso[h["lente"]] += 1; hits[h["lente"]] += int(bool(h.get("hit")))
    return sorted(LENTES, key=lambda k: (uso[k], -hits[k], k))[0]


def directivas(root=None) -> str:
    """Directivas vigentes de Nico (config/autopilot/DIRECTIVAS.md, 2026-10-27): van en cada paquete y nunca se recortan."""
    f = Path(root or Path(__file__).resolve().parents[2]) / "config/autopilot/DIRECTIVAS.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""                 # completas: cualquier corte dejó afuera directivas (4000 → la 9; 8000 → la 12)


# ---- NÚCLEO: lo que el proyecto ya aprendió y NUNCA se recorta (pedido de Nico, 2026-11-09) ---------------------------------
# Antes el paquete tenía un tope de 19.000 caracteres y lo aprendido (errores y guardas, aprendizajes, decisiones) quedaba afuera:
# los agentes repetían errores ya documentados. Ahora cada rol recibe su núcleo completo; lo que se recorta es lo rotativo.
# (clave, ruta, roles que lo reciben: "todos" = cualquier rol con `nucleo: true` en AGENTES.json; "diseño" = proponente y programador)
NUCLEO_FUENTES = [
    ("directivas_de_nico", "config/autopilot/DIRECTIVAS.md", "todos"),
    ("factores_con_ventaja", "docs/research/FACTORES_CON_VENTAJA.md", "todos"),          # lo más valioso descubierto (si existe)
    ("errores_y_guardas", "docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md", "todos"),
    ("decisiones_vigentes", "docs/DECISIONES_20261108.md", "todos"),
    ("decisiones_de_validacion", "docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md", "todos"),
    ("medir_en_r", "docs/research/MEDIR_EN_R_20261102.md", "todos"),
    ("metodo_de_investigacion", "docs/research/METODO_DE_INVESTIGACION.md", "todos"),              # el orden de una idea a una decisión
    ("practicas_de_trabajo", "docs/research/PRACTICAS_DE_TRABAJO_20261110.md", "todos"),          # qué salió bien y mal, con guardas
    ("aprendizajes_espiral", "docs/research/APRENDIZAJES_ESPIRAL.md", "diseño"),
    ("cartera_viva", "docs/CARTERA_VIVA.md", "diseño"),
    ("guia_regimen", "docs/research/GUIA_REGIMEN_PARA_AGENTE_20261107.md", "diseño"),
    ("guia_grilla_masiva", "docs/research/GUIA_GRILLA_MASIVA.md", "codigo"),                    # la usa quien construye (2026-11-10: el método desaconseja grillas grandes)
    ("ideas_externas_indice", "docs/research/ideas_externas/INDICE.md", "diseño"),
]
ROLES_DISENO = ("proponente", "programador", "meta_analista")


def redactar(texto: str) -> str:
    """Deja pasar un documento del repo por `roles.sanitize` sin perder contenido: neutraliza rutas locales y palabras de secreto."""
    from edgelab.autopilot.roles import LOCAL_PATH, SECRET
    t = LOCAL_PATH.sub(lambda m: m.group(1) + "<ruta-local>/", texto)
    return SECRET.sub("<redactado>", t)


def nucleo(rol: str = "proponente", root=None) -> dict:
    """Núcleo de contexto del rol: documentos completos, en orden fijo. Un rol sin `nucleo` en AGENTES.json recibe {}."""
    from edgelab.autopilot import agentes as AG
    if not AG.rol(rol).get("nucleo"): return {}
    r = Path(root or Path(__file__).resolve().parents[2]); out = {}
    for clave, ruta, quien in NUCLEO_FUENTES:
        if quien == "diseño" and rol not in ROLES_DISENO: continue
        if quien == "codigo" and rol != "programador": continue
        f = r / ruta
        if f.exists(): out[clave] = redactar(f.read_text(encoding="utf-8"))
    return out


def con_nucleo(rol: str, entrada: dict, root=None) -> dict:
    """Entrada de un rol + su núcleo (para revisor, revisor2, auditor, abogado, meta_analista). Falla si no entra en su presupuesto."""
    from edgelab.autopilot import agentes as AG
    p = dict(entrada, nucleo_proyecto=nucleo(rol, root)); tope = AG.rol(rol)["contexto_max_chars"]
    n = len(json.dumps(p, ensure_ascii=False))
    if n > tope: raise ValueError(f"la entrada de {rol} ({n} caracteres) no entra en su presupuesto ({tope}): subir contexto_max_chars en AGENTES.json o achicar la entrada, nunca el núcleo")
    return p


def memoria_ideas(semilla: int = 0, root=None, n_hallazgos: int = 3) -> dict:
    """Memoria que se recuerda en TODOS los ciclos (pedido de Nico, 2026-11-08): el índice de ideas externas completo, un reel que rota
    y hallazgos robustos del CerebroSSRN que rotan. Determinista por semilla (día + ciclo); acotado (~3.000 caracteres)."""
    r = Path(root or Path(__file__).resolve().parents[2]); out = dict(indice="", reel=None, hallazgos_ssrn=[], cerebro="corpus/ssrn/cerebro/COMO_USAR.md")
    ind = r / "docs/research/ideas_externas/INDICE.md"
    if ind.exists(): out["indice"] = "\n".join(l for l in ind.read_text(encoding="utf-8").splitlines() if l.startswith("- "))[:1600]
    reels = sorted((r / "docs/research/ideas_externas/reels").glob("*.md"))
    if reels:
        f = reels[semilla % len(reels)]; t = f.read_text(encoding="utf-8")
        i = t.find("## Resumen"); out["reel"] = dict(archivo=str(f.relative_to(r)), extracto=(t[i:] if i >= 0 else t)[:1200])
    h = r / "corpus/ssrn/cerebro/hallazgos_por_mercado.md"
    if h.exists():
        ls = [l for l in h.read_text(encoding="utf-8").splitlines() if l.startswith("- **[alta]**")]
        if ls: out["hallazgos_ssrn"] = [ls[(semilla * 7 + k * 101) % len(ls)][:350] for k in range(n_hallazgos)]
    return out


def armar_paquete(*, tablero: dict, vacios: list, fichas: list, retiradas: list, lente: str, max_chars: int | None = None, cartas=None, memoria=None,
                  rol: str = "proponente", con_nucleo_completo: bool | None = None) -> dict:   # 2026-11-08: 12000 no dejaba entrar las cartas con las directivas 9–10
    """Determinista y acotado. Recorta por prioridad: primero fichas, después vacíos, después cartas de la gramática
    (edgelab/research/agente/gramatica.py: coordenadas lejos de lo medido, sin resultados); prioridades y lente nunca se recortan."""
    from edgelab.autopilot import agentes as AG
    if con_nucleo_completo is None: con_nucleo_completo = max_chars is None           # un tope explícito (tests, diagnósticos) = paquete liviano
    max_chars = max_chars or AG.rol(rol)["contexto_max_chars"]
    nuc = nucleo(rol) if con_nucleo_completo else {}
    p = dict(prioridades=PRIORIDADES, directivas_de_nico=nuc.pop("directivas_de_nico", None) or directivas(), nucleo_proyecto=nuc, lente=dict(nombre=lente, consigna=LENTES[lente]), tablero=tablero,
             cartas_gramatica=[dict(id=c["id"], coordenadas=c["coordenadas"], cercana_medida=c.get("cercana_medida"), paridad=c.get("paridad"))
                               for c in (cartas or [])],
             friccion=__import__('edgelab.autopilot.friccion', fromlist=['x']).tabla_para_contexto(),
             memoria_ideas=memoria if memoria is not None else memoria_ideas(),
             vacios=list(vacios), fichas=list(fichas), prohibido=dict(familias_retiradas=list(retiradas),
             reglas=["no abrir holdout", "no P&L sin pre-registro publicado y doble revisión (la aprobación es del agente, no de un humano)", "a lo sumo 3 parámetros libres por hipótesis puntual; un barrido masivo declara todas sus perillas y registra todas sus celdas", "el código nuevo lo escribe el programador (pedido_codigo), dentro de su perímetro y con tests"]))
    while len(json.dumps(p, ensure_ascii=False)) > max_chars and (p["fichas"] or p["vacios"] or p["cartas_gramatica"]):
        (p["fichas"] or p["vacios"] or p["cartas_gramatica"]).pop()
    while len(json.dumps(p, ensure_ascii=False)) > max_chars and p["memoria_ideas"].get("hallazgos_ssrn"):
        p["memoria_ideas"]["hallazgos_ssrn"].pop()                       # la memoria se recorta última y el índice nunca
    if con_nucleo_completo and len(json.dumps(p, ensure_ascii=False)) > max_chars:
        raise ValueError(f"el núcleo de {rol} no entra en {max_chars} caracteres: subir contexto_max_chars en config/autopilot/AGENTES.json")
    return p


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-záéíóúñ0-9]+", s.lower()) if len(t) > 3}


def novedad(propuesta: dict, existentes: list, umbral: float = 0.6):
    """Jaccard de términos de familia+mecanismo contra lo existente y lo retirado. Devuelve (es_nueva, parecida_a, similitud)."""
    a = _tokens(propuesta.get("familia", "") + " " + propuesta.get("mecanismo", ""))
    best = (None, 0.0)
    for e in existentes:
        b = _tokens(e)
        s = len(a & b) / len(a | b) if a | b else 0.0
        if s > best[1]: best = (e, s)
    return best[1] < umbral, best[0], round(best[1], 3)


def proponer(runner, paquete: dict, existentes: list) -> dict:
    r = runner.call("proponente", paquete)
    if r.get("status") not in ("OK", "CACHED"):
        return dict(status=r.get("status"), borrador=None)
    nueva, parecida, sim = novedad(r["output"], existentes)
    if not nueva:
        return dict(status="DESCARTADA_POR_REPETIDA", parecida_a=parecida, similitud=sim, borrador=r["output"])
    return dict(status="BORRADOR_NO_AUTORIZADO", lente=paquete["lente"]["nombre"], borrador=r["output"],
                siguiente="redactar pre-registro, committearlo y promover a mano (tools/autopilot_generate.py promote)")
