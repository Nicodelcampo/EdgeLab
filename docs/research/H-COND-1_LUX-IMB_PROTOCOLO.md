# H-COND-1 — Familia LUX-IMB (OG/VI) y protocolo de efectos condicionales

**Fecha:** 2026-08-10  
**Corrección de fuente:** 2026-08-11  
**Estado:** protocolo corregido. Nada ejecutado.  
**Gate:** bloqueado hasta cerrar el incidente P0 de procedencia y completar paridad Pine→NT8.

> **Familia registrada:** `LUX-IMB` — indicador `Imbalance Detector [LuxAlgo]`, restringido a **Opening Gap (OG)** y **Volume Imbalance (VI)**. Fair Value Gap queda **fuera de alcance** por decisión del operador.
>
> **Esta familia es independiente de BigTrap2.** No hereda resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad.

Nada de este documento afirma un edge ni autoriza outcomes.

---

## 0. Corrección obligatoria de la fuente

El protocolo anterior atribuía al indicador dos propiedades que no corresponden
a la configuración observada por el operador:

1. que las zonas mitigadas desaparecían automáticamente;
2. que existía un input llamado `Mitigation Method`.

Ambas afirmaciones quedan **retiradas**. En el indicador usado por Nico las
zonas no desaparecen por mitigación, y los parámetros que deben exportarse son:

- selector `Imbalance`, con **OG y VI activos** y **FVG apagado**;
- `Min Width`;
- `Extend`;
- timeframe;
- instrumento/contrato y plantilla de sesión.

No se debe volver a pedir ni inventar un método de mitigación. `Extend` se trata
como parámetro de proyección visual hasta reproducir exactamente su semántica
desde el Pine original.

La corrección elimina el argumento de “supervivencia por borrado”. El ledger
as-of sigue siendo obligatorio, pero por otra razón: impedir hindsight,
selección de capturas, ambigüedad de toques, densidad de zonas y cambios de
parámetros; no para reconstruir zonas supuestamente desaparecidas.

---

## 1. Pregunta falsable

> ¿El precio reacciona en zonas OG/VI más de lo que reaccionaría en intervalos
> comparables, y existe una función condicional replicable que prediga cuándo?

La unidad primaria es el **primer encuentro elegible zona-precio**, adjudicado
con información disponible hasta ese instante. OG y VI son dos subfamilias
separadas, con nulos, estimandos y multiplicidad propios.

---

## 2. Por qué un resultado marginal nulo no cierra la hipótesis condicional

Si los encuentros se reparten en condiciones `c`, con peso `pi_c` y efecto
`Delta_c`:

```text
Delta_marginal = sum_c pi_c * Delta_c
```

### Dilución

Un efecto de 0,20 presente en 10% de los encuentros produce un marginal de
0,02, posiblemente por debajo del MDE.

### Cancelación

Rechazo en un régimen y aceleración en otro pueden promediar cero aunque ambos
sean reales. Por eso se reportan en paralelo:

- canal direccional;
- canal no direccional (magnitud/volatilidad);
- distribución completa;
- primera llegada con riesgos competitivos.

Un nulo sin MDE publicado es ininterpretable.

---

## 3. OG y VI no se agrupan

| Aspecto | Opening Gap (OG) | Volume Imbalance (VI) |
|---|---|---|
| Geometría candidata | Mechas adyacentes sin solapamiento | Cuerpos sin solapamiento con mechas solapadas |
| Contenido | Intervalo sin negociación entre velas | Hubo negociación, pero no solapamiento de cuerpos |
| Confusor dominante | Hora, corte/reapertura, noticias y liquidez | Densidad/cobertura del eje de precio |
| Control prioritario | Matching por fase de sesión y volatilidad | Casi-zonas y cobertura precio-tiempo |

Las fórmulas exactas, desigualdades de borde y disponibilidad temporal se toman
del Pine exportado; esta tabla es conceptual y no sustituye el código fuente.
La implementación NT8 no se usa para outcomes hasta pasar paridad.

---

## 4. Amenazas principales después de la corrección

### 4.1 Selección retrospectiva

Una captura puede elegirse porque el giro ya ocurrió. La evidencia formal usa
un censo de todas las zonas y encuentros, no ejemplos visuales. La etiqueta de
resultado se mantiene oculta durante la construcción del detector y el matching.

### 4.2 Densidad y cobertura

Para tolerancia `k`:

```text
C(k) = (1/T) * sum_t 1(existe una zona activa a distancia <= k de P_t)
```

Si `C(k)` es alta, “había una zona cerca” es casi inevitable. Se publican curvas
completas de cobertura por subfamilia, fase de sesión, `Min Width`, `Extend` y
`k`; queda prohibido elegir una tolerancia después de ver la reacción.

### 4.3 Hora, liquidez y noticias

OG puede ser casi colineal con reaperturas, publicaciones macro y horarios de
baja profundidad. Sin matching por fase de sesión, volatilidad y liquidez no se
adjudica efecto a la zona.

### 4.4 Solapamiento y múltiples zonas

Una observación puede estar expuesta simultáneamente a varias zonas OG/VI. El
ledger registra todas; la regla de adjudicación primaria se congela antes de
medir y los encuentros ambiguos no se asignan silenciosamente al nivel que
“funcionó”.

---

## 5. Contrato de parámetros del chart

La población no queda definida hasta exportar y hashear:

- [ ] OG activo;
- [ ] VI activo;
- [ ] FVG apagado;
- [ ] modo y valor exactos de `Min Width`;
- [ ] valor exacto de `Extend`;
- [ ] timeframe de detección;
- [ ] instrumento y contrato;
- [ ] plantilla/calendario de sesión;
- [ ] versión o digest del Pine disponible.

No forman parte del contrato porque no son inputs observados: `Mitigation
Method`, parámetros FVG ni reglas heredadas de BigTrap2.

---

## 6. Ledger as-of

Campos mínimos por zona:

- `zone_id`, `instrument`, `contract`, `session_id`, `bar_spec`;
- `subfamily` (`OG` o `VI`) y dirección;
- barra/timestamp de creación y `available_at`;
- límites `L/U`, ancho en ticks y ancho normalizado por volatilidad;
- `min_width_mode/value`, `extend`, timeframe y digest de parámetros;
- barras iniciales que originan la geometría;
- estado de proyección/render por barra según el Pine;
- todos los contactos, penetraciones y cruces, con ordinal y timestamp;
- zonas concurrentes y regla de adjudicación;
- hashes del Pine, del port NT8 y del dataset.

**Auditoría causal:** para cada prefijo de datos hasta `t`, el detector debe
producir exactamente las mismas zonas con `available_at <= t` que el ledger
completo restringido a ese prefijo. Toda discrepancia bloquea outcomes.

---

## 7. Paridad Pine → NT8

La lógica debe portarse a NT8, pero el port no se declara correcto por parecerse
en pantalla. Sobre fixtures exportados desde TradingView se comparan conjuntos
de zonas con la misma identidad temporal y geométrica.

Para cada fixture:

```text
J = |Z_pine ∩ Z_nt8| / |Z_pine ∪ Z_nt8|
```

Además de `J`, se comparan por zona: subfamilia, dirección, barra de creación,
`available_at`, `L`, `U` y extensión. Reglas:

- fixtures sintéticos de borde: coincidencia exacta;
- fixtures reales: toda diferencia se publica fila por fila;
- ninguna corrida económica puede usar NT8 mientras exista una divergencia no
  adjudicada;
- mover una desigualdad, redondeo o timestamp exige nueva versión y nuevo hash.

---

## 8. Controles negativos

1. **C1 — niveles aleatorios emparejados** por sesión, hora, distancia inicial,
   ancho, volatilidad y liquidez.
2. **C2 — intervalos sintéticos de geometría idéntica** que replican anchos y
   posiciones sin cumplir la regla OG/VI.
3. **C3 — casi-zonas**, candidatos que fallan el criterio por el margen mínimo:
   un tick de solapamiento para OG o solapamiento corporal mínimo para VI,
   sujeto a la desigualdad exacta del Pine.
4. **C4 — desplazamiento temporal**, conservando geometría y moviendo la zona a
   una fase vecina de sesión.

No debe aparecer una discontinuidad económica creada únicamente por el valor
visual elegido de `Min Width`. Horizontes, tolerancias y anchos se publican como
superficies completas.

---

## 9. Resultados y riesgos competitivos

### Canales

1. direccional: movimiento con signo;
2. no direccional: magnitud absoluta, volatilidad realizada y tasa de giro;
3. distribucional: distancia de energía y pruebas de distribución contra nulo;
4. primera llegada: rechazo frente a continuación, con censura.

Para encuentro `i`:

```text
T_R = primer tiempo hasta el umbral de rechazo
T_C = primer tiempo hasta el umbral de continuación
```

Se estima incidencia acumulada puntual con **Aalen–Johansen**, tratando rechazo
y continuación como riesgos competitivos. No se usa `1-KM` por causa porque
sobreestima incidencia cuando el otro evento impide el primero. La incertidumbre
se obtiene con bootstrap cluster por sesión.

Un resultado admisible es: “la zona predice que ocurrirá movimiento, pero no su
dirección”. Eso es información descriptiva, no un edge operable.

---

## 10. Heterogeneidad: orden obligatorio

1. **Contrastes dirigidos pre-registrados** con signo predicho.
2. **Omnibus de heterogeneidad** dentro de sets emparejados.
3. Sólo si el omnibus rechaza y hay positividad: **CATE con cross-fitting**.
4. Mejor predictor lineal y estabilidad entre particiones.
5. Requisito de forma: región suave, no celda aislada.
6. Romano–Wolf stepdown para moderadores.
7. Descubrimiento y confirmación disjuntos; holdout cerrado.

Moderadores candidatos: ancho/volatilidad, velocidad de aproximación, ordinal
del toque, edad, confluencia, volumen de creación, fase de sesión y profundidad.
La lista y los signos se congelan antes de outcomes; agregar uno después implica
nueva campaña.

---

## 11. MDE y multiplicidad

Para diferencia pareada con `S` sesiones:

```text
MDE = (z_(1-alpha/2) + z_power) * sigma_D / sqrt(S)
```

Cada resultado publica MDE, tamaño efectivo y cobertura. Presupuesto inicial:

- **primarios: 2**, un omnibus no direccional por OG y VI;
- **secundarios: 16**, ocho moderadores por subfamilia bajo Romano–Wolf;
- demás curvas: exploratorias, sin capacidad de adjudicar.

Si la positividad falla en un moderador, ese CATE no se estima; no se extrapola.

---

## 12. H-PERCEPT-1 corregido

El test perceptual ya no contrapone “zonas visibles” contra “zonas borradas”.
Usa dos tareas válidas:

### Tarea A — discriminación real/nulo

Fragmentos con zonas reales y controles emparejados, sin nombre, fecha ni escala
identificable. Se mide exactitud, Wilson, Brier y calibración.

### Tarea B — predicción forward-only

Se muestra únicamente información disponible antes del primer encuentro y se
pide anticipar rechazo, continuación o ninguna. Las etiquetas se revelan sólo
al cerrar el lote.

Si el desempeño supera controles, se congela una regla que aproxime la intuición
y se prueba en datos intactos. Mirar correctamente retrospectivamente no cuenta
como capacidad predictiva.

---

## 13. Criterios de muerte

- OG/VI no superan controles C1–C3;
- el efecto desaparece al controlar fase de sesión/volatilidad;
- el omnibus de heterogeneidad no rechaza;
- el CATE no calibra fuera de muestra o falla positividad;
- el efecto vive en una celda aislada;
- no replica en confirmación;
- la paridad Pine→NT8 no puede cerrarse;
- sobrevive estadísticamente pero queda por debajo de costos: `informativo pero
  sub-fee`.

---

## 14. Implementación por etapas

1. exportar parámetros permitidos y Pine/versiones;
2. construir fixtures sintéticos de desigualdades y bordes;
3. reimplementar OG/VI causalmente en Python y NT8;
4. cerrar paridad Pine↔Python↔NT8;
5. producir ledger as-of y auditoría de prefijos;
6. medir cobertura precio-tiempo y solapamiento;
7. construir controles y matching;
8. ejecutar competing risks/Aalen–Johansen con bootstrap por día;
9. ejecutar omnibus; CATE sólo si habilitado;
10. aplicar Romano–Wolf y partición de confirmación;
11. monetizar una sola regla únicamente si sobreviven las etapas anteriores.

---

## 15. Gate de ejecución

Nada se ejecuta sobre outcomes hasta:

- cerrar el incidente P0 de procedencia;
- exportar `Imbalance`, `Min Width`, `Extend`, timeframe y contrato;
- confirmar OG/VI on y FVG off;
- cerrar el ledger causal;
- cerrar paridad Pine→NT8.

El holdout sigue intacto.

---

## 16. Referencias de trabajo

- Script observado: <https://www.tradingview.com/script/C0cC294Q-Imbalance-Detector-LuxAlgo>
- Conceptos de desequilibrio: <https://docs.luxalgo.com/docs/algos/price-action-concepts/imbalances>
- Inferencia genérica sobre efectos heterogéneos: <https://arxiv.org/abs/1712.04802>
- Bosques causales honestos: <https://grf-labs.github.io/grf/reference/causal_forest.html>
- Romano–Wolf: <https://ftp.iza.org/dp12845.pdf>
- Impacto de precio del desequilibrio de flujo: <https://arxiv.org/abs/1011.6402>
