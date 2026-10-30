# Pre-registro v2: canasta de 7 reglas (firmado por Nico en sala, 2026-10-30; holdout sin abrir)
Canasta: CVGAP-NQ, CVGAP-CFD-NQ, U1-ZONAS-AVCL-NQ, U1-ORO, U1-RACIMOS-NQ, U1-YM, U1-ZONAS-NQ. Elegidas por INTEGRIDAD y replica.pasa, después de ver OOS (selección posterior declarada).
Excluida: BT2-ES, U1-ES, RACIMOS-ES, BT2-NQ, ZONAS-ES.
Principal: t por sesión de la canasta, con revisiones a 20, 40 y 60 sesiones y corrección secuencial: t >= 2.39, 1.69, 1.38 (O'Brien-Fleming, alfa total 0,10 una cola, simulado).
Por regla: estados de umbrales_estado.json; colapso con corrección por 7 reglas; sin p-valor individual.
Secundarios: frecuencia, acierto, cobertura, freno por t_exit, propfirm con estimar_propfirm.py.
Revisión a 20 sesiones: se abre solo si llega a 20 con datos válidos; si media <= 0 en la revisión de 60, no aprueba.
Sin freno en la prueba principal: el freno diario queda como secundario medido por t_exit.
El pre-registro de canasta_12_20261030 queda anulado.
Antes de abrir: calentamiento de zonas, ruta sellada, reconciliación de SV1 y test de punta a punta de LocalRunner.
