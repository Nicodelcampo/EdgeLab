"""Gramática de hipótesis del agente (2026-10-24): un espacio EXPLÍCITO de estrategias para proponer con diversidad y sin repetir.

Pedido de Nico: «maximizar la creatividad del agente del Debian, derivado del abanico de posibilidades a mano… con rigurosidad».
Creatividad acá = cubrir el espacio de lo que se puede probar con lo que ya existe (indicadores con paridad, primitivas de precio,
fuentes, simulador, embudo), lejos de lo ya medido, en vez de variar la última idea. Rigor = cada carta sale con los campos que
las reglas del proyecto exigen ANTES de correr (justificación económica, cómo podría refutarse, espacio de eventos enumerado,
régimen declarado ex ante, fricción, conteo de celdas) y la elección entre cartas NO mira ningún resultado de P&L: sólo
novedad, diversidad y viabilidad frente a la fricción. Una carta no es una prueba: no consume multiplicidad hasta que su campaña
se registra en el contador global.

Uso:
    from edgelab.research.agente import gramatica as G
    for c in G.cartas(n=8, semilla=20261024): print(c["id"], c["coordenadas"])
    python -m edgelab.research.agente.gramatica 8          # las mismas cartas, en JSON
Los ejes y la cobertura viven en este archivo (perímetro del agente): agregar un valor a un eje o una familia medida es un
cambio de una línea con su test.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys

import numpy as np

# --------------------------------------------------------------------------------------------------------------- ejes
# Cada eje: valor -> descripción corta (lo que el experimento tendría que implementar). Orden = orden de la coordenada.
EJES = {
    "objeto": {
        "LUX-IMB": "zonas OG/VI del Imbalance Detector (PASS, NQ M1)",
        "aVolClusterPOI": "clusters de volumen POI (PASS, MNQ 50t/200t)",
        "aVolZonePOI2": "zonas, order blocks y racimos de volumen (PASS, MNQ 25t/200t)",
        "VolTicksDef": "barras de volumen por ticks, delta/defensa (PASS, MNQ 150t)",
        "HFTZonesNQ": "zonas HFT de NQ (PASS, HP-007 V2)",
        "HFTZones2": "zonas HFT v2 (PASS, ramas cubiertas)",
        "BigTrap2": "vela creadora extrema / trampa (PASS_CON_CAVEAT; imán CERRADO)",
        "expansion": "impulso de precio >= R·ATR desde el extremo de una ventana (primitiva de precio)",
        "rango_apertura": "rango de los primeros minutos de una sesión o bloque (ORB)",
        "extremos_previos": "máximo/mínimo de la sesión anterior, de la semana o del overnight",
        "vwap": "VWAP de la sesión y sus bandas de desvío",
        "perfil_volumen": "POC / nodos de alto y bajo volumen del perfil de la sesión anterior",
        "franja_horaria": "momento fijo del día (slot), sin objeto de precio",
        "divergencia_activos": "señal en un activo, ejecución en otro (CFD -> futuro, ES <-> NQ, oro spot -> GC)",
    },
    "evento": {   # regla de población del CLAUDE.md: se enumeran TODAS antes de congelar una
        "creacion": "nace el objeto",
        "aproximacion": "el precio se acerca a menos de d del objeto",
        "primer_toque": "primer contacto después de nacer",
        "toque_n": "n-ésimo contacto (n >= 2)",
        "invalidacion": "el precio lo atraviesa / lo rompe",
        "expiracion": "vence por tiempo sin tocarse",
        "confluencia": "dos o más objetos coinciden en precio o tiempo",
        "estado_continuo": "en cada vela: distancia, cantidad activa, posición relativa (estado, no evento)",
    },
    "lectura": {
        "continuacion": "a favor del movimiento que creó el objeto",
        "reversion": "en contra: vuelta al origen / al valor",
        "ruptura": "a favor de la ruptura del objeto",
        "trampa": "falla de ruptura: entra en contra de la ruptura fallida",
        "iman": "revisita: el objeto atrae el precio (objetivo, no entrada)",
    },
    "regimen": {   # declarado ex ante como perilla (edgelab/research/agente/regimen.py); "ninguno" = incondicional
        "ninguno": "sin condición de régimen",
        "vol_ahora": "ATR reciente relativo a la sesión anterior (tercios)",
        "vol_diaria": "rango de la sesión anterior relativo a 20 sesiones (tercios)",
        "eficiencia": "tendencia vs rango en 60 velas (tercios)",
        "tendencia_dia": "dirección y tamaño del día hasta k (tercios)",
        "actividad": "volumen de 30 velas relativo a la sesión anterior (tercios)",
        "hora": "bloque UTC (Asia / Europa / NY / cierre)",
        "dia": "día de la semana",
    },
    "entrada": {
        "E1C": "a mercado al cierre de la vela de decisión",
        "E1A": "a mercado en el primer tick de la vela siguiente",
        "limite_retroceso": "límite tras un retroceso de x % del recorrido",
        "espera_volumen": "esperar a que se haga volumen (>= q × mediana) antes de entrar",
        "confirmacion": "esperar que la vela siguiente cierre a favor",
    },
    "salida": {
        "estructural": "objetivo y stop en niveles del objeto (borde, medio, extremo)",
        "multiplo_R": "objetivo en múltiplos de la distancia al stop",
        "tiempo": "salida por tiempo fijo (sin objetivo)",
        "trailing": "stop que sigue la estructura (último mínimo/máximo de n velas)",
    },
    "horizonte": {
        "minutos": "<= 15 min (sólo si el movimiento esperado >= 3x fricción)",
        "intradia": "15 min a 4 h",
        "sesion": "hasta el cierre de la sesión",
        "multisesion": "varias sesiones (overnight incluido: declarar el riesgo de hueco)",
    },
    "instrumento": {
        "NQ": "futuro (costo medido)", "ES": "futuro (costo medido)", "YM": "futuro (costo medido)", "RTY": "futuro (costo medido)",
        "GC": "futuro (costo medido)", "6E": "futuro (costo medido)", "MBT": "futuro (costo medido)",
        "DK:USATECHIDXUSD->NQ": "señal en el CFD, operación en NQ", "DK:XAUUSD->GC": "señal en oro spot, operación en GC",
    },
}
EJES_ORDEN = tuple(EJES)

# Combinaciones que no tienen sentido (objeto sin precio no tiene toques; un estado no tiene «primer toque»).
SIN_TOQUES = {"franja_horaria", "divergencia_activos"}
EVENTOS_DE_TOQUE = {"aproximacion", "primer_toque", "toque_n", "invalidacion", "expiracion"}

# --------------------------------------------------------------------------------------------------- cobertura medida
# Lo ya medido (registro global + MEDIDO/NO MEDIDO), en coordenadas de la gramática. None = comodín (el eje no definía la familia).
# estado: MUERTA (no se repropone igual), SIN_POTENCIA (viva: más datos, no otra variante), VIVA (en embudo: no duplicar),
# MEDIDA (ya tiene pruebas en el registro global; su veredicto está en su acta, no acá). Lista PARCIAL: al cerrar cada campaña se
# agrega su línea (playbook §6). Sólo se marca MUERTA / SIN_POTENCIA lo que dice un acta citada en `ref`.
MEDIDO = [
    dict(familia="BIGTRAP2_IMAN", estado="MUERTA", c=dict(objeto="BigTrap2", evento="creacion", lectura="iman"),
         ref="docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md"),
    dict(familia="BIGTRAP2_SOPORTE", estado="MUERTA", c=dict(objeto="BigTrap2", evento="primer_toque", lectura="reversion"),
         ref="CLAUDE.md (≈96 % de ruptura)"),
    dict(familia="HFTZONES_ES", estado="SIN_POTENCIA", c=dict(objeto="HFTZonesNQ", evento="primer_toque", instrumento="ES"),
         ref="docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md"),
    dict(familia="AREAS_EXP_1", estado="MEDIDA", c=dict(objeto="LUX-IMB", evento="confluencia", lectura="reversion", instrumento="NQ"),
         ref="docs/research/areas_expansion_20261022/"),
    dict(familia="AREAS_EXP_1_CRUZADO (U1)", estado="VIVA", c=dict(objeto="LUX-IMB", evento="confluencia", lectura="reversion",
         instrumento="DK:USATECHIDXUSD->NQ"), ref="docs/research/DESCUBRIMIENTO_U1_CRUZADO_REGISTRO.md"),
    dict(familia="EXPANSION_ZONAS", estado="VIVA", c=dict(objeto="expansion", evento="creacion", instrumento="NQ"),
         ref="docs/research/expansion_zonas_20261023/SPEC.md"),
    dict(familia="LUXIMB_FADE_VISOR", estado="MEDIDA", c=dict(objeto="LUX-IMB", evento="primer_toque", lectura="reversion", instrumento="NQ"),
         ref="docs/research/luximb_parity_20261020/"),
    dict(familia="LUXIMB_IMPULSOS", estado="MEDIDA", c=dict(objeto="LUX-IMB", evento="creacion", lectura="continuacion", instrumento="NQ"),
         ref="docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"),
    dict(familia="AVZP2_RACIMOS", estado="MEDIDA", c=dict(objeto="aVolZonePOI2", evento="confluencia", lectura="continuacion"),
         ref="docs/research/AVZP2_RACIMO_REPLICA_ES_NQ_RESULTADOS_20261014.md"),
    dict(familia="TIME_SLOT_HOLD_COND_SCAN", estado="MEDIDA", c=dict(objeto="franja_horaria", evento="estado_continuo", salida="tiempo"),
         ref="docs/research/TRIAL_REGISTRY_GLOBAL.jsonl (barrido_horario_20261004)"),
    dict(familia="ORB0100 / ORB_HORARIOS", estado="MEDIDA", c=dict(objeto="rango_apertura", evento="invalidacion", lectura="ruptura"),
         ref="docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"),
    dict(familia="AVOLCLUSTERPOI_EF0", estado="MEDIDA", c=dict(objeto="aVolClusterPOI", evento="primer_toque"),
         ref="docs/research/AVOLCLUSTERPOI_EF0_KAGGLE_RUN_2026-09-01.md"),
]

# Paridad: un indicador PASS vale en el instrumento y la resolución de su evidencia (config/autopilot/indicadores.json); en otro
# instrumento pide su propio oráculo antes de un barrido. Las primitivas de precio son causales por construcción (test_causal).
PRIMITIVAS = {"expansion", "rango_apertura", "extremos_previos", "vwap", "perfil_volumen", "franja_horaria", "divergencia_activos"}
PARIDAD_EN = {"LUX-IMB": {"NQ", "DK:USATECHIDXUSD->NQ"}, "aVolClusterPOI": {"NQ"}, "aVolZonePOI2": {"NQ"}, "VolTicksDef": {"NQ"},
              "HFTZonesNQ": {"NQ"}}
PESO_SIN_PARIDAD = 0.6

# Viabilidad frente a la fricción (principio de Nico: macro antes que micro). Peso multiplicativo en el puntaje, no un filtro.
PESO_HORIZONTE = {"minutos": 0.35, "intradia": 1.0, "sesion": 1.0, "multisesion": 0.8}


def compatible(c: dict) -> bool:
    if c["objeto"] in SIN_TOQUES and c["evento"] in EVENTOS_DE_TOQUE: return False
    if c["evento"] == "estado_continuo" and c["entrada"] == "limite_retroceso": return False
    if c["lectura"] == "iman" and c["salida"] == "tiempo": return False                # un imán es un objetivo, no un reloj
    if c["objeto"] == "divergencia_activos" and "->" not in c["instrumento"]: return False
    if c["objeto"] == "BigTrap2" and c["lectura"] == "iman": return False              # cerrado (acta 2026-08-13)
    return True


def paridad_ok(c: dict) -> bool:
    return c["objeto"] in PRIMITIVAS or c["instrumento"] in PARIDAD_EN.get(c["objeto"], set())


def _coincide(c: dict, m: dict) -> bool:
    return all(c.get(k) == v for k, v in m.items() if v is not None)


def medida(c: dict):
    """La familia medida que cubre esta coordenada (o None)."""
    for m in MEDIDO:
        if _coincide(c, m["c"]): return m
    return None


def distancia(a: dict, b: dict) -> int:
    """Hamming sobre los ejes que ambas definen."""
    return sum(1 for k in EJES_ORDEN if k in a and k in b and a[k] != b[k])


def novedad(c: dict) -> int:
    """Distancia a la familia medida más cercana, contando sólo los ejes que esa familia define (lo no definido no la protege)."""
    return min((sum(1 for k, v in m["c"].items() if v is not None and c.get(k) != v) for m in MEDIDO), default=len(EJES_ORDEN))


def _sorteo(rng, n_max):
    """Muestreo uniforme del producto de ejes (el espacio entero es ~10^6: no se enumera)."""
    vals = [list(EJES[k]) for k in EJES_ORDEN]
    for _ in range(n_max):
        yield {k: v[rng.integers(len(v))] for k, v in zip(EJES_ORDEN, vals)}


def tamano_espacio() -> dict:
    total = int(np.prod([len(EJES[k]) for k in EJES_ORDEN]))
    return dict(ejes={k: len(EJES[k]) for k in EJES_ORDEN}, combinaciones=total)


def cartas(n: int = 8, semilla: int = 0, min_dif: int = 3, candidatos: int = 20000, excluir=("MUERTA", "VIVA", "SIN_POTENCIA", "MEDIDA")) -> list:
    """n cartas diversas (cada par difiere en >= min_dif ejes), lejos de lo medido, viables frente a la fricción.
    Greedy max-min sobre un muestreo uniforme: determinista por `semilla`. NO usa resultados: sólo coordenadas."""
    rng = np.random.default_rng(semilla); pool, vistos = [], set()
    for c in _sorteo(rng, candidatos):
        key = tuple(c[k] for k in EJES_ORDEN)
        if key in vistos or not compatible(c): continue
        vistos.add(key); m = medida(c)
        if m is not None and m["estado"] in excluir: continue
        pool.append((novedad(c) * PESO_HORIZONTE[c["horizonte"]] * (1.0 if paridad_ok(c) else PESO_SIN_PARIDAD), float(rng.random()), c))
    pool.sort(key=lambda x: (-x[0], x[1]))                            # a igual puntaje, orden al azar (sembrado): no amontona
    elegidas = []
    for sc, _, c in pool:
        if all(distancia(c, e) >= min_dif for e in elegidas): elegidas.append(c)
        if len(elegidas) >= n: break
    return [ficha(c) for c in elegidas]


def ficha(c: dict) -> dict:
    """La carta con todo lo que la regla del proyecto pide escribir ANTES de correr. Los «COMPLETAR» son obligatorios."""
    cid = "G-" + hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:8]
    otros_eventos = [e for e in EJES["evento"] if e != c["evento"]]
    reg = c["regimen"]
    return dict(
        id=cid, coordenadas=c, descripcion={k: EJES[k][c[k]] for k in EJES_ORDEN},
        cercana_medida=min(MEDIDO, key=lambda m: sum(1 for k, v in m["c"].items() if v is not None and c.get(k) != v))["familia"] if MEDIDO else None,
        novedad=novedad(c),
        justificacion_economica="COMPLETAR: quién pierde plata del otro lado y por qué el efecto no se arbitra (mecanismo, no patrón)",
        como_podria_refutarse="COMPLETAR: resultado concreto que la mata (p. ej. réplica con media <= 0 o el control sin objeto da lo mismo)",
        espacio_de_eventos=dict(elegido=c["evento"], alternativas_consideradas=otros_eventos,
                                por_que_este="COMPLETAR (regla de población: enumerar antes de congelar; evento vs estado)"),
        regimen=dict(perilla=None if reg == "ninguno" else f"edgelab.research.agente.regimen.VARIABLES_REGIMEN['{reg}']",
                     declarado_ex_ante=True,
                     nota="el régimen es una perilla: entra en n_celdas y en la celda congelada; el OOS evalúa la señal SOLO con el "
                          "régimen presente (pocas operaciones = SIN_POTENCIA, no refutación)"),
        friccion=dict(regla="movimiento mediano del objetivo >= 3x la fricción canónica (edgelab/costos.py)", peso_horizonte=PESO_HORIZONTE[c["horizonte"]]),
        paridad="primitiva causal: test_causal" if c["objeto"] in PRIMITIVAS else (
            "evidencia de paridad en este instrumento" if paridad_ok(c) else
            f"SIN evidencia de {c['objeto']} en {c['instrumento']}: pide su oráculo (o usar el instrumento de la evidencia) antes del barrido"),
        controles=["test_control_ruido", "test_control_plantado", "test_causal"] + (["placebo sin objeto"] if c["objeto"] not in SIN_TOQUES else []),
        siguiente="módulo en edgelab/research/agente/ (interfaz grilla_generica §6) + campaña JSON con embudo=true (guía §8); preflight antes",
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8; s = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(json.dumps(dict(espacio=tamano_espacio(), cartas=cartas(n=n, semilla=s)), indent=1, ensure_ascii=False))
