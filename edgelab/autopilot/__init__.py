"""EdgeLab autopilot: ciclo autónomo y acotado (proponer → validar → lanzar → analizar → aprender) pensado para correr en un Debian.
Principios: todo se pre-registra y se cuenta ANTES de lanzar; el holdout, los gates y los pre-registros pasados son intocables; la mejora recursiva
(de scripts, de configuración de corridas, de la selección de hipótesis) solo se acepta con salidas idénticas o con una regla de decisión fijada de antemano;
el sistema propone y ejecuta análisis, nunca opera ni promueve estrategias."""
HOLDOUT_FIRST_TRADE_DATE = "2026-10-01"
