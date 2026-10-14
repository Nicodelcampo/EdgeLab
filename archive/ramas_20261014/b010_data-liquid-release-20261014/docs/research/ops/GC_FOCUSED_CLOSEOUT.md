# GC: la pista de retorno no se sostuvo en el bloque posterior

Ambos jobs completaron correctamente: científico `138560454/v1` (edgelab-gc-focused-return-v1), benchmark `138560470/v1` (edgelab-gc-bt2a-schedule-benchmark-v1). Fuente de código `73f38712b743aadac73a0f07d3e7d710e9987dd0`; plan `49bb3dd734685d41fddfa619ae5393a9f2be9d4f2b91e9e16a229218cb27cbd4`. Dos nuevas intenciones cerradas; tres consultas del científico y una del benchmark. Ningún reenvío o sustitución de fecha.

## Resultado principal, sin rescatar el corte
AVOLZONEPOI2 tick25 denso × BigTrap2 tick200, dentro de ambas exposiciones y retorno observado en ambas: **3.099 anclas en9 sesiones**, 27 de agosto–9 de septiembre. 28 de agosto vacío conservado como ausencia, no cero; feriado7 de septiembre retenido. Total común54.068 anclas; un par/dos perfiles/diez modelos. Calibración/entrenamiento e historia nativa originales mantenidos.

Δ Brier×1000; negativo mejora:

| Llegada contra | Media por sesión | Ponderado por anclas | Sesiones que mejora |
|---|---:|---:|---:|
| Base continua | −1,1873 | −2,5761 |6/9|
| Control de igual capacidad | **+1,1332** | **+0,7203** |**4/9**|
| Densidad sola | **+3,3401** | **+3,1414** |**1/9**|

La campaña anterior daba−0,8446 ponderado por anclas frente al control y10/12 sesiones mejores. Esta prueba posterior da+0,7203 y4/9: **el aporte incremental de llegada no se sostuvo**. Mejorar base continua no basta si se pierde contra los controles. No es refutación universal de absorción, exhaustion o de toda combinación AVZ/BigTrap.

En todas las anclas comunes del bloque nuevo, media por sesión: densidad−base−1,0300; completo−base+0,3476; completo−densidad+1,3776. La densidad sigue siendo una hipótesis de desarrollo, no una estrategia validada. En el corte principal el completo−espejo también empeora+4,0268 por sesión.

## Dependencia y sensibilidad
Las anclas solapadas no son réplicas independientes. Bootstrap descriptivo de sesiones: llegada−control intervalo[−0,3808,+2,8756] ×1000; incluye cero, no se usa como aprobación ni prueba confirmatoria.

Afinando primero la grilla común a separación≥60s y después filtrando retorno quedan **279 anclas en9 sesiones**: soporte insuficiente frente al mínimo2000. En esta sensibilidad llegada−control da−0,8133 por sesión/−0,5378 ponderado, pero solo2/9 sesiones mejoran; intervalo descriptivo incluye cero. Se conserva esa excepción y no se la presenta como réplica. Llegada−densidad sigue peor+4,9383 por sesión. No hay identidades de episodios de zona exportadas; no inventarlas desde estos agregados.

## Rendimiento real
- Científico: **166,49s runner /172,80s host**, ~324MiB RSS muestreada por host. Un par, no la grilla18. No se calcula una aceleración frente a la campaña anterior: cambian fechas y trabajo realizado.
- Benchmark aislado: mismos76.117 ticks GC del3 de agosto, tres perfiles BT2Absorption, ABBA. Secuencial2,6065/2,6146s; intercalado2,5600/2,5168s. Medianas: **1,0284×**, reducción de duración **2,7649%** del subpaso medido. Incluye instrumentación de capturas, no velocidad de todo el pipeline.
- Capturas, logs nativos, conteos, residuos y tamaños de estado exactos en los cuatro pases. Cachehits2→3046, misses7611→4567: mucha más reutilización sin gran mejora total. Perfilar los demás costos nativos antes de ampliar cache o prometer aceleración grande.
- El método nuevo no se activó en producción. La paridad es del mismo Python con la misma entrada, no certificado NT8 ni calentamiento multis sesión.

## Aprendizajes y sistema autónomo
Propuesta de conocimiento preserva el resultado negativo. No escritura canónica del EdgeBrain, selección automática, P&L, holdout, deployment Debian ni merge del PR. Historial anterior sigue terminal; no relanzar la grilla para repetir este resultado.

Pruebas:922 ResearchOps +18 navegación PASS, catálogo PASS_NAVIGATION_ONLY; luego un test focal adicional PASS para corregir etiquetas de telemetría de futuros paquetes benchmark. No se afirma que la regresión922 incluya ese cambio posterior: no afecta runner científico ni jobs inmutables ejecutados.

El wrapper compartido del benchmark terminado marcó outcomes_requested/computed=true por herencia: el módulo ejecutado **no calcula etiquetas/respuestas ni ajusta modelos**. Se preserva el recibo original, se documenta la inconsistencia y se corrigió el empaquetador futuro. También se registraron fallos locales de casing de test, offset de shard aislado, descubrimiento duplicado de tests y referencia a recibo del paquete anterior. Ninguno implicó reenvío a Kaggle ni nueva validación de dataset.

Siguiente trabajo útil: perfilar estados/percentiles de BT2A con la misma entrada y probar equivalencia de estado en un prefijo multis sesión antes de activar intercalado en el runner. Para ciencia, diseñar otra hipótesis por mecanismo (no rescatar mediante miles de cortes lo que falló) y conservar densidad como comparador obligatorio. Todo nuevo experimento requiere plan y presupuesto propios; holdout desde1 de octubre permanece cerrado.
