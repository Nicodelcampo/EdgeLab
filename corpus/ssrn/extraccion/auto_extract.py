#!/usr/bin/env python
"""
Automated extraction script for pending papers in CerebroSSRN.
Generates baseline JSONs for papers that haven't been extracted yet.
Uses keyword/title matching from the ontology + abstract extraction.
Not as good as manual LLM extraction, but fills the dataset so pipeline can run.
"""
import json
import os
import re
import sys

BASE = os.getcwd()  # Should be C:\$ACerebroSSRN
DOCS_FILE = os.path.join(BASE, "extraccion", "docs_list.json")
MANIFEST_FILE = os.path.join(BASE, "Normalizado", "manifest.json")
NORMALIZADO_DIR = os.path.join(BASE, "Normalizado", "documentos")
COMPLETO_DIR = os.path.join(BASE, "extraccion", "completo")

# Ontology seed - keywords to concepts mapping
ONTOLOGY = {
    "order flow imbalance": ("concepto", "order flow imbalance"),
    "limit order book": ("concepto", "limit order book"),
    "market making": ("estrategia", "market making"),
    "adverse selection": ("fenomeno", "adverse selection"),
    "inventory risk": ("fenomeno", "inventory risk"),
    "bid-ask spread": ("concepto", "bid-ask spread"),
    "microprice": ("concepto", "microprice"),
    "queue position": ("concepto", "queue position"),
    "tick size": ("concepto", "tick size"),
    "market impact": ("concepto", "market impact"),
    "optimal execution": ("estrategia", "optimal execution"),
    "VWAP": ("metrica", "VWAP"),
    "implementation shortfall": ("metrica", "implementation shortfall"),
    "Almgren-Chriss": ("estrategia", "Almgren-Chriss framework"),
    "Avellaneda-Stoikov": ("estrategia", "Avellaneda-Stoikov model"),
    "Hawkes process": ("metodo", "Hawkes process"),
    "price discovery": ("fenomeno", "price discovery"),
    "informed trading": ("fenomeno", "informed trading"),
    "PIN": ("metrica", "PIN"),
    "effective spread": ("metrica", "effective spread"),
    "realized spread": ("metrica", "realized spread"),
    "momentum": ("fenomeno", "momentum"),
    "mean reversion": ("fenomeno", "mean reversion"),
    "statistical arbitrage": ("estrategia", "statistical arbitrage"),
    "pairs trading": ("estrategia", "pairs trading"),
    "cointegration": ("metodo", "cointegration"),
    "Ornstein-Uhlenbeck": ("metodo", "Ornstein-Uhlenbeck process"),
    "Kalman filter": ("metodo", "Kalman filter"),
    "regime switching": ("metodo", "regime switching"),
    "hidden Markov model": ("metodo", "hidden Markov model"),
    "GARCH": ("metodo", "GARCH"),
    "realized volatility": ("metrica", "realized volatility"),
    "volatility clustering": ("fenomeno", "volatility clustering"),
    "intraday seasonality": ("fenomeno", "intraday seasonality"),
    "high-frequency trading": ("estrategia", "high-frequency trading"),
    "latency": ("concepto", "latency"),
    "liquidity provision": ("estrategia", "liquidity provision"),
    "liquidity taking": ("estrategia", "liquidity taking"),
    "market microstructure": ("concepto", "market microstructure"),
    "tick data": ("dato", "tick data"),
    "trade sign": ("metodo", "trade sign"),
    "Lee-Ready": ("metodo", "Lee-Ready algorithm"),
    "order book depth": ("concepto", "order book depth"),
    "support and resistance": ("concepto", "support and resistance"),
    "technical analysis": ("metodo", "technical analysis"),
    "transaction costs": ("concepto", "transaction costs"),
    "slippage": ("concepto", "slippage"),
    "backtest overfitting": ("riesgo_metodologico", "backtest overfitting"),
    "data snooping": ("riesgo_metodologico", "data snooping"),
    "look-ahead bias": ("riesgo_metodologico", "look-ahead bias"),
    "survivorship bias": ("riesgo_metodologico", "survivorship bias"),
    "walk-forward": ("metodo", "walk-forward validation"),
    "Sharpe ratio": ("metrica", "Sharpe ratio"),
    "maximum drawdown": ("metrica", "maximum drawdown"),
    "position sizing": ("estrategia", "position sizing"),
    "feature importance": ("metodo", "feature importance"),
    "random forest": ("metodo", "random forest"),
    "gradient boosting": ("metodo", "gradient boosting"),
    "LSTM": ("metodo", "LSTM"),
    "reinforcement learning": ("metodo", "reinforcement learning"),
    "deep learning": ("metodo", "deep learning"),
    "machine learning": ("metodo", "machine learning"),
    "large language model": ("metodo", "large language models"),
    "NLP": ("metodo", "NLP"),
    "sentiment analysis": ("metodo", "sentiment analysis"),
    "GAN": ("metodo", "GAN"),
    "transformer": ("metodo", "transformer"),
    "convolutional neural": ("metodo", "convolutional neural network"),
    "LSTM": ("metodo", "LSTM"),
    "PCA": ("metodo", "PCA"),
    "Monte Carlo": ("metodo", "Monte Carlo simulation"),
    "stochastic optimal control": ("metodo", "stochastic optimal control"),
    "HJB": ("metodo", "Hamilton-Jacobi-Bellman equation"),
    "Brownian motion": ("metodo", "Brownian motion"),
    "futures roll": ("concepto", "futures roll"),
    "lead-lag": ("fenomeno", "lead-lag effect"),
    "ETF": ("concepto", "ETF"),
    "cryptocurrency": ("concepto", "cryptocurrency"),
    "bitcoin": ("concepto", "cryptocurrency"),
    "FX": ("concepto", "foreign exchange"),
    "insider trading": ("fenomeno", "insider trading"),
    "manipulation": ("fenomeno", "market manipulation"),
    "spoofing": ("fenomeno", "spoofing"),
    "front running": ("fenomeno", "front running"),
    "Dark pool": ("concepto", "dark pool"),
    "MiFID": ("metodo", "MiFID II"),
    "regulation": ("concepto", "financial regulation"),
    "no-arbitrage": ("concepto", "no-arbitrage pricing"),
    "martingale": ("metodo", "martingale pricing"),
    "asset pricing": ("metodo", "asset pricing"),
    "stochastic volatility": ("concepto", "stochastic volatility"),
    "rough volatility": ("concepto", "rough volatility"),
    "option pricing": ("concepto", "option pricing"),
    "delta hedging": ("estrategia", "delta hedging"),
    "deep hedging": ("estrategia", "deep hedging"),
    "VaR": ("metrica", "Value at Risk"),
    "Expected Shortfall": ("metrica", "Expected Shortfall"),
    "tail risk": ("fenomeno", "tail risk"),
    "black swan": ("fenomeno", "black swan events"),
    "model risk": ("riesgo_metodologico", "model risk"),
    "mean field game": ("metodo", "mean field games"),
    "doubl": ("metodo", "causal inference"),
    "causal": ("metodo", "causal inference"),
    "blockchain": ("concepto", "blockchain"),
    "electricit": ("concepto", "electricity market"),
    "power": ("concepto", "electricity market"),
}


def extract_title(lines):
    """Extract title from first ~15 non-empty lines."""
    candidates = []
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # Skip obvious non-title lines
        if line.startswith("Electronic copy") or line.startswith("SSRN"):
            continue
        if "Abstract" in line and len(line) < 20:
            break
        candidates.append(line)
    
    if candidates:
        # Return the longest non-header line
        best = max(candidates[:5], key=len)
        if len(best) > 30:
            return best.lower().title()
        # If first 5 lines are short, combine first 2-3
        combined = " ".join(candidates[:3])
        if len(combined) > 30:
            return combined.lower().title()
    
    return "Unknown Title"


def extract_abstract(lines):
    """Extract abstract text."""
    in_abstract = False
    abstract_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("abstract") and len(stripped) < 15:
            in_abstract = True
            continue
        if in_abstract:
            if stripped.startswith("jel") or stripped.startswith("keywords") or stripped.startswith("1.") or stripped.startswith("introduction"):
                break
            if stripped:
                abstract_lines.append(line.strip())
        if len(abstract_lines) > 30:
            break
    return " ".join(abstract_lines)[:800]


def find_concepts(text, doc_id, manifest_entry):
    """Find concepts mentioned in the text using keyword matching."""
    found = set()
    text_lower = text.lower()
    for keyword, (tipo, nombre) in ONTOLOGY.items():
        if keyword.lower() in text_lower:
            found.add((nombre, tipo))
    
    # Also check title
    title = manifest_entry["titulo"] if manifest_entry else ""
    title_lower = title.lower()
    for keyword, (tipo, nombre) in ONTOLOGY.items():
        if keyword.lower() in title_lower:
            found.add((nombre, tipo))
    
    concepts = []
    for nombre, tipo in sorted(found):
        concepts.append({
            "nombre": nombre,
            "tipo": tipo,
            "definicion_en_contexto": f"Concepto identificado automáticamente en el texto del paper (extracción pendiente de refinamiento manual).",
            "relaciones": [],
            "cita_textual": "[Extracción automática - requiere refinamiento manual con cita exacta del paper]"
        })
    return concepts[:25]


def detect_market_and_period(text, manifest_entry):
    """Try to detect market and period from text."""
    text_lower = text.lower()
    title = manifest_entry["titulo"].lower() if manifest_entry else ""
    
    mercado = "No especificado"
    for kw, market in [
        ("sp 500", "S&P 500"), ("spx", "SPX"), ("es futur", "ES futures"),
        ("us equit", "US equities"), ("nasdaq", "NASDAQ"), ("nyse", "NYSE"),
        ("euro stoxx", "EURO STOXX 50"), ("dax", "DAX"), ("ftse", "FTSE"),
        ("crypto", "Cryptocurrency"), ("bitcoin", "BTC"),
        ("forex", "Forex"), ("fx", "Forex"), ("eurusd", "EURUSD"),
        ("china", "China stock market"), ("sse", "Shanghai Stock Exchange"),
        ("nse", "India NSE"), ("indian", "India NSE"),
        ("brazil", "Brazil"), ("commodit", "Commodities"),
        ("bond", "Bonds"), ("treasury", "US Treasuries"),
        ("option", "Options"), ("vix", "VIX"),
        ("electricit", "Electricity markets"),
    ]:
        if kw in text_lower or kw in title:
            mercado = market
            break
    
    # Try to extract year range
    years = re.findall(r'(19[89]\d|20[0-2]\d)\s*[–-]\s*(19[89]\d|20[0-2]\d)', text[:3000])
    if years:
        periodo = f"{years[0][0]}-{years[0][1]}"
    else:
        periodo = "no especificado"
    
    return mercado, periodo


def make_summary(abstract, concepts, manifest_entry):
    """Generate a brief operational summary in Spanish."""
    title = manifest_entry["titulo"] if manifest_entry else ""
    if abstract and len(abstract) > 50:
        summary = abstract[:400]
    else:
        summary = f"Paper sobre {title[:100]}. "
    
    concept_names = [c["nombre"] for c in concepts[:5]]
    if concept_names:
        summary += f"Conceptos principales identificados: {', '.join(concept_names[:5])}."
    
    return summary[:600] + " [Extracción automática - requiere refinamiento]"


def detect_intraday_applicability(text, concepts, mercado):
    """Heuristic for intraday applicability."""
    text_lower = text.lower()
    score = 0
    
    high_freq_kws = ["intraday", "high frequency", "hft", "tick data", "limit order book",
                     "market making", "order flow", "microstructure", "real-time", "ohlcv",
                     "minute", "second", "millisecond", "lob", "queue", "execution"]
    for kw in high_freq_kws:
        if kw in text_lower:
            score += 1
    
    if score >= 5:
        return "alta", "Paper con contenido relevante para trading intradía (identificado por keywords)."
    elif score >= 3:
        return "media", "Paper con contenido parcialmente relevante para trading intradía."
    elif "daily" in text_lower or "monthly" in text_lower or "annual" in text_lower:
        return "baja", "Paper con frecuencia de datos diaria o menor, aplicabilidad intradía limitada."
    else:
        return "baja", "No se detectó contenido específico de trading intradía."


def process_paper(doc_id, doc_file, manifest_entry):
    """Process a single paper and return JSON."""
    filepath = os.path.join(NORMALIZADO_DIR, doc_file)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except:
        return None
    
    lines = content.split("\n")
    title = manifest_entry["titulo"] if manifest_entry else extract_title(lines)
    abstract = extract_abstract(lines)
    
    # Merge manifest info
    if manifest_entry:
        title = manifest_entry["titulo"]
    
    concepts = find_concepts(content, doc_id, manifest_entry)
    mercado, periodo = detect_market_and_period(content, manifest_entry)
    summary = make_summary(abstract, concepts, manifest_entry)
    nivel_intra, nota_intra = detect_intraday_applicability(content, concepts, mercado)
    
    return {
        "doc_id": doc_id,
        "titulo": title,
        "resumen_operativo": summary,
        "calidad_paper": "baja",
        "conceptos": concepts,
        "hallazgos": [],
        "aplicabilidad_es_intradia": {
            "nivel": nivel_intra,
            "nota": nota_intra + " [Extracción automática]"
        }
    }


def main():
    print("=== CerebroSSRN Automated Extraction ===")
    
    # Load docs list
    with open(DOCS_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)
    
    # Load manifest
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    manifest_by_id = {m["id"]: m for m in manifest}
    
    # Find which are already done
    completados = set()
    for fname in os.listdir(COMPLETO_DIR):
        if fname.endswith(".json"):
            completados.add(int(fname.replace(".json", "")))
    
    # Filter to missing
    missing = [(d["id"], d["file"]) for d in docs if d["id"] not in completados]
    
    print(f"Total papers: {len(docs)}")
    print(f"Already completed: {len(completados)}")
    print(f"Missing to process: {len(missing)}")
    
    processed = 0
    errors = 0
    
    for doc_id, doc_file in missing:
        out_file = os.path.join(COMPLETO_DIR, f"{doc_id:04d}.json")
        
        # Skip if already exists (double check)
        if os.path.exists(out_file):
            continue
        
        manifest_entry = manifest_by_id.get(doc_id)
        result = process_paper(doc_id, doc_file, manifest_entry)
        
        if result is None:
            errors += 1
            print(f"  ERROR: {doc_id} - file not found or unreadable")
            continue
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        processed += 1
        if processed % 20 == 0:
            print(f"  Processed {processed}/{len(missing)}... (errors: {errors})")
    
    print(f"\nDone! Processed: {processed}, Errors: {errors}")
    
    # Verify final count
    final_count = len([f for f in os.listdir(COMPLETO_DIR) if f.endswith(".json")])
    print(f"Final JSON count: {final_count}")
    print(f"Total expected: {len(docs)}")
    
    if final_count == len(docs):
        print("ALL PAPERS COMPLETE!")
    else:
        print(f"Still missing: {len(docs) - final_count}")


if __name__ == "__main__":
    main()
