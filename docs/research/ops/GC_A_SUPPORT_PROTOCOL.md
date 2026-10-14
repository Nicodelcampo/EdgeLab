# Diagnóstico científico de soporte del proxy A — sólo entrenamiento

Plan `GC_A_SUPPORT_PLAN.json`, SHA `0201ee0951f602d1699e93d10b843d59cdf800072205b23b4266675767685cc9`.

## Pregunta y alcance
¿Por qué la conjunción A del protocolo GC A/E anterior aparece sólo dos veces en entrenamiento? Diagnóstico científico, NO nueva auditoría del dataset ni prueba de respuesta/edge. Reutiliza exactamente las seis sesiones de entrenamiento 3–10 de agosto, fuente GC12-26 y calibración GC del31 de julio SHA539b4ba2. No lee evaluación ni calcula labels/outcomes, no ajusta umbrales o modelos. El resultado anterior se preserva, incluidos negativos y primarios inconclusos.

## Medidas congeladas
Cinco condiciones en orden de bits:
1. Presión actual ≥ q80 de calibración.
2. Presión previa ≥ q80 de calibración.
3. Avance neto absoluto ≤ umbral de stall congelado.
4. Rango de precio ≤ umbral congelado.
5. Camino recorrido ≤ umbral congelado.

Conteo individual, **las32máscaras de combinación**, conjunción completa y conteo que satisface todas las demás condiciones al omitir cada una. Estos últimos son diagnóstico matemático de soporte, NO autorización para relajar parámetros. No atribuir causalidad o utilidad predictiva al criterio con mayor aumento.

Separar fase/dirección, fechas y UNKNOWN; denominador elegible definido por observabilidad/calibración ANTES de cualquier futuro. Reportar cuantiles10/25/50/75/90 de componentes en entrenamiento junto con los umbrales originales. Cuantiles son descriptores agregados; no reemplazan la calibración ni se recombinan desde cuantiles por sesión. Crossfoot de máscaras, estados, totales y paridad del censo antes de labels frente al recibo GC A/E ya guardado.

## Pruebas y entrega
Fixtures verifican32máscaras, reconcilian conteos independientes y bloquean constructors/labels de respuesta y fit. Startup aislado delbundle yboot conoutcomes_requested/computed=False. Recibos boot/census≤512KiB; auditor sóloagregados, no recomputación privada deltape. Datos/arrays/logs quedan sóloenKaggletemporal. Plan/límites/source/bundle/job/journals/resultados/negativos y propuestas de conocimiento se guardan enrepo. Propuesta de conocimiento NO es escritura canónica delcerebro.

## Presupuesto y autoridad
Una intención nueva, un job privadoCPU, seis polls máximo. CPU/wall600s,parent1200s,notebook1800s,8Mticks total,250kanclas por sesión,AS6GiB/RSS4GiB. Firma/bytes deltransporte sóloidentidad,no calidadcertificada. Journals anteriores terminalesintactos; nuncareset/retry ambiguo. Sin reenvío automático, holdout/P&L/merge/daemonDebian/24x7 cerrados. Una eventual definición nueva necesitará otro plan antes de nuevos outcomes; no convertir elcenso en una búsqueda de ganador.
