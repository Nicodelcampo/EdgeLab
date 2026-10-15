import json
import numpy as np
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.bridge.indicators.espejo_impulsos import run

def audit_bundle(bundle_path, ext_thr=0.50, reentry_thr=0.10):
    print(f"\n=======================================================")
    print(f"AUDITORIA FORENSE: Excursión Post-Espejo en {bundle_path.name}")
    print(f"Configuración: Extensión >= {ext_thr*100:.0f}% W | Reingreso máx <= {reentry_thr*100:.0f}% W")
    print(f"=======================================================")
    
    data = json.load(open(bundle_path, encoding="utf-8"))
    candles = data["bar_series"]["tick_25"]["candles"]
    n = len(candles)
    tick = data["meta"].get("tick_size", 1.0)
    
    t = np.array([c["time"] for c in candles], dtype=np.int64)
    O = np.array([c["open"] for c in candles], dtype=np.float64) / tick
    H = np.array([c["high"] for c in candles], dtype=np.float64) / tick
    L = np.array([c["low"] for c in candles], dtype=np.float64) / tick
    C = np.array([c["close"] for c in candles], dtype=np.float64) / tick
    V = np.array([c["volume"] for c in candles], dtype=np.float64)
    session = np.zeros(n, dtype=np.int32)
    last_of_session = np.zeros(n, dtype=bool)

    # Nivel 3 de permiso (Base Nico: min_w = 17, max_bars = 20)
    res = run(t, O, H, L, C, V, session, last_of_session, params={"min_w": 17, "max_bars": 20})
    
    total_impulses = len(res["impulses"])
    completed = [m for m in res["impulses"] if m.get("estado_final") == "MIRROR_COMPLETED" and m.get("bar_final") is not None]
    
    print(f"Total impulsos detectados: {total_impulses}")
    print(f"Total espejos completados (MIRROR_COMPLETED): {len(completed)}")

    # Simular EXACTAMENTE la lógica de index.html
    ext_count = 0
    reentered_before_ext = 0
    never_reached_ext = 0
    
    max_excursions = []
    
    for m in completed:
        d = m["dir"]
        a = m["A"]
        w = m["W"]
        b_comp = m["bar_final"]
        
        req_dist = ext_thr * w
        max_reentry = reentry_thr * w
        
        reached = False
        reentered = False
        
        # Evaluar vela de completitud
        if d == 1:
            if L[b_comp] <= a - req_dist:
                reached = True
            if C[b_comp] > a + max_reentry:
                reentered = True
        else:
            if H[b_comp] >= a + req_dist:
                reached = True
            if C[b_comp] < a - max_reentry:
                reentered = True
                
        # Evaluar hasta 200 velas posteriores
        max_check = min(n - 1, b_comp + 200)
        curr_max_exc = 0.0
        
        for k in range(b_comp + 1, max_check + 1):
            if d == 1:
                # Excursión a favor del cierre del espejo (hacia abajo, d=1 bajista hacia A)
                exc = (a - L[k]) / w
                if exc > curr_max_exc:
                    curr_max_exc = exc
                if H[k] > a + max_reentry:
                    reentered = True
                    break
                if not reached and L[k] <= a - req_dist:
                    reached = True
                    break
            else:
                # Excursión a favor del cierre del espejo (hacia arriba, d=-1 alcista hacia A)
                exc = (H[k] - a) / w
                if exc > curr_max_exc:
                    curr_max_exc = exc
                if L[k] < a - max_reentry:
                    reentered = True
                    break
                if not reached and H[k] >= a + req_dist:
                    reached = True
                    break
            if reached:
                break
                
        max_excursions.append(curr_max_exc)
        
        if reached and not reentered:
            ext_count += 1
        else:
            if reentered:
                reentered_before_ext += 1
            else:
                never_reached_ext += 1
                
    pct_ext = (ext_count / len(completed)) * 100 if completed else 0
    pct_fail = 100 - pct_ext
    
    print(f"\n--- RESULTADOS DEL FILTRO 'Alejamiento post-espejo' ---")
    print(f"Espejos que cumplen (con excursión >= {ext_thr*100:.0f}% y reingreso <= {reentry_thr*100:.0f}%): {ext_count} ({pct_ext:.2f}%)")
    print(f"Espejos que NO cumplen (reingresan inmediatamente o no se alejan): {len(completed) - ext_count} ({pct_fail:.2f}%)")
    print(f"  - Reingresaron > {reentry_thr*100:.0f}% antes de tocar +{ext_thr*100:.0f}%: {reentered_before_ext} ({(reentered_before_ext/len(completed))*100:.2f}%)")
    print(f"  - Nunca llegaron a +{ext_thr*100:.0f}% en 200 velas: {never_reached_ext} ({(never_reached_ext/len(completed))*100:.2f}%)")
    
    excs = np.array(max_excursions)
    print(f"\n--- DISTRIBUCIÓN DE EXCURSIÓN MÁXIMA ANTES DEL REINGRESO DEL {reentry_thr*100:.0f}% ---")
    print(f"Mediana de excursión: {np.median(excs)*100:.1f}% de W")
    print(f"Percentil 25: {np.percentile(excs, 25)*100:.1f}% de W")
    print(f"Percentil 75: {np.percentile(excs, 75)*100:.1f}% de W")
    print(f"Espejos con excursión < 10% de W (rechazo inmediato al tocar A): {np.sum(excs < 0.10)} ({(np.sum(excs < 0.10)/len(completed))*100:.1f}%)")
    print(f"Espejos con excursión < 25% de W: {np.sum(excs < 0.25)} ({(np.sum(excs < 0.25)/len(completed))*100:.1f}%)")

if __name__ == "__main__":
    audit_bundle(Path("E:/EdgeLab/viewer/nt8_bridge/bundles/MYM_03-26_ESPEJO.json"), ext_thr=0.50, reentry_thr=0.10)
    audit_bundle(Path("E:/EdgeLab/viewer/nt8_bridge/bundles/MBT_07-26_ESPEJO.json"), ext_thr=0.50, reentry_thr=0.10)
