# H-SWEEP-1 — YM-PRERANGE: rango 08:12–09:12 y barrido del extremo opuesto

**Fecha:** 2026-08-10  
**Corrección y formalización:** 2026-08-11  
**Estado:** hipótesis registrada; extractor implementado; outcomes no ejecutados.  
**Familia:** independiente de BigTrap2 y LUX-IMB.

> Observación inicial del operador: en seis jornadas consecutivas de YM, el
> precio pareció tomar un extremo del rango 08:12–09:12 y luego el opuesto en
> cinco de seis casos. La racha justifica construir una medición; no constituye
> evidencia de edge.

Nada de este documento autoriza abrir el holdout ni operar.

---

## 0. Correcciones de procedencia visual

1. **“Tokyo” no identifica una sesión de mercado.** Era un indicador cualquiera
   usado sólo para colorear la ventana temporal en TradingView. No se lo trata
   como variable, causa ni confusor.
2. **TradingView fue un bloc de observación.** Las capturas registran la idea de
   rango y toma de extremos; no son el dataset de investigación.
3. **No se adjudica cuál día falló.** El registro válido es 5/6. En el caso
   fallido, el precio quedó cerca del segundo extremo y reaccionó en una zona
   LUX; eso se registra como pista para una interacción futura, no como excusa
   para reclasificar el día.
4. La hora se define con `America/New_York`, no con un offset EST fijo. El código
   debe resolver EST/EDT por calendario.

---

## 1. Observación semilla

- Instrumento visual: `YM1!`, CBOT, barras de 1 minuto.
- Ventana declarada: 08:12–09:12 hora de Nueva York.
- Racha visual: 5/6.
- Rangos aproximados anotados en las capturas, en puntos:
  `104, 153, 79, 94, 121, 188`.
- Media descriptiva: 123,2 puntos.
- Mediana descriptiva: 112,5 puntos.
- Especificación económica de YM: tick de 1 punto; USD 5 por punto/contrato.

Los seis valores no se usan para seleccionar thresholds, horizonte ni stop.
Son procedencia de la hipótesis y control de que la extracción automatizada
esté midiendo la misma geometría.

---

## 2. Ventana candidata y decisión de endpoint

La implementación propone como contrato primario:

```text
W_d = [08:12, 09:12) America/New_York
```

Son 60 barras M1, desde 08:12 hasta 09:11, equivalentes a offsets RTH
`m_rth = -78,...,-19` respecto de 09:30.

La captura podría haber contado también la barra 09:12. Por eso, antes de
recontar las seis jornadas se debe hacer una reconciliación **sin outcomes**:

- especificación A: `[08:12,09:12)`, 60 barras;
- especificación B: `[08:12,09:13)`, 61 barras, si la convención visual incluía
  la barra rotulada 09:12.

Se elige la que reproduzca la geometría dibujada en las seis capturas. La otra
queda como sensibilidad declarada; no se escoge según cuál eleve 5/6.

---

## 3. Geometría formal

Para cada sesión elegible `d`:

```text
H_d = max(high_t : t in W_d)
L_d = min(low_t  : t in W_d)
R_d = H_d - L_d
```

Un día sólo es válido si:

- pertenece al calendario elegible congelado;
- tiene la primera barra de la ventana;
- tiene las 60 barras esperadas para el análisis primario;
- no tiene minutos duplicados;
- instrumento, contrato y rollover cumplen el manifiesto.

Los días elegibles sin datos no desaparecen: permanecen como fila `NaN`. El
resultado persiste el SHA-256 del calendario completo.

---

## 4. Evento de dos extremos

Después del cierre de la ventana, sean:

```text
T_H = primer t elegible con high_t >= H_d
T_L = primer t elegible con low_t  <= L_d
T_1 = min(T_H, T_L)
```

El primer extremo es `H` si `T_H < T_L`, `L` si `T_L < T_H`. Si ambos se tocan
en la misma barra M1, el orden es ambiguo y se aplica una de estas reglas,
congelada antes de outcomes:

1. resolver con ticks point-in-time si están disponibles;
2. si no, clasificar `simultáneo/ambiguo`, sin imponer un orden favorable.

El segundo evento es el primer toque del extremo opuesto después de `T_1`:

```text
T_2 = inf{t > T_1 : low_t <= L_d}   si H fue primero
T_2 = inf{t > T_1 : high_t >= H_d}  si L fue primero
```

**Éxito primario:** `T_2` ocurre antes del horizonte `tau_d`.  
**Censura:** la sesión termina o vence `tau_d` sin segundo toque.  
**Fallo:** no se alcanza el extremo opuesto; “quedó cerca” no se recodifica.

El horizonte todavía no está congelado porque faltan las seis fechas y la
convención exacta de las capturas. Ningún recuento formal comienza antes de
registrar `tau_d` (por ejemplo, fin de RTH o una hora fija) en el manifiesto.

---

## 5. Dos estimandos distintos

### 5.1 Probabilidad geométrica

```text
p2 = P(T_2 <= tau_d | T_1 observado)
```

Pregunta si el extremo opuesto se alcanza más que en controles comparables.
No implica por sí sola una estrategia.

### 5.2 Resultado económico

Una operación exige entrada, `available_at`, fill, stop, target, vencimiento y
costos. Se registra como hipótesis posterior y separada. Una tasa alta de doble
toque puede ser inoperable si la excursión adversa o el tiempo hasta `T_2` son
demasiado grandes.

**Regla constitucional:** justificar una medición no justifica una operación.

---

## 6. Por qué 5/6 no alcanza

Bajo un baseline binomial con probabilidad `p0`:

```text
P(X >= 5 | n=6,p0) = 6*p0^5*(1-p0) + p0^6
```

Con `p0=0,5`, la cola es `7/64 = 10,94%`: ni siquiera rechaza una moneda al 5%.
Y 0,5 no es el nulo natural: al condicionar en que un extremo ya fue tomado,
la probabilidad de alcanzar el otro puede ser alta por pura volatilidad y por
un horizonte largo.

Para un paseo sin drift entre `L` y `H`, partiendo de `x`:

```text
P_x(tocar H antes que L) = (x-L)/(H-L)
P_x(tocar L antes que H) = (H-x)/(H-L)
```

Esas fórmulas ilustran que el baseline depende de ubicación, rango, horizonte y
volatilidad; no prueban el fenómeno intradía real. La decisión sale de nulos
condicionados y datos fuera de las seis capturas.

---

## 7. Nulos obligatorios

### N0 — días emparejados

Misma ventana aplicada a días de desarrollo no seleccionados, emparejados por:

- contrato/roll;
- día de semana;
- volatilidad pre-08:12;
- ancho de rango normalizado;
- overnight gap;
- fase de calendario macro si se dispone de fuente ex ante.

### N1 — ventanas placebo dentro del día

Desplazar la ventana preservando duración, separación respecto de RTH y
cobertura. Publicar toda la superficie de offsets; no elegir un horario porque
funcionó.

### N2 — puente/proceso condicionado

Simular trayectorias condicionadas en `R_d`, volatilidad y estado al cierre de
la ventana. El nulo debe preservar las variables que por sí solas elevan la
probabilidad de doble toque.

### N3 — etiquetas/permutaciones por sesión

Permutar la identidad 08:12–09:12 entre días emparejados, conservando sesiones
completas. Es el test decisivo contra “cualquier rango de una hora hace lo
mismo”.

Cada nulo se versiona y usa al menos 1.000 réplicas. No existe un MCPT universal.

---

## 8. Resultados a publicar

Por sesión:

- `H_d`, `L_d`, `R_d` y cobertura;
- extremo tomado primero y `T_1`;
- indicador de segundo toque y `T_2-T_1`;
- MAE/MFE desde `T_1`;
- distancia mínima al extremo opuesto en censurados;
- zonas LUX concurrentes, sólo como covariable registrada as-of;
- razón de exclusión, nunca eliminación silenciosa.

Agregados:

- incidencia acumulada de segundo toque;
- curvas por tiempo desde `T_1`;
- bootstrap cluster por sesión;
- comparación pareada contra N0–N3;
- MDE publicado;
- canal direccional y no direccional.

Si se modelan eventos competidores (segundo toque, stop económico, fin de
sesión), usar Aalen–Johansen; no tratar el competidor como censura independiente.

---

## 9. Potencia y tamaño de muestra

Para comparar `p1` contra `p0`, una aproximación inicial es:

```text
n ~= [z_(1-alpha/2)*sqrt(2*pbar*(1-pbar))
      + z_power*sqrt(p0*(1-p0)+p1*(1-p1))]^2 / (p1-p0)^2
```

El cálculo final usa diferencia pareada por sesión y bootstrap/permutación del
estimando real. El objetivo no es “llegar a significancia”, sino declarar qué
diferencia mínima podría detectar el calendario disponible. Seis días no
permiten esa adjudicación.

---

## 10. Interacción futura con LUX-IMB

El día visualmente fallido pareció reaccionar a una zona LUX antes del segundo
extremo. Esto genera una hipótesis **nueva**:

```text
H-SWEEP-1e:
la incidencia de segundo toque cambia cuando existe exposición OG/VI as-of
entre T_1 y el extremo opuesto.
```

No convierte el fallo en éxito y no se prueba hasta que LUX-IMB tenga paridad
Pine→NT8. Requiere omnibus de heterogeneidad, positividad y multiplicidad.

---

## 11. Implementación disponible

`edgelab/sessions.py` incorpora:

- `minute_window_matrices()` con `America/New_York`;
- calendario explícito y `calendar_sha256`;
- preservación de días faltantes como matrices `NaN`;
- detección de timestamps duplicados y barras fuera del calendario;
- soporte UTC naive/aware y ventanas cruzando medianoche;
- `ym_prerange_matrices()` para `[08:12,09:12)`;
- compatibilidad con `build_session_matrices()` y `rth_matrices()`.

Los tests cubren enero/EST, agosto/EDT, calendario incompleto, duplicados,
compatibilidad RTH y cruce de medianoche.

---

## 12. Calendario YM

La lista elegible debe provenir de una fuente CME Equity/CBOT verificable. No se
sustituye por un calendario federal aproximado. Candidatos de implementación:

- calendario oficial CME del E-mini Dow;
- `pandas_market_calendars` si su `CME_Equity` reproduce exactamente cierres,
  feriados y sesiones parciales de YM;
- `exchange_calendars`/`CMES` sólo después de una prueba de equivalencia.

La fuente, versión, rango y digest quedan en el manifiesto.

---

## 13. Gates antes de medir

- [ ] recuperar las seis fechas exactas;
- [ ] reconciliar endpoint 60/61 barras sin mirar el recuento resultante;
- [ ] congelar `tau_d`;
- [ ] congelar igualdad/inclusión del toque y resolución intrabar;
- [ ] seleccionar calendario oficial y persistir su SHA-256;
- [ ] congelar roll de contrato y días parciales;
- [ ] registrar nulos, matching, MDE y multiplicidad;
- [ ] completar tests de paridad contra fixtures manuales;
- [ ] mantener holdout cerrado.

Hasta completar la lista, 5/6 sigue siendo **motivación para medir**, no evidencia.

---

## 14. Criterios de muerte

- la incidencia no supera días/ventanas placebo;
- el efecto desaparece al condicionar en rango, volatilidad y horizonte;
- depende de una convención de endpoint elegida ex post;
- no replica fuera de las seis jornadas;
- sobrevive geométricamente pero MAE/tiempo/costos lo vuelven inoperable;
- aparece sólo al reclasificar “casi llegó” como éxito;
- la interacción LUX carece de positividad o paridad.

---

## 15. Próxima acción legítima

Cerrar los metadatos de las seis capturas y el calendario. Después, ejecutar
únicamente extracción y paridad geométrica sobre desarrollo. La primera corrida
de outcomes ocurre una sola vez con protocolo y digests congelados.
