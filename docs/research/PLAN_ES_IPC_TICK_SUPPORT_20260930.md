# ES IPC: soporte por ticks, sin retornos

Plan anterior al cómputo. Fuente: Kaggle v2, ES03-26 y GC04-26; ventana UTC [2026-02-01,2026-03-01). Tick nominal ES 0,25; GC 0,10. No se compara valor monetario ni se presume superioridad del tick nominal.

Unidad de frecuencia: fecha UTC del tick, NO sesión CME certificada. Velas de 25 registros/operaciones, ancladas al primer registro de cada fecha; se descarta y cuenta únicamente el remanente final incompleto. Se conservan fechas de calendario sin datos. No se exige paridad con el bundle del visor ni se reinterpreta su calendario.

Detectores ES originales, confirmación por precio a 2 ticks: PLANAS w2/gap15/step2/pull5/nmin3/dmax35; EMPINADAS w2/gap15/step3/pull6/nmin3/dmax35/total5/step_min3. Un evento por primera confirmación de una cadena que satisface la familia; sólo geometría disponible hasta ese momento, sin extensión futura. No se ajustan parámetros para alcanzar la frecuencia solicitada.

Se mide cantidad de eventos por fecha, piso geométrico 4, solapamiento entre familias y test de estabilidad de prefijos. Se compara spread cotizado del exportador en ticks: bid/ask positivos y ask>bid para el denominador; locked, crossed y faltantes se informan separados. Export de ticks NO es L2 reconstruido, no mide cola/defensa/fills/comisiones.

STOP antes de resultados posteriores a señal, modelos predictivos o ventaja neta. El modelo de climas ES STOP sigue STOP. Un libro ES fresco sería una nueva fuente y fase aparte.
