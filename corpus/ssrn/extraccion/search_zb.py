import json
import glob
import sys

results = []
for fpath in glob.glob(r'C:\$ACerebroSSRN\extraccion\completo\*.json'):
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            text = json.dumps(data).lower()
            if any(k in text for k in ['treasury', 't-bond', ' zb ', 'interest rate futures', 'bond']):
                title = data.get('titulo', '')
                app = data.get('aplicabilidad_trading', {})
                score = app.get('score', '')
                if True:
                    results.append(f"TITLE: {title}")
                    results.append(f"SCORE: {score}")
                    results.append(f"FINDINGS: {app.get('hallazgos', [])}")
                    results.append("-" * 40)
    except Exception as e:
        print(f"Error {fpath}: {e}")

with open(r'C:\$ACerebroSSRN\extraccion\search_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
print(f"Found {len(results)//4} papers. Saved to search_results.txt")
