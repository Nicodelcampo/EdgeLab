"""Taxonomía de reglas de prop firms, incluidas las que suelen quedar escondidas en artículos de ayuda, términos y
condiciones o FAQs de retiros.

Cada categoría tiene patrones (regex, inglés y español) y un peso de impacto en la esperanza del participante:
`sim` = afecta directamente al simulador de EV (tiene que modelarse), `filtro` = restringe qué estrategias son
admisibles (una estrategia que la viola no cobra), `costo` = cambia el costo, `info` = contexto.

El inventario clasifica cada oración de cada página en todas las categorías que coinciden (una oración puede tocar
varias) y guarda la fuente. La cobertura por firma marca las categorías **sin evidencia**: una categoría vacía no
significa «no existe la regla», significa «no la encontramos»; hay que buscarla a mano antes de simular.
"""
from __future__ import annotations

import re

C = re.I

CATEGORIES: dict[str, dict] = {
    # --- geometría de la evaluación y la fondeada (sim) ---
    "objetivo_beneficio": dict(impacto="sim", pat=r"profit\s*target|objetivo\s*de\s*(?:beneficio|ganancia)"),
    "drawdown_maximo": dict(impacto="sim", pat=r"max(?:imum)?\s*loss\s*limit|\bMLL\b|max(?:imum)?\s*drawdown|trailing\s*(?:threshold|drawdown)|end[- ]of[- ]day\s*drawdown|\bEOD\b\s*drawdown|intraday\s*(?:trailing\s*)?drawdown|liquidation\s*threshold"),
    "drawdown_bloqueo": dict(impacto="sim", pat=r"(?:lock|stop)s?\s*(?:at|trailing)|no\s*longer\s*trail|stops?\s*trailing|trail(?:ing)?\s*stops?|locked\s*(?:at|to)"),
    "perdida_diaria": dict(impacto="sim", pat=r"daily\s*loss\s*limit|\bDLL\b|daily\s*drawdown|max(?:imum)?\s*daily\s*loss|soft\s*breach|hard\s*breach"),
    "consistencia": dict(impacto="sim", pat=r"consistency|(?:single|one|best)\s*(?:trading\s*)?day\s*(?:can(?:not|'t)|may\s*not|must\s*not)|\d+\s*%\s*of\s*(?:your\s*)?(?:total\s*)?profits?"),
    "dias_minimos": dict(impacto="sim", pat=r"min(?:imum)?\s*(?:of\s*)?\d*\s*(?:trading\s*)?days|trading\s*days?\s*required|at\s*least\s*\d+\s*(?:trading\s*)?days"),
    "dias_ganadores": dict(impacto="sim", pat=r"winning\s*days?|profitable\s*days?|days?\s*(?:of|with)\s*(?:at\s*least\s*)?\$\s?\d+|green\s*days?"),
    "plazo_maximo": dict(impacto="sim", pat=r"no\s*time\s*limit|unlimited\s*time|within\s*\d+\s*(?:calendar\s*|trading\s*)?days|expire[sd]?|time\s*limit"),
    "inactividad": dict(impacto="sim", pat=r"inactiv|dormant|no\s*trad(?:e|ing)\s*(?:for|in)\s*\d+|must\s*trade\s*(?:at\s*least\s*)?(?:once|every)|minimum\s*activity|\d+\s*trades?\s*(?:per|a|every)\s*(?:week|month)|no\s*trading\s*activity|qualifying\s*(?:profit\s*)?days?\s*within"),
    # --- retiros (sim) ---
    "retiro_colchon": dict(impacto="sim", pat=r"buffer|safety\s*net|cushion|minimum\s*balance|above\s*(?:the\s*)?(?:starting|initial)\s*balance|withdrawable"),
    "retiro_frecuencia": dict(impacto="sim", pat=r"payouts?\s*(?:every|each|per|once|weekly|bi-?weekly|monthly|daily)|(?:request|withdraw)\s*(?:a\s*)?payouts?\s*(?:after|every|once)|payout\s*(?:cycle|period|window|schedule)"),
    "retiro_minimo": dict(impacto="sim", pat=r"minimum\s*(?:payout|withdrawal)|payout\s*minimum|withdraw(?:al)?\s*(?:of\s*)?at\s*least|minimum\s*(?:request|withdrawal\s*amount|amount\s*(?:to|you\s*can)\s*(?:request|withdraw))"),
    "retiro_maximo": dict(impacto="sim", pat=r"max(?:imum)?\s*(?:payout|withdrawal)|payout\s*(?:cap|limit)|up\s*to\s*\$\s?[\d,]+\s*(?:per|each)\s*(?:payout|request|withdrawal)|capped|withdrawal\s*(?:cap|limit)|max(?:imum)?\s*(?:you\s*can\s*)?withdraw"),
    "retiro_split": dict(impacto="sim", pat=r"profit\s*split|payout\s*split|keep\s*(?:\d+\s*%|100\s*%)|\d+\s*/\s*\d+\s*split|\d+\s*%\s*of\s*(?:the\s*)?profits?\s*(?:go|are|is)"),
    "retiro_cantidad": dict(impacto="sim", pat=r"(?:number|count)\s*of\s*payouts|after\s*(?:the\s*)?\w+\s*payouts?|first\s*(?:\d+\s*)?payouts?|payouts?\s*(?:1|one)\s*(?:through|to|-)\s*\d+"),
    "cuenta_live": dict(impacto="sim", pat=r"live\s*(?:funded\s*)?account|move(?:d)?\s*to\s*live|live\s*(?:capital|trading)|sim(?:ulated)?\s*funded|express\s*funded|\bXFA\b|\bPA\b\s*account|performance\s*account"),
    "cierre_cuenta": dict(impacto="sim", pat=r"account\s*(?:will\s*be\s*)?(?:closed|terminated|revoked|reset)|close\s*(?:your|the)\s*account|forfeit|terminat(?:e|ion)"),
    # --- tamaño y exposición (sim / filtro) ---
    "contratos_maximos": dict(impacto="sim", pat=r"max(?:imum)?\s*(?:position\s*size|contracts?|lots?)|contract\s*limit|position\s*limit|\d+\s*(?:mini|micro)s?\b|minis?\s*or\s*\d+\s*micros?"),
    "escalado": dict(impacto="sim", pat=r"scaling\s*plan|scale\s*up|scaling\s*rule|half\s*(?:size|contracts)|until\s*(?:you\s*)?(?:reach|exceed)"),
    "riesgo_por_trade": dict(impacto="filtro", pat=r"(?:max(?:imum)?|open)\s*(?:risk|loss)\s*per\s*(?:trade|position)|\d+\s*%\s*(?:of\s*(?:your\s*)?)?(?:the\s*)?(?:trailing\s*)?(?:drawdown|threshold|profit\s*balance)|stop[- ]loss\s*(?:is\s*)?(?:required|mandatory)|must\s*(?:use|have|place)\s*(?:a\s*)?stop|without\s*stop[- ]?loss|mental\s*stop|threshold\s*as\s*a\s*stop|\bMAE\b|maximum\s*adverse"),
    "relacion_riesgo_beneficio": dict(impacto="filtro", pat=r"risk[- ]?(?:to|/|:)[- ]?reward|reward[- ]?(?:to|/|:)[- ]?risk|\d\s*:\s*1\s*(?:ratio|risk)|\bR:R\b|small\s*profit\s*targets?\s*while\s*risking|disproportionate(?:ly)?\s*large|\d+[- ]tick\s*(?:profit\s*target|stop)"),
    "ganancia_extraordinaria": dict(impacto="filtro", pat=r"windfall|single\s*trade\s*(?:profit|accounts?\s*for)|one\s*trade\s*(?:can(?:not|'t)|may\s*not)|(?:largest|biggest)\s*(?:winning\s*)?trade|lucky|all\s*or\s*nothing|lottery"),
    "tiempo_minimo_tenencia": dict(impacto="filtro", pat=r"(?:hold|held|holding)\s*(?:time|for|longer|at\s*least)|minimum\s*(?:hold|holding|duration)|(?:less|under|shorter)\s*than\s*\d+\s*seconds|micro[- ]?scalp|tick\s*scalp|\d+\s*seconds"),
    "noticias": dict(impacto="filtro", pat=r"news\s*(?:event|release|trading)|economic\s*(?:release|calendar|event)|tier\s*1|\bFOMC\b|\bNFP\b|\bCPI\b|high[- ]impact"),
    "horario_y_overnight": dict(impacto="filtro", pat=r"overnight|weekend|hold(?:ing)?\s*(?:positions?\s*)?(?:past|through|over)|flat\s*by|close\s*(?:all\s*)?positions?\s*(?:by|before)|\d{1,2}:\d{2}\s*(?:pm|am)?\s*(?:ct|et|est|cst)|trading\s*hours|market\s*close"),
    "instrumentos": dict(impacto="filtro", pat=r"(?:allowed|permitted|eligible|available|tradable)\s*(?:instruments?|products?|contracts?|markets?)|(?:only|cannot)\s*trade\s*(?:the\s*)?(?:following|CME|micro)|restricted\s*(?:products?|instruments?)"),
    "estrategias_prohibidas": dict(impacto="filtro", pat=r"prohibited|not\s*(?:allowed|permitted)|banned|forbidden|strictly\s*prohibited|may\s*not\s*be\s*used|violat(?:e|ion|ing)|abus(?:e|ive)|exploit"),
    "cobertura_y_copy": dict(impacto="filtro", pat=r"hedg(?:e|ing)|opposite\s*(?:positions?|direction)|copy\s*trad(?:e|ing|er)|trade\s*copier|group\s*trading|mirror|multiple\s*accounts?|same\s*strategy\s*across"),
    "bots_y_automatizacion": dict(impacto="filtro", pat=r"\bbots?\b|automat(?:ed|ion)|algorithm(?:ic)?|\bEAs?\b|expert\s*advisor|\bHFT\b|high[- ]frequency|latency|arbitrage"),
    "martingala_y_promediar": dict(impacto="filtro", pat=r"martingale|grid\s*trading|averag(?:e|ing)\s*down|add(?:ing)?\s*to\s*(?:a\s*)?losing|dollar[- ]cost|\bDCA\b|pyramid"),
    "cuentas_maximas": dict(impacto="filtro", pat=r"max(?:imum)?\s*(?:of\s*)?\d+\s*(?:funded\s*|active\s*|evaluation\s*|PA\s*)?accounts|up\s*to\s*\d+\s*(?:funded\s*|active\s*|live\s*)?(?:accounts|PAs)|account\s*limit|\d+\s*(?:evaluations|PAs)\b|per\s*household|multiple\s*(?:user\s*)?accounts|stockpil"),
    "discrecional_firma": dict(impacto="filtro", pat=r"sole\s*discretion|at\s*(?:our|its)\s*discretion|reserve[s]?\s*the\s*right|without\s*notice|any\s*reason|deem(?:s|ed)?\s*(?:to\s*be\s*)?(?:inappropriate|abusive|gambling)|gambl"),
    "kyc_y_jurisdiccion": dict(impacto="filtro", pat=r"\bKYC\b|identity\s*verification|restricted\s*(?:countries|jurisdictions)|residents?\s*of|sanction|age\s*(?:of\s*)?18|VPN|IP\s*address|device"),
    # --- costos ---
    "cuota": dict(impacto="costo", pat=r"(?:per|/)\s*mo(?:nth)?\b|monthly\s*(?:fee|subscription)|one[- ]time\s*(?:fee|payment)|evaluation\s*(?:fee|price|cost)|subscription"),
    "activacion_y_reset": dict(impacto="costo", pat=r"activation\s*fee|reset\s*(?:fee|price|cost)|reactivat|re-?set\s*your\s*account"),
    "comisiones_y_datos": dict(impacto="costo", pat=r"commission|round[- ]?turn|per\s*side|\bRT\b\s*fee|exchange\s*fees?|data\s*fee|market\s*data|platform\s*fee|NinjaTrader|Rithmic|Tradovate"),
}
_COMP = {k: re.compile(v["pat"], C) for k, v in CATEGORIES.items()}
_NUM = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?[kK]?|\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\s?(?:seconds?|minutes?|days?|contracts?|minis?|micros?|payouts?|accounts?)\b|\b\d{1,2}:\d{2}\b|\b\d+\s*:\s*\d+\b", C)
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])|\s{2,}|\s+•\s+|\s+·\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if 25 <= len(s.strip()) <= 700]


def classify(text: str) -> list[dict]:
    """Oraciones con las categorías que tocan y los números que contienen."""
    out = []
    for s in sentences(text):
        cats = [k for k, rx in _COMP.items() if rx.search(s)]
        if cats:
            out.append(dict(texto=s, categorias=cats, numeros=[m.group(0).strip() for m in _NUM.finditer(s)]))
    return out


def coverage(items: list[dict]) -> dict[str, int]:
    cov = {k: 0 for k in CATEGORIES}
    for it in items:
        for c in it["categorias"]:
            cov[c] += 1
    return cov
