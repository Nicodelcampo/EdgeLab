# Auditoria y continuacion del funnel — 2026-10-03

Base revisada: ab9a0540c43ad7f68a015a9f22892633a555cd6d. No se descargaron precios reales, no se amplio el historico, no se abrio D2 y no se modificaron los registros originales de MGC.

## Hallazgos del codigo (no inferencias sobre los datos ejecutados)

1. `run_e1_e3` pasaba todas las senales y todas las barras al kernel; filtraba D0/D1 DESPUES de calcular outcomes. La mascara sellada no impedia leer precios de D2, ni que un horizonte D0 entrara en D1. El impacto real requiere reconstruir el manifiesto y repetir SOLO D0/D1, nunca inspeccionar D2 para auditar este problema.
2. CPU retorna float64, pero el batching original presupone cuatro bytes por celda. Ademas, fuerza una columna aun cuando no entra en el presupuesto. El nuevo wrapper usa ocho bytes, rechaza ese caso y verifica nbytes. Es un limite por matriz de salida, NO de RAM/VRAM total.
3. PBO sobre sobrevivientes no equivale a control de multiplicidad del universo completo. Se etiqueta como diagnostico, sin permiso de promocion; no se sustituyen SPA/DSR/BH ni el registro faltante de 126 pruebas.

## Cambio

El runner ahora usa ventanas fisicamente recortadas por particion y excluye senales sin horizonte completo. Registra exclusions, horizonte y politica `complete_horizon_stage_local_v1`. El kernel existente visita hold+1 barras; esa semantica se conserva explicitamente, sin inventar outcomes por censura. Los reportes ahora incluyen `devices` por etapa en lugar del antiguo `device` unico.

Las estadisticas precedentes del cheap-screen deben considerarse pendientes de revalidacion de aislamiento. Esto NO borra negativos, no autoriza retuning ni declara contaminado el motor tick-exact independiente. Conservar resultados anteriores; escribir una ejecucion nueva y enlazar su correccion en el ledger existente solo cuando haya custodia y datos D0/D1 verificados.

## Validacion realmente ejecutada

- 10/10 tests nuevos de unittest con arrays sinteticos: aislamiento, horizontes, indices, presupuesto float64, oraculo independiente y ruta del runner con servicios externos sustituidos por dobles de prueba.
- compileall sobre los archivos nuevos/modificados: PASS.
- No se ejecuto Numba, CuPy, CUDA, Parquet ni la suite historica completa: el entorno actual carece de esas dependencias y no tiene internet habilitado. Estos tests NO demuestran paridad CPU/GPU.

## Gate de paridad reproducible

En un entorno Kaggle GPU con dependencias instaladas, ejecutar desde un checkout de ESTA rama/commit:

```sh
python tools/verify_funnel_cpu_gpu.py --out parity_cpu_gpu.json
```

El script genera solo datos sinteticos; no requiere adjuntar datasets MGC ni D2. Compara CPU compilado y GPU con un oraculo Python, incluyendo stop-first, touch sin fill, ambos sentidos, multiplicadores, horizontes 0/1/17/200, ultimas barras y comisiones no binarias. Guarda hashes de fuentes y versiones. Falla si falta CUDA; no convierte un fallback CPU en PASS GPU. `--cpu-only` emite `CPU_ONLY_PASS_GPU_PENDING`, nunca PASS de paridad. La precision GPU declarada es float32, no igualdad bit a bit float64.

```sh
python -m unittest discover -s tests -p 'test_funnel_isolation.py' -v
```

## Estado y siguientes pasos

- CUDA_PARITY: PENDING_REAL_EXECUTION.
- MGC_PROMOTION: BLOCKED, sin cambiar TP400 tick-exact ni aprobar TP200.
- D2: SEALED; esta auditoria solo utiliza datos sinteticos.
- Las familias no-EMA ya constan en `NONEMA_D0_D1.md`: VWAP reclaim, absorption y failed auction, cada una 0/3 sobrevivientes reportados. No relanzarlas con umbrales vecinos. Su screening previo tambien requiere verificar aislamiento.
- HFTZones, BigTrap y aVolCluster requieren custodia/semantica de las features y contrato estructurado antes de proponer nuevas pruebas.
- No se recrearon los schemas faltantes del atlas original.
- Antes de rerun real: fijar manifiesto y particiones originales; no recalcular fracciones sobre un historico expandido o truncado. Auditar tambien productores de features target-free: este parche aisla outcomes del runner, no garantiza por si solo toda la cadena de carga/feature generation.
- El runner actual aun elige headline por score de medias, no acredita plateau de parametros ni independencia; no se etiqueta como estabilidad validada.

El acceso privado a Kaggle debe usar el canal seguro del Worker/credencial existente, no tokens en chat, archivos versionados ni salida de terminal. No se solicitaron credenciales en esta etapa: faltan primero habilitar acceso de ejecucion y verificar la configuracion vigente.
