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
import json, re

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
    "Fills pasivos sólo por replay tick a tick con máquina de estados causal (espera acotada, cancelación si el precio escapa, excursiones medidas después del fill, stop primero): el modelo 'tocó el precio en la ventana' infló ~0,6 ticks/op en ES (k32). Una partición es réplica sólo si el registro de la familia la declara sin usar. Un gate diseñado después de ver la pérdida es una prueba nueva.",
]
LENTES = {
    "puente_mecanismo": "Llevá un hallazgo de información ya medido a un mecanismo económico publicado que lo explique y predecí algo nuevo.",
    "replica_debil": "Tomá una pista débil y diseñá su réplica en una muestra que todavía no se usó.",
    "artefacto": "Buscá el artefacto más probable detrás del resultado más sospechoso del tablero (microestructura, rebote bid-ask, look-ahead).",
    "otro_instrumento": "Trasladá el efecto más robusto a otro instrumento o escala sin cambiar a la vez la métrica.",
    "abogado_del_diablo": "Formulá la hipótesis que, si es cierta, explicaría el éxito más fuerte SIN que sea un edge. Que sea refutable.",
    "costo_y_ejecucion": "Diseñá la medición que decide si el mejor efecto vivo puede pagar costos reales (spread, comisión, slippage).",
    "ingenieria_inversa": "Tomá un resultado ya medido (ganadoras vs. perdedoras, o eventos que el detector descartó) y preguntá qué estado previo lo habría anticipado. Lo que encuentres es una HIPÓTESIS nueva: debe probarse en una muestra que no participó del hallazgo, nunca en la misma.",
    "hueco_gramatica": "Tomá UNA de las cartas_gramatica (coordenadas lejos de lo ya medido, elegidas sin mirar resultados) y convertila en familia: mecanismo económico, espacio de eventos enumerado, régimen declarado ex ante y perillas del barrido. Si ninguna tiene un mecanismo plausible, decilo y proponé la variante más cercana que sí lo tenga.",
    "regimen_declarado": "Tomá una lectura viva o una carta y proponé su versión condicionada a un régimen detectable en tiempo real (edgelab/research/agente/regimen.py como perilla, o regimen.definicion/actual_desde en la campaña), escrito ANTES de mirar el OOS: qué régimen, por qué el mecanismo depende de él y qué resultado lo refuta.",
    "meta_etiquetado": "Sobre una señal primaria viva, proponé un filtro secundario (meta-labeling) entrenado sólo con predicciones fuera de pliegue, con su partición de evaluación declarada antes y su conteo de pruebas.",
}


def elegir_lente(historial: list) -> str:
    """Rotación con memoria: la lente menos usada; a igualdad, la que más hallazgos dio. historial = [{'lente','hit'}]."""
    uso = {k: 0 for k in LENTES}; hits = {k: 0 for k in LENTES}
    for h in historial:
        if h.get("lente") in uso:
            uso[h["lente"]] += 1; hits[h["lente"]] += int(bool(h.get("hit")))
    return sorted(LENTES, key=lambda k: (uso[k], -hits[k], k))[0]


def armar_paquete(*, tablero: dict, vacios: list, fichas: list, retiradas: list, lente: str, max_chars: int = 12000, cartas=None) -> dict:
    """Determinista y acotado. Recorta por prioridad: primero fichas, después vacíos, después cartas de la gramática
    (edgelab/research/agente/gramatica.py: coordenadas lejos de lo medido, sin resultados); prioridades y lente nunca se recortan."""
    p = dict(prioridades=PRIORIDADES, lente=dict(nombre=lente, consigna=LENTES[lente]), tablero=tablero,
             cartas_gramatica=[dict(id=c["id"], coordenadas=c["coordenadas"], cercana_medida=c.get("cercana_medida"), paridad=c.get("paridad"))
                               for c in (cartas or [])],
             friccion=__import__('edgelab.autopilot.friccion', fromlist=['x']).tabla_para_contexto(),
             vacios=list(vacios), fichas=list(fichas), prohibido=dict(familias_retiradas=list(retiradas),
             reglas=["no abrir holdout", "no P&L sin pre-registro publicado y doble revisión (la aprobación es del agente, no de un humano)", "a lo sumo 3 parámetros libres por hipótesis puntual; un barrido masivo declara todas sus perillas y registra todas sus celdas", "el código nuevo lo escribe el programador (pedido_codigo), dentro de su perímetro y con tests"]))
    while len(json.dumps(p, ensure_ascii=False)) > max_chars and (p["fichas"] or p["vacios"] or p["cartas_gramatica"]):
        (p["fichas"] or p["vacios"] or p["cartas_gramatica"]).pop()
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
