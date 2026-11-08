# Resultado: CANASTA-GLOBAL (08/11/2026)

Estado: RESULTADO (pre-registro `PREREGISTRO.md`; 6 tandas en Kaggle `canasta-global-t0…t5-20261108`, combinadas con
`tools/canasta_global.py`; datos `RESULTADO_CANASTA_GLOBAL.json`). Ventana 05/08/2025 → 30/09/2026, 338 sesiones, 106 cubos. Holdout
no tocado.

**La selección pasa la regla de Nico: p = 0,0099 (< 0,10).**
- Canasta de 10 reglas, todas de la familia U1 (zonas U1 en NQ y ES, grillas U1 en GC y en los CFD del Dow y del S&P, zonas AVCL y BT2).
- R neto por sesión de la canasta: +0,013; positiva en los 5 sub-bloques (+0,010, +0,013, +0,019, +0,013, +0,011); t diario 12,2.
- Nulo de la selección completa (B = 200): mediana del t 10,0, q90 11,4, q95 11,7. El t alto viene en gran parte de elegir entre
  millones de celdas; la canasta observada supera al nulo, pero por poco.

**Auditoría previa:** los módulos de los cubos elegidos (`u1_zonas`, `u1_oro`, `u1_cfd`, `u1_zonas_avcl`, `u1_zonas_bt2`) tienen
certificado de causalidad OK emitido antes de generar los cubos (`config/causalidad_certificados.json`).

**Lectura:** primera canasta que se distingue del azar con la selección contada. El efecto por sesión es chico (+0,013 R con 10 reglas),
así que lo económico depende de la escala y de que se sostenga hacia adelante. No es un edge todavía: falta el holdout.

**Siguiente paso (pre-registrado en `PREREGISTRO.md`):** apertura exploratoria del holdout con la canasta congelada (las 10 celdas
y pesos iguales), combinación Fisher con p_selección = 0,0099, pre-registro de la apertura aparte antes de abrir.
