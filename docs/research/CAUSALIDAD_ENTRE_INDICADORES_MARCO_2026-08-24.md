# Causalidad entre indicadores — marco operativo target-free

- **Fecha:** 2026-08-24
- **Estado:** contrato metodológico; **no contiene mediciones nuevas**
- **Firewall:** no toca outcomes, retornos, P&L ni holdout; no declara edge
- **Pregunta:** cómo distinguir dependencia algorítmica, insumo común, precedencia predictiva y causalidad de mercado entre indicadores.

> Regla central: correlación, Jaccard o Granger bivariado no autorizan una flecha causal.
> Antes de preguntar por causalidad hay que identificar qué computa cada indicador, cuándo
> queda disponible y qué información común consume.

---

## 1. Cuatro relaciones distintas

| relación | pregunta | evidencia mínima |
|---|---|---|
| **dependencia algorítmica** | ¿B usa directamente un estado o salida de A? | linaje de fuente y parámetros |
| **insumo común** | ¿A y B responden al mismo tape/book/régimen? | grafo de inputs y condicionantes point-in-time |
| **precedencia predictiva** | ¿el pasado de A mejora la predicción target-free de B? | serie regular, lags congelados, baseline condicionado |
| **causalidad de mercado** | ¿una intervención sobre el mecanismo de A cambiaría B? | intervención defendible e invariancia fuera del entorno de ajuste |

Estas relaciones pueden coexistir, pero ninguna implica automáticamente la siguiente.
En particular:

- correlación no distingue `A→B`, `B→A` ni una causa común `Z`;
- Granger mide información predictiva condicional al modelo y a los lags, no causalidad por sí sola;
- Jaccard mide coincidencia de conjuntos, no dirección ni mecanismo;
- una dependencia en código puede explicar precedencia perfecta sin ninguna causalidad de mercado.

---

## 2. Estado de evidencia en EdgeLab

### Medido o verificado en fuente

- `BigTrap2Absorption` reutiliza piezas del kernel y agrega condiciones propias.
- `event_keys` representa coordenadas de eventos, no la población temporal completa.
- el sweep target-free prohíbe outcomes y advierte que el solapamiento es descriptivo.
- `ABS_SCORE` necesita la cubeta completa: su disponibilidad causal es el cierre/publicación de la cubeta, no `t_start`.

### Inferido, pendiente de medición explícita

- puede haber alta contención o coincidencia entre eventos de `BigTrap2` y
  `BigTrap2Absorption` bajo parámetros compatibles.
- tape rate y spread pueden capturar parte del estado común de liquidez/actividad.

### No medido

- contención exacta `Absorption ⊆ BigTrap2` a identidad y geometría congeladas;
- ausencia de confusores latentes;
- dirección causal entre indicadores;
- estabilidad de una red temporal entre contratos, sesiones o crypto;
- cualquier relación con retornos.

Por eso se retira la afirmación global `Absorption ⊆ BigTrap2`. La hipótesis correcta es:

> **Bajo un mapeo explícito de parámetros, identidad temporal y geometría, medir si los
> eventos de Absorption son un subconjunto de los eventos de BigTrap2.**

Si la contención aparece, primero se interpreta como linaje/filtrado computacional. Si no
aparece, la discrepancia se audita antes de aplicar un modelo temporal.

---

## 3. El atlas causal por capas

### C0 — linaje computacional

Construir un DAG desde fuente y configuración:

- inputs crudos consumidos;
- transformaciones compartidas;
- estados reutilizados;
- parámetros y condiciones adicionales;
- timestamp real de disponibilidad;
- identidad causal `(timestamp, sequence)` cuando hay empates.

C0 contesta dependencia algorítmica. No necesita estadística ni outcomes.

### C1 — grafo temporal target-free condicionado

Sólo después de C0:

1. construir una **población temporal regular** o risk set que incluya eventos y no-eventos;
2. congelar resolución, lags y política de ceros/missing;
3. condicionar por proxies point-in-time de actividad y liquidez;
4. estimar precedencia con baseline autocorrelado y control de multiplicidad;
5. ejecutar placebos de tiempo y dirección.

PCMCI, Granger condicionado o información dirigida son herramientas posibles, no sellos
de causalidad. Tape rate y spread son **proxies parciales**, no “el confundidor”. Quedan
abiertos profundidad, volatilidad, hora, sesión, noticias, latencia, venue y confusores
latentes.

### C2 — intervenciones computacionales

Intervenir donde sí hay control:

- apagar un filtro manteniendo igual el input;
- permutar o bloquear una señal intermedia;
- variar una única transformación con el resto congelado;
- comprobar si cambia B en el sentido previsto por C0.

Esto identifica dependencia del software/mecanismo implementado. No equivale todavía a
intervenir el mercado.

### C3 — invariancia

Una relación candidata debe conservar signo, timing y magnitud razonable fuera del entorno
donde se detectó:

- contratos y sesiones no usados para ajustar;
- regímenes de actividad/liquidez;
- instrumentos comparables;
- crypto, sólo tras validar unidades, join causal y microestructura 24/7.

Una flecha que desaparece al cambiar de entorno se etiqueta dependiente del régimen, no
causa estable.

### C4 — outcomes, sólo con STOP y preregistro separados

C0–C3 no dicen que un indicador tenga expectativa. Antes de abrir C4 debe existir:

- STOP explícito del descubrimiento target-free;
- conjunto de hipótesis congelado;
- métrica, horizonte, costes y multiplicidad preregistrados;
- población y holdout sellados;
- autorización escrita para abrir outcomes.

Hasta entonces: `CAMPAIGN_OUTCOMES_OPENED=false`.

---

## 4. Por qué un store sólo de eventos no alcanza

`P(evento | C)` requiere denominador. `event_keys` y `event_pit` sólo contienen instantes
con evento, por lo que no permiten estimar `P(evento)`, riesgo base ni hazard sin construir
la población de exposición.

El artefacto mínimo para C1 necesita:

- grilla temporal preregistrada;
- indicador de evento por nodo;
- tiempo en riesgo/no-evento;
- disponibilidad de cada feature;
- sesión, contrato e instrumento;
- missing explícito;
- cobertura y hash por sesión.

La resolución no es un detalle de implementación. Deben medirse al menos dos o tres escalas
congeladas y decidirse por criterios target-free de sparsity, aliasing y estabilidad, no por
resultados futuros.

---

## 5. Contrato point-in-time

Para cada feature:

```text
feature_available_at < event_time
```

Se permite igualdad sólo si existe una secuencia de publicación inequívoca y se compara
`(timestamp, sequence)`. En otro caso, igualdad es ambigua y falla cerrado.

Requisitos del store:

- `ABS_SCORE` fechado al cierre real de su cubeta;
- frontera de tape por `(ts_ns, sequence)` o `sig_idx`, no sólo timestamp;
- ventana que no cruza sesión;
- tamaño de ventana parametrizado y preregistrado;
- definición explícita de tasa (`N` observaciones cubren `N-1` intervalos);
- locked book declarado y crossed book rechazado;
- geometría en ticks enteros o medios ticks;
- `event_keys ↔ event_pit` uno-a-uno;
- schema, hash, cobertura y conteos `as_of_ok` por sesión;
- recomputación obligatoria de parciales producidos con un schema anterior.

---

## 6. Tests negativos antes de creer una flecha

1. **Placebo temporal:** desplazar A al futuro no debe “predecir” B.
2. **Permutación por sesión:** romper orden preservando tasas marginales.
3. **Control de causa común:** agregar estado de actividad/liquidez y observar atenuación.
4. **Dirección inversa:** comparar `A→B` contra `B→A` con la misma disciplina.
5. **Intervención de código:** desactivar el supuesto mecanismo de C0.
6. **Invariancia:** replicar sin reajustar en otro contrato/régimen/instrumento.
7. **Sensibilidad de binning/lags:** una flecha no puede depender de un único corte elegido después de mirar.

Si una relación falla estos controles, se conserva como asociación descriptiva.

---

## 7. Herramientas y límites

- **PCMCI/tigramite:** útil para dependencia temporal multivariada condicionada; sensible a
  variables omitidas, resolución y supuestos del test condicional.
- **Granger condicionado:** prueba precedencia predictiva bajo un modelo; no identifica una
  intervención causal por sí solo.
- **Transfer entropy/información dirigida:** capta no linealidad, pero paga estimación,
  discretización y multiplicidad.
- **QCA/fsQCA/NCA:** vocabulario útil para necesidad/suficiencia, pero su encaje con streams
  masivos de microestructura no está establecido acá. No se afirma “cero aplicaciones” sin
  una revisión bibliográfica sistemática.
- **Pearson:** resumen de dependencia lineal. No es proxy de causalidad lineal sin supuestos
  causales adicionales.

---

## 8. Orden de ejecución

1. corregir y validar el store point-in-time;
2. producir C0 desde fuente y tests de contención condicionada;
3. construir risk set regular target-free;
4. preregistrar resolución, lags, proxies y multiplicidad de C1;
5. ejecutar C2 y placebos;
6. exigir C3 fuera del entorno de descubrimiento;
7. STOP;
8. sólo con autorización separada, diseñar C4.

## Dictamen

Sí: el enfoque por atlas se usa en análisis a gran escala, pero la unidad correcta no es
“correlación entre indicadores”. Es una secuencia auditable de **linaje → dependencia
temporal condicionada → intervención computacional → invariancia**. Recién después, y bajo
otro preregistro, puede preguntarse por outcomes.
