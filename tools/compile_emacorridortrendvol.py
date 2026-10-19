import sys, tempfile, shutil, importlib.util, os
spec = importlib.util.spec_from_file_location('c', r'E:\EdgeLab-port\tools\compilar_nt8_cs.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
refs, err = c.referencias()
print('refs err:', err)
refs['resueltas'] = [r for r in refs['resueltas'] if 'GEXRadarWallsOnNT8' not in r and 'NinjaTrader.Vendor' not in r] + [r'C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.dll']
csc = c.buscar_csc()
base = r'C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators'
for name in ('EmaCorridorTrend', 'EmaCorridorTrendVol'):
    tmp = tempfile.mkdtemp()
    r = c.compilar(os.path.join(base, name + '.cs'), refs, csc, tmp, name)
    print(name, 'exit', r['exit_code'], 'errores', r['n_errores'])
    for e in r['errores'][:8]:
        print('   ', e[-260:])
    shutil.rmtree(tmp, ignore_errors=True)
src = open(os.path.join(base, 'EmaCorridorTrendVol.cs'), encoding='utf-8-sig').read()
i = src.rindex('\t\t#endregion')
mut = src[:i] + c.MUTACION + src[i:]
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, 'MUT.cs')
open(p, 'w', encoding='utf-8-sig').write(mut)
r = c.compilar(p, refs, csc, tmp, 'MUT')
print('control negativo (debe fallar): exit', r['exit_code'], 'errores', r['n_errores'])
