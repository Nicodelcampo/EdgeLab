"""Glosario bilingue es<->en de trading/microestructura para expansion deterministica de consultas.

Los hallazgos del corpus SSRN estan en castellano y los pasajes en ingles: sin expansion, una consulta en
castellano no encuentra pasajes. Lista cerrada y versionada (sin modelos): agregar terminos es un cambio de
codigo revisable, y el benchmark de `tests/test_edge_brain_passage_search.py` mide su efecto.
"""
from __future__ import annotations

import re
import unicodedata

# frase castellana -> frase inglesa (ambas sin tildes, minusculas). Frases multi-palabra primero.
ES_EN: dict[str, str] = {
    "libro de ordenes": "order book", "flujo de ordenes": "order flow", "orden limite": "limit order",
    "ordenes limite": "limit orders", "orden de mercado": "market order", "reversion a la media": "mean reversion",
    "arbitraje estadistico": "statistical arbitrage", "alta frecuencia": "high frequency",
    "aprendizaje por refuerzo": "reinforcement learning", "aprendizaje automatico": "machine learning",
    "aprendizaje profundo": "deep learning", "costos de transaccion": "transaction costs",
    "costo de transaccion": "transaction cost", "creador de mercado": "market maker",
    "creacion de mercado": "market making", "rango de apertura": "opening range",
    "impacto de mercado": "market impact", "impacto en precio": "price impact",
    "seguimiento de tendencia": "trend following", "punto de control": "point of control",
    "perfil de volumen": "volume profile", "precio medio": "midprice", "series de tiempo": "time series",
    "fuera de muestra": "out of sample", "dentro de muestra": "in sample",
    "desbalance": "imbalance", "desequilibrio": "imbalance", "ejecucion": "execution",
    "deslizamiento": "slippage", "volatilidad": "volatility", "liquidez": "liquidity",
    "cointegracion": "cointegration", "pares": "pairs", "arbitraje": "arbitrage", "microestructura": "microstructure",
    "intradia": "intraday", "tendencia": "trend", "ruptura": "breakout", "regimen": "regime",
    "regimenes": "regimes", "futuros": "futures", "acciones": "equities", "riesgo": "risk",
    "rentabilidad": "profitability", "retornos": "returns", "retorno": "return", "sobreajuste": "overfitting",
    "sesgo": "bias", "regulacion": "regulation", "apertura": "opening", "cierre": "close", "diferencial": "spread",
    "horquilla": "spread", "profundidad": "depth", "absorcion": "absorption", "agotamiento": "exhaustion",
    "estrategia": "strategy", "estrategias": "strategies", "senal": "signal", "senales": "signals",
    "prediccion": "prediction", "pronostico": "forecasting", "cartera": "portfolio", "subasta": "auction",
    "comisiones": "fees", "costos": "costs", "momento": "momentum", "toxicidad": "toxicity",
    "informado": "informed", "manipulacion": "manipulation", "criptomonedas": "cryptocurrency",
    "rendimiento": "performance", "robustez": "robustness", "validacion": "validation",
    # siglas habituales -> forma larga (asi "HFT" encuentra "alta frecuencia" y viceversa)
    "hft": "high frequency trading", "ofi": "order flow imbalance", "lob": "limit order book",
    "poc": "point of control", "vpin": "volume synchronized probability of informed trading",
    "orb": "opening range breakout", "twap": "time weighted average price",
    "vwap": "volume weighted average price", "pnl": "profit and loss",
}
EN_ES: dict[str, str] = {}
for _es, _en in ES_EN.items():
    EN_ES.setdefault(_en, _es)

_WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset({
    "a", "al", "de", "del", "el", "en", "la", "las", "los", "un", "una", "y", "o", "con", "por", "para", "que",
    "se", "su", "sus", "es", "son", "lo", "como", "mas", "sin", "sobre", "entre",
    "the", "of", "to", "and", "or", "in", "on", "for", "with", "is", "are", "by", "an", "as", "at", "from",
    "this", "that", "be", "it", "its", "do", "does", "how", "what",
})


def fold(text: str) -> str:
    """minusculas y sin tildes (ejecucion == ejecución)."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def expand_query(query: str) -> list[str]:
    """Terminos de la consulta + traducciones del glosario, deduplicados y en orden estable."""
    q = " " + " ".join(_WORD.findall(fold(query))) + " "
    phrases: list[str] = []
    for table in (ES_EN, EN_ES):
        for src in sorted(table, key=len, reverse=True):
            if f" {src} " in q:
                phrases.append(table[src])
    terms: list[str] = []
    for chunk in [q] + phrases:
        for w in _WORD.findall(chunk):
            if w not in STOPWORDS and len(w) > 1 and w not in terms:
                terms.append(w)
    return terms


def expand_phrases(query: str) -> list[str]:
    """Frases multi-palabra a buscar como tales: traducciones del glosario + bigramas de la consulta."""
    q = " " + " ".join(_WORD.findall(fold(query))) + " "
    out: list[str] = []
    for table in (ES_EN, EN_ES):
        for src in sorted(table, key=len, reverse=True):
            if f" {src} " in q:
                for ph in (src, table[src]):
                    if " " in ph and ph not in out:
                        out.append(ph)
    words = [w for w in q.split() if w not in STOPWORDS and len(w) > 1]
    for a, b in zip(words, words[1:]):
        ph = f"{a} {b}"
        if ph not in out:
            out.append(ph)
    return out
