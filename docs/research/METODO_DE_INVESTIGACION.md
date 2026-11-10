# Método de investigación de EdgeLab — de una idea a una decisión

Estado: VIGENTE (2026-11-10, aprobado por Nico). Va completo en el núcleo de contexto de TODOS los roles del agente del Debian
(`edgelab/autopilot/contexto.py::NUCLEO_FUENTES`). Ejemplo completo y probado: `docs/research/hft_clusters_u1_20261110/`
(clusters de zonas HFT: E0, E0-b, rebote, imán, siete definiciones de rebote, contexto de otros clusters).

## El orden (no se saltea ningún paso)
1. **¿Ya está medido?** `docs/research/FACTORES_CON_VENTAJA.md`, `docs/research/FAMILIAS.md`, `python tools/existente.py buscar "…"`.
   Si hay una PISTA_VIVA relacionada, se trabaja sobre ella antes de abrir algo nuevo.
2. **Población escrita:** enumerar los eventos posibles (creación, alejamiento, primer toque, toque n-ésimo, confirmación, expiración,
   estado continuo) y decir cuál se mide y por qué.
3. **E0 sin retornos:** frecuencia por sesión, ancho/tamaño, estabilidad mes a mes, fricción en R si el stop fuera la estructura.
   La definición se elige con una **regla mecánica escrita antes**. Criterio recomendado: minimizar
   `borde detectable = 2,49/√N + fricción / tamaño` (el borde bruto más chico que sería a la vez medible y rentable).
4. **Varias definiciones con hipótesis propia, pocas pruebas:** cada definición tiene su mecanismo económico y umbrales redondos fijos
   (no una grilla). Se combinan activos con la misma regla (Stouffer) y se corrige entre definiciones (BH q 0,10).
5. **Control que comparte la condición del evento:** el mismo procedimiento sobre algo que no es el objeto (nivel corrido, otra hora
   de la sesión) y que no se superponga con el objeto real vivo. Un control sin la misma condición (p. ej. una carrera contra el
   espejo sin zona) dio falsos positivos en BigTrap2.
6. **Desenlace en bruto y umbral económico:** carrera simétrica ±X con X = fricción / 0,08; el neto es desenlace − 0,08.
7. **Contexto y moderadores** (cantidad, cercanía y edad de otros objetos, hora, volatilidad): compuerta de potencia por conteos,
   contraste entre estratos extremos y el MISMO contraste en el control (diferencia en diferencias) para separar el objeto de la
   estructura del precio.
8. **Salida como guía, no como 0/1:** `edgelab/research/recomendador.py` traduce cada resultado en categoría, lectura, próximo
   análisis y prioridad (CONFIRMAR, INDAGAR, ESTRUCTURA_DE_PRECIO, INCONSISTENTE, SIN_MUESTRA, DESCARTAR, NO_CONCLUYENTE) y escribe
   `RECOMENDACIONES_<modo>.md`. Cada módulo define `SUGERENCIAS` (el próximo análisis de cada ítem si muestra algo).
8b. **Muchas ideas sobre los mismos eventos → banco de eventos** (`docs/research/BANCO_DE_EVENTOS.md`): si la tabla ya existe, la
   idea es una especificación JSON; el banco explora en la mitad A, congela k hipótesis y las prueba en la mitad B (BH q 0,10).
9. **Réplica congelada** (una vez, mismo código) sólo para lo CONFIRMAR; **P&L con ejecución fija** sólo después de la réplica.
10. **Cierre:** RESULTADO + RECOMENDACIONES + entrada en `FACTORES.jsonl` (aunque sea SIN_FACTOR o NO_REPETIR) en el mismo commit.

## Guardas técnicas que todo detector cumple antes de lanzar
- Reloj en segundos, sesión CME, geometría congelada al detectar, sólo datos posteriores a la detección.
- Test de causalidad por prefijo y casos de borde (evento en el primer y el último tick).
- Kernel probado de punta a punta con datos sintéticos; si falla en Kaggle, leer `ERROR_KERNEL.txt` antes de tocar nada.
- Toda corrección después de lanzar se documenta como enmienda fechada; lo corrido con código viejo no se mira.

## Cómo se usa con el agente del Debian
- **Proponente:** una propuesta nueva declara en qué paso del orden está y qué produce (E0, hipótesis + control, contexto o réplica);
  sin E0 previo no propone retornos.
- **Revisor:** KILL a una propuesta con retornos sin E0, sin control que comparta la condición, o sin regla de elección escrita.
- **Meta-analista:** lee `RECOMENDACIONES_*.md` de la familia cerrada y asienta como PROPUESTO_META las INDAGAR y CONFIRMAR.
- **Herramienta para familias nuevas:** copiar la estructura de `hft_clusters_info.py` / `hft_rebotes.py` / `hft_contexto.py`
  (detector → eventos → carrera → control → contraste → `SUGERENCIAS` → recomendador).
