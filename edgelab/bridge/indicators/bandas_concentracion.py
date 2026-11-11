"""Bandas de concentración OG+VI (LUX-IMB) — referencia Python de la capa `&cz=1` del visor (EDGELAB_CONC_ZONAS_V1).

Causal y target-free. En cada vela M1 (por su hora de apertura `t`) se miran sólo las zonas ya nacidas (`t0 <= t`) y
vivas (`t1 > t`, vida 500 min). Se busca la banda de alto `alto` (en precio) que contiene completas más zonas (candidatos: las bandas que empiezan en el piso de cada zona viva); si tiene >= `umbral`
zonas se marca, se sacan sus zonas del corte y se repite, así un mismo corte puede dar varias bandas sin superponerse
en zonas. Por cada banda marcada:
- si pisa en precio una banda todavía viva (`t <= t1`), esa banda se alarga: `t1 = t + vida` y `n = max(n, conteo)`;
- si no, nace una banda nueva `[t, t + vida] x [piso, piso + alto]`.
La banda queda definida en el momento `t0` con información disponible en `t0` (no mira hacia adelante); su fin `t1`
sí depende del futuro (se alarga mientras la concentración siga), así que `t1` NO puede usarse como dato en `t0`.

Paridad con el visor: misma iteración, mismo orden y mismos desempates (el primer piso con el máximo conteo).
"""
from __future__ import annotations

from dataclasses import dataclass

VIDA_S = 500 * 60


@dataclass
class Banda:
    t0: int          # epoch s de la vela M1 donde se detecta (apertura de la vela)
    t1: int          # fin: última vela que la cumplió + vida
    piso: float
    techo: float
    n: int           # máximo de zonas contenidas mientras estuvo viva
    n0: int          # zonas contenidas al detectarse


def detectar(zonas, tiempos, alto: float, umbral: int, vida_s: int = VIDA_S) -> list[Banda]:
    """`zonas`: iterables de dicts con t0, t1, top, bottom (s epoch). `tiempos`: aperturas M1 ordenadas."""
    Z = sorted(zonas, key=lambda z: z["t0"])
    act: list = []
    j = 0
    out: list[Banda] = []
    for t in tiempos:
        while j < len(Z) and Z[j]["t0"] <= t:
            act.append(Z[j]); j += 1
        act = [z for z in act if (z.get("t1") or z["t0"] + vida_s) > t]
        if len(act) < umbral:
            continue
        srt = sorted(act, key=lambda z: z["bottom"])
        while True:                                   # todas las bandas >= umbral del corte, sin superponerse
            bn, bb, bi = 0, 0.0, []
            for i, z in enumerate(srt):
                b = z["bottom"]
                idx = [k for k in range(i, len(srt)) if srt[k]["top"] <= b + alto]
                if len(idx) > bn:
                    bn, bb, bi = len(idx), b, idx
            if bn < umbral:
                break
            srt = [z for k, z in enumerate(srt) if k not in set(bi)]
            for o in out:
                if t <= o.t1 and bb < o.piso + alto and bb + alto > o.piso:
                    o.t1 = t + vida_s; o.n = max(o.n, bn)
                    break
            else:
                out.append(Banda(t0=int(t), t1=int(t + vida_s), piso=bb, techo=bb + alto, n=bn, n0=bn))
    return out
