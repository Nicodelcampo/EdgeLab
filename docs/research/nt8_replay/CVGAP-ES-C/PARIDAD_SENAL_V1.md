# Paridad de la señal: CVGAP-ES-C nativa en NT8 contra Python (04/11/2026)

Estado: VIGENTE — primera comparación. NT8: `EdgeLabCvgapESC` v1.0, Strategy Analyzer, ES con merge non back adjusted, del 01/06 al
03/11/2026 (junio usado de arranque). Python: ANALIZAR_REGLA de la celda congelada, réplica abr–sep 2026 (`operaciones_python.csv`).
Ventana comparada: del 08/06 al 30/09/2026 (octubre es papel y queda afuera).

| | Cantidad |
|---|---|
| Operaciones de Python | 29 |
| Disparos de NT8 que pasan la celda | 39 |
| **En el mismo minuto** | **27 de 29 (93 %)** |
| De esos, con el mismo lado, stop y objetivo exactos | **27 de 27** |
| Sólo en Python | 2 (12/06 15:34 y 03/09 14:08) |
| Sólo en NT8 | 12 (5 el 17/08; el resto sueltos en junio, agosto y septiembre) |

## Lectura

- **La traducción de la lógica es correcta.** Cuando los dos disparan, la regla da exactamente los mismos niveles al tick.
- **Las diferencias son de cobertura, no de cálculo.** Causas probables, a verificar en este orden:
  1. **Historia del percentil.** El P90 del volumen de la caja usa las últimas 50 cajas. NT8 arrancó el 1/6 y Python en agosto de 2025, así
     que sus umbrales difieren hasta acumular historia. Se verifica corriendo NT8 desde enero de 2026.
  2. **Datos.** Las sesiones de roll (11–18/9) y los días con diferencias de ticks entre el release de Python y los datos de NT8. El 17/08
     concentra 5 de los 12 extras, lo que sugiere un día de datos distinto.
  3. **Operaciones sin llenado en Python.** Python sólo lista las que llenaron (la vela k+2 tiene que ser de la misma sesión), mientras que
     el disparo de NT8 se registra aunque no opere.
- La ejecución de la v1.0 estaba rota: quedaba en «posición abierta» y omitía todo. Está corregida en la v1.1.
