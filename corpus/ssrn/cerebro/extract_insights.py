import json
from pathlib import Path

files = list(Path(r'../extraccion/completo').glob('*.json'))
high_impact = []
keywords = ['stop', 'loss', 'spoof', 'inventory', 'hidden', 'iceberg', 'limit', 'book', 'liquidity', 'exhaustion', 'reversion', 'momentum', 'imbalance', 'absorb', 'hft', 'algo', 'tick', 'impact']

for f in files:
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        app_obj = data.get('aplicabilidad_es_intradia', {})
        if isinstance(app_obj, dict):
            nivel = app_obj.get('nivel', '').lower()
        else:
            nivel = str(app_obj).lower()
            
        if 'alta' in nivel or 'media' in nivel:
            hallazgos = data.get('hallazgos', [])
            matched = []
            for h in hallazgos:
                afirmacion = ""
                if isinstance(h, dict):
                    afirmacion = h.get('afirmacion', '')
                elif isinstance(h, str):
                    afirmacion = h
                
                if any(k in afirmacion.lower() for k in keywords):
                    matched.append(afirmacion)
                    
            if matched:
                high_impact.append({
                    'id': data.get('doc_id'),
                    'title': data.get('titulo'),
                    'hallazgos': matched
                })
    except Exception as e:
        pass

with open('deep_insights.txt', 'w', encoding='utf-8') as out:
    for doc in high_impact:
        out.write(f"\n=== PAPER {doc['id']} ===\n")
        out.write(f"TITLE: {doc['title']}\n")
        for h in doc['hallazgos']:
            out.write(f"- {h}\n")
