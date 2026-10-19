# Reporte de investigación (10) — integración del censo de primeros toques

Se conectaron la población primaria y su decongestión en un censo puro y
auditable: `edgelab/research/first_touch_census.py`.

El integrador exige cobertura exacta de contratos y sesiones, falla ante fechas
repetidas entre contratos, filtra defensivamente eventos fuera del universo y
conserva sesiones de tasa cero. Las identidades de zona se prefijan por archivo
para impedir colisiones entre contratos.

La salida declara:

- política `first_touch_after_creation_bar`;
- conteos crudos y post-separación por sesión;
- sesiones cero;
- eventos fuera del universo;
- cobertura de contratos y sesiones;
- política de decongestión completa;
- `outcomes_accessed=false`.

Las regresiones cubren integración, decongestión, días cero, defensa de universo,
contratos faltantes y fechas duplicadas.

Queda un único acople operativo: ejecutar BigTrap2 sobre cada Parquet limpio y
pasar sus resultados al integrador. La lógica científica de población,
separación y cobertura ya no depende de esa I/O.

**Aporte al referente:** el censo primario completo tiene ahora un núcleo puro,
determinista y comprobable, separado de la lectura de Parquet y del cálculo de
outcomes.
