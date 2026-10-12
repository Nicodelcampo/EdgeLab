import json, os
base = os.getcwd()
completo = os.path.join(base, r'extraccion', 'completo')
deleted = 0
for f in os.listdir(completo):
    fp = os.path.join(completo, f)
    if not f.endswith('.json'):
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            d = json.load(fh)
        text = json.dumps(d, ensure_ascii=False)
        if 'Extracción automática' in text:
            os.remove(fp)
            deleted += 1
    except:
        pass
print(f'Deleted: {deleted}')
remaining = [f for f in os.listdir(completo) if f.endswith('.json')]
print(f'Remaining: {len(remaining)}')
