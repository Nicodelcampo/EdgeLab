#!/usr/bin/env python3
r"""Registro en el Cerebro (hipocampo) de lo medido y aprendido el 27–28/09/2026. Idempotente por episodio: si un
episode_id ya está en su ledger, se saltea.

    .venv\Scripts\python tools\brain_register_20260928.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from edgelab.edge_brain.episode_logger import measurement_episode  # noqa: E402
from edgelab.edge_brain.hippocampus import AnalysisEpisode, LessonCandidate  # noqa: E402
from edgelab.edge_brain.hippocampus_store import DurableHippocampus  # noqa: E402

H = REPO / "artifacts" / "hippocampus"
NOW = datetime.now(timezone.utc).isoformat()

EPISODES = [  # (ledger, episode_id, goal, tool, inputs, prereg, nota)
    ("ipc_20260926.jsonl", "EP-IPC-ROB-ES-NQ-20260928", "Robustez del positivo IPC etapa A 25t (controles as-of, midquote, C-SW emparejado)",
     "tools/ipc_robust.py", {"reporte": "artifacts/ipc_rob/reporte.json"}, "docs/research/MANIFIESTO_IPC_ROBUSTEZ_20260928.md",
     "NO_ROBUSTO 0/23 (sha f8e68b1a404b); el positivo venía de controles con zonas futuras y del rebote del precio de trade"),
    ("espejo_ind_20260926.jsonl", "EP-ESPEJO-NICO-100T-20260928", "Semejanza a lo Nico (modelo congelado 73 %) y completado del espejo, ES 100t",
     "tools/espejo_nico_descubrimiento.py", {"reporte": "artifacts/espejo/nico_100t/reporte.json"},
     "docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md",
     "0/8 con nulo N1 corregido (pool estrictamente previo, auditoría 059); P2 negativa en 3/4; MDE 0,07-0,16"),
    ("espejo_ind_20260926.jsonl", "EP-ESPEJO-VOLLIMP-100T-20260928", "Volumen y limpieza de la vuelta vs la ida (y la invertida), ES 100t",
     "tools/espejo_vollimp.py", {"reporte": "artifacts/espejo/vollimp_100t/reporte.json"},
     "docs/research/MANIFIESTO_ESPEJO_VOLUMEN_LIMPIEZA_100T_20260928.md",
     "0/24; menor p: R-VL x=0,75 otros -0,12 (p 0,042) en contra: pista, no resultado"),
    ("ipc_20260926.jsonl", "EP-IPC-NIVEL-MES-20260928", "IPC-NIVEL (>= 3 visitas, picos monótonos): barrido tras la formación, MES 25t",
     "tools/ipc_nivel_run.py", {"reporte": "artifacts/ipc_nivel/reporte.json"}, "docs/research/MANIFIESTO_IPC_NIVEL_MES_20260928.md",
     "1/8 sobrevive y va contra el imán: techo v2 se barre 6,2 pp menos que un pivote suelto emparejado; pivotes sueltos +5 pp sobre el azar"),
]

LESSONS = [  # (ledger, episode_id, lesson_id, statement, robustness, conditions)
    ("espejo_ind_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-NULL-F-BIASED-20260928",
     "P(completar)=f no es el nulo del espejo con velas OHLC, toque por mecha, extremo nuevo más allá de B y horizonte "
     "censurado: el paseo sintético da +1 a +5 pp sin censura y hasta +25 pp con censura sobre los resueltos. Usar un nulo "
     "simulado con la misma estructura y medir sobre todos los eventos.", "REPLICATED", ["espejo", "velas 25t/100t"]),
    ("espejo_ind_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-NULL-POOL-STRICT-20260928",
     "El pool de un nulo remuestreado tiene que terminar estrictamente antes de la vela del evento; incluir las subvelas de "
     "la vela que define el evento viola el pre-registro aunque no sea información futura (auditoría 059).", "UNRATED", []),
    ("nq_l2_20260924.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-L2-INTRABATCH-CROSS-20260928",
     "En el MBP10 de NT8 un mismo timestamp trae el ask nuevo antes de borrar el bid viejo: el cruce se evalúa al cerrar el "
     "lote. Y un cruce real (preapertura CME) no debe vaciar el libro: se cuenta y el minuto queda no elegible.",
     "REPLICATED", ["NT8 MBP10", "NQ 2026-06..09"]),
    ("nq_l2_20260924.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-L2-SHALLOW-SNAPSHOT-20260928",
     "La foto de un archivo L2 de NT8 puede traer 9 de los 10 niveles: los índices profundos quedan corridos. Hueco de 1 "
     "nivel en la cola (>= 8) se marca desconocido; fuera de la cola se sigue fallando cerrado.", "UNRATED", ["NQ 20260729"]),
    ("ipc_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-CONTROLS-ASOF-20260928",
     "Un control de nivel tiene que usar sólo zonas existentes en ese instante: los controles con zonas futuras fabricaron el "
     "positivo de IPC etapa A (+0,20 -> +0,06 -> -0,04 con midquote y C-SW emparejado).", "REPLICATED", ["ES", "NQ"]),
    ("ipc_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-DETECTOR-FIT-DURATION-20260928",
     "Ajustar un detector por superposición con zonas marcadas premia zonas larguísimas (hasta 11 h): acotar la duración "
     "antes de medir cobertura/precisión. Con el tope, la v0 pasó de F1 0,62 aparente a 0,18 real.", "UNRATED", ["IPC-NIVEL"]),
    ("ipc_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-PIVOT-SWEPT-20260928",
     "En MES 25t un pivote suelto (zigzag 6 t) se barre ~5 pp más que un paseo sin memoria (0,49 vs 0,44); un nivel con >= 3 "
     "visitas no. Medido sobre controles emparejados, no sobre el censo: el censo es un pre-registro aparte.",
     "UNRATED", ["MES 25t", "ago-2025..mar-2026", "precio de trade"]),
    ("espejo_ind_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-ESPEJO-SIM-SCOPE-20260928",
     "La semejanza vuelta/impulso de ESPEJO-SIM (MNQ 25t, métrica automática) está replicada en 3 contratos (+2..5 pp, "
     "parecidas - poco parecidas); su exceso sobre f no se sostiene (f sesgado). No se trasladó a ES 100t con el modelo de "
     "Nico: instrumento, escala y métrica cambian a la vez.", "REPLICATED", ["MNQ 25t"]),
    ("espejo_ind_20260926.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-TICKBARS-ONE-PROVIDER-20260928",
     "Lucid y NT8 son el mismo feed por minuto pero no por tick (NQ: 53 % de cierres 25t idénticos): una familia en barras "
     "de ticks se construye de punta a punta con un solo proveedor.", "REPLICATED", ["ES", "NQ", "jul-2025..jun-2026"]),
    ("nq_l2_20260924.jsonl", "EP-BRAIN-LECCIONES-20260928", "LES-RAM-ONE-HEAVY-L2-20260928",
     "Con 16 GB, dos procesos que cargan días completos del libro L2 de NQ a la vez colgaron la máquina (28/09): un solo "
     "proceso pesado de L2 por vez.", "UNRATED", ["máquina local 16 GB"]),
]


def done(ledger: Path, episode_id: str) -> bool:
    return ledger.exists() and f'"{episode_id}"' in ledger.read_text(encoding="utf-8")


def main():
    for led, eid, goal, tool, inputs, prereg, nota in EPISODES:
        p = H / led
        if done(p, eid):
            print("ya estaba", eid); continue
        with measurement_episode(p, eid, goal=goal, recorded_by=tool, inputs={k: REPO / v for k, v in inputs.items()},
                                 prereg_ref=prereg, repo=REPO) as ep:
            ep.note("resultado", nota)
        print("registrado", eid)
    by_ledger = {}
    for led, eid, lid, st, rob, cond in LESSONS:
        by_ledger.setdefault(led, []).append((eid, lid, st, rob, cond))
    for led, items in by_ledger.items():
        p = H / led; store = DurableHippocampus(p)
        eid = items[0][0]
        if not done(p, eid):
            store.register_episode(AnalysisEpisode(episode_id=eid, goal="Lecciones metodológicas 27-28/09 (propuestas)",
                                                   status="COMPLETED", created_at_utc=NOW, updated_at_utc=NOW,
                                                   recorded_by="tools/brain_register_20260928.py", outcomes_inspected=False))
        for eid, lid, st, rob, cond in items:
            if done(p, lid):
                print("ya estaba", lid); continue
            store.record_lesson(LessonCandidate(lesson_id=lid, episode_id=eid, statement=st, confidence="LOW",
                                                status="PROPOSED", scope="METHODOLOGICAL", created_at_utc=NOW,
                                                robustness=rob, conditions=cond))
            print("lección", lid)


if __name__ == "__main__":
    main()
