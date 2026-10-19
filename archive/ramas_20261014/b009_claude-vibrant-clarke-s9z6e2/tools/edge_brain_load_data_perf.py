#!/usr/bin/env python3
"""Carga en el Edge Brain (hipocampo durable, append-only y encadenado por hash) el aprendizaje de la corrida GEX-1 de Kaggle del 2026-10-05:
por qué tardó y falló, y cómo se arregló. Idempotente: si el episodio ya existe, no escribe nada. Las lecciones entran como PROPOSED/LOW (techo del almacén durable)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.edge_brain import DurableHippocampus
from edgelab.edge_brain.hippocampus import AnalysisEpisode,StepExecution,Expectation,FailureEvent,RepairAction,SuccessEvent,LessonCandidate
LEDGER=Path("docs/research/edge_brain/hippocampus_ledger.jsonl");NOW="2026-10-05T18:00:00Z";EP="DATA-PERF-GEX1-20261005";BY="claude-session-01EvKWDhmuFWVViFYMiE5pZf"
def extra(h):
    """Registros agregados después (append-only): comprobación previa contra Kaggle, fuentes alternativas y prueba de humo. Idempotente por id."""
    have_l={l.lesson_id for l in h.memory.lessons[EP]};have_s={x.success_id for x in h.memory.successes[EP]}
    if "OK2" not in have_s:
        h.record_success(SuccessEvent("OK2",EP,"S2","Prueba de humo en Kaggle: M1 de MES de 5 trimestres en 36 s (antes ≈ 10 min por trimestre); mismas cantidades de filas que la corrida original",["82.794 y 84.180 filas, iguales al log de la corrida GEX-1 original","tools/kaggle_launch.py rechaza lanzar si una sesión aprobada no tiene fuente en Kaggle","sin resultados de análisis calculados"],lesson_candidate_id="L6",occurred_at_utc=NOW))
    new=[("L6","Lanzá kernels con tools/kaggle_launch.py: comprueba contra la lista VIVA de Kaggle que cada sesión aprobada tenga fuente (primaria o alternativa consistente) y no lanza si falta alguna. Un resolver que apunta a archivos que aún no están subidos hace fallar el kernel tarde.",["El resolver apuntaba a 23 archivos del dataset edgelab-ticks-nt8-reexport-20261005, que solo tenía el README (767 sesiones aprobadas afectadas)"],["datasets nuevos o re-exportados"]),
         ("L7","Un resolver debe guardar, por sesión, fuentes alternativas del mismo contrato y fecha con una marca de consistencia (trades a 1 %), y la lectura debe usarlas con aviso. Una fuente inconsistente no se usa en silencio.",["RESOLVER_STATUS.md: 495 de 767 sesiones tienen alternativa; 272 no"],["más de un dataset con el mismo contrato"])]
    for lid,st,ev,cond in new:
        if lid not in have_l:h.record_lesson(LessonCandidate(lid,EP,st,evidence_record_ids=ev,confidence="LOW",status="PROPOSED",scope="METHODOLOGICAL",created_at_utc=NOW,robustness="UNRATED",conditions=cond))
    (LEDGER.parent/"HIPOCAMPO.md").write_text(h.render_markdown())


def main():
    LEDGER.parent.mkdir(parents=True,exist_ok=True);h=DurableHippocampus(LEDGER)
    if EP in h.memory.episodes:
        extra(h);print("episodio ya cargado; tip",h.tip_hash[:12]);return
    h.register_episode(AnalysisEpisode(episode_id=EP,goal="Que las corridas de Kaggle sobre datos de ticks sean rápidas: la corrida GEX-1 tardó 25,7 min y falló al final",created_at_utc=NOW,updated_at_utc=NOW,recorded_by=BY))
    h.record_step(StepExecution("S1",EP,1,"Leer el log del kernel (kernels/output) para ver dónde se fue el tiempo y por qué falló","tools/kaggle_kernel.py output",status="DONE",output_summary="MES 2025-07..09 a los 612 s, 2025-10..12 a los 1.161 s; FileNotFoundError a los 1.540 s por dataset no adjuntado",executed_at_utc=NOW))
    h.record_step(StepExecution("S2",EP,2,"Reescribir load_m1 y verificar igualdad exacta contra la versión original","tools/m1_speed_check.py",status="DONE",output_summary="127,2 s -> 2,1 s (1ª vez) -> 0,05 s (caché); assert_frame_equal sobre 141.603 minutos de GC",executed_at_utc=NOW))
    h.record_expectation(Expectation("E1",EP,"Construir M1 por grupo de filas con numpy y caché reduce el tiempo en más de 10 veces sin cambiar el resultado","load_m1_seconds","DECREASE",status="PROPOSED",baseline_value=127.2,expected_value=12.7,created_at_utc=NOW))
    h.record_failure(FailureEvent("F1",EP,"S1","SLOW_PIPELINE","load_m1 procesaba cada tick en pandas","la fecha de sesión se calculaba como CADENA por tick (tz_convert + strftime sobre decenas de millones de filas), np.isin sobre cadenas, concat y sort de todos los ticks, groupby con columnas de texto; ≈ 10 min por trimestre de MES en Kaggle",occurred_at_utc=NOW))
    h.record_failure(FailureEvent("F2",EP,"S1","MISSING_INPUT","El kernel falló a los 1.540 s con FileNotFoundError","se lanzó sin adjuntar el dataset edgelab-ticks-nt8-reexport-20261005 que el resolver ya usaba como primera prioridad; el error aparecía recién al llegar al último tramo",occurred_at_utc=NOW))
    h.record_repair(RepairAction("R1","F1","load_m1 agrega por grupo de filas con numpy, calcula la fecha de sesión una vez por MINUTO, usa columnas con diccionario y guarda el M1 de cada archivo en caché",["docs/data_catalog/edgelab_data.py: _file_m1, _m1_cached, load_m1","tests/test_edgelab_data_m1.py","tools/m1_speed_check.py"],verified_by_test=True,status="DONE",executed_at_utc=NOW),EP)
    h.record_repair(RepairAction("R2","F2","required_files y check_inputs: load_ticks y load_m1 comprueban TODOS los archivos antes de procesar y listan los datasets que faltan; `python edgelab_data.py INST DESDE HASTA` dice qué adjuntar",["docs/data_catalog/edgelab_data.py: required_files, check_inputs"],verified_by_test=True,status="DONE",executed_at_utc=NOW),EP)
    h.record_success(SuccessEvent("OK1",EP,"S2","load_m1 rápida idéntica a la original",["igualdad exacta (columnas, tipos y valores) en 141.603 minutos de GC","3 pruebas nuevas pasan","no se leyó el holdout"],lesson_candidate_id="L1",occurred_at_utc=NOW))
    L=[("L1","No construyas M1 desde ticks tick por tick en pandas en cada corrida: agregá por grupo de filas con numpy, calculá la fecha de sesión por minuto (no por tick), evitá columnas de texto por tick (usá diccionario) y cacheá el M1 por archivo. Verificá igualdad exacta contra la versión lenta antes de reemplazarla.",["Medición: 127,2 s -> 2,1 s -> 0,05 s en GC (ver S2/R1)"],["lectura de parquet de ticks de NT8 con 10^7-10^8 filas","resultado verificado idéntico"]),
       ("L2","Antes de lanzar un kernel largo, resolvé y comprobá todos los inputs: un archivo que falta no debe aparecer tras 25 minutos. Usá required_files/check_inputs y adjuntá los datasets que lista.",["F2: FileNotFoundError a los 1.540 s"],["kernels de Kaggle con datasets montados como input"]),
       ("L3","Diagnosticá con el log del kernel antes de optimizar: el log trae el tiempo de cada etapa. Imprimí marcas de tiempo por etapa en los scripts largos.",["S1: 612 s y 1.161 s por trimestre de MES"],["cualquier corrida en Kaggle"]),
       ("L4","Probá todo script de Kaggle con un recorte chico (un mes, un instrumento) antes de la corrida completa.",["F1 y F2 se habrían visto en el recorte"],["corridas de más de unos minutos"]),
       ("L5","Los datos derivados que se reusan (M1 por archivo) conviene publicarlos como dataset propio (edgelab-m1-bars) para que una corrida no recalcule nada. Propuesta, aún no construida.",["R1: el caché por archivo ya existe; falta publicarlo"],["varias corridas sobre los mismos futuros"])]
    for lid,st,ev,cond in L:h.record_lesson(LessonCandidate(lid,EP,st,evidence_record_ids=ev,confidence="LOW",status="PROPOSED",scope="METHODOLOGICAL",created_at_utc=NOW,robustness="UNRATED",conditions=cond))
    print("registros cargados; tip",h.verify()[:12]);(LEDGER.parent/"HIPOCAMPO.md").write_text(h.render_markdown())
if __name__=="__main__":main()
