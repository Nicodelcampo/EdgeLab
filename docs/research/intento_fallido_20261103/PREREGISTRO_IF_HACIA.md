# Pre-registro: INTENTO-FALLIDO-HACIA (Nico, 03/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 exploratorio**.
Código: `edgelab/research/intento_fallido_b80.py` (+ `intento_fallido_hacia_lux`, `_racimos`); tests `tests/research/test_intento_fallido_b80.py`.
Padre: INTENTO-FALLIDO v2 (pista destacada B80_HACIA, `RESULTADO_INTENTO_FALLIDO.md`).

## Pedido de Nico

«Agregar variables: cuánto se alejó desde que se creó la zona, cómo es la zona (nivel de comercio sobre ella), cuánto se acercó luego de
alejarse, cuánto se alejó luego de acercarse y cuánto se acercó otra vez; cuántas velas tiene cada pierna (¿la cantidad de velas de algún
impulso cambia el resultado? p. ej. si hace 50 velas al alejarse, ¿tiene más probabilidad de llegar a la zona al alcanzar el 80 % que si
hace 10, o al revés?); probar varias lógicas de entrada; reutilizar lo que ya está armado; correrlo sobre los mejores tipos de zona».

## Diseño

- **Evento**: el de INTENTO-FALLIDO con umbrales **mínimos**: lo más cerca ≤ 0,33·A sin tocar, rechazo ≥ 0,10·A. La gradación de
  cuánto se acercó y cuánto rechazó pasa a ser **variable**, no corte. Después, la recuperación r ∈ {50 %, 80 %, 100 %} del rechazo
  (variable de grupo). **Siempre se entra hacia la zona.**
- **Variables** (terciles de DESC, «extremos»: bajo / alto / cualquiera; todas causales al cierre de la decisión):
  - `A/H`: cuánto se alejó desde la zona;
  - `vol_zona`: comercio sobre la zona, como volumen medio de las velas que la tocaron desde su marca, sobre la sesión anterior;
  - `acerco`: cuánto se acercó, 1 − dist/A;
  - `rechazo`: cuánto se alejó después, en unidades de A;
  - `dur_ida`, `dur_aprox`, `dur_rech`, `dur_reac`: velas de cada una de las cuatro piernas.
  
  **Velas**: el motor corre en M1, así que las duraciones son minutos. Las velas de 25 ticks no están en la tubería de la grilla.
  Si alguna duración resulta relevante, una hija la mide en barras de ticks.
- **Entradas**:
  - MERC: tick siguiente;
  - CONF: espera una vela más que cierre hacia la zona;
  - LIM: límite al 25 % del reacercamiento hacia atrás, vigente 120 velas.
- **Stop y TP**: el stop va un tick más allá del extremo del rechazo. TP: Z1/Z2/Z3 (borde cercano, medio o lejano de la zona) o 2R.
- **Celdas**: 3 × 3⁸ = 19.683 celdas × 12 ejecuciones = **236.196 por canal**.
- **Noticias**: sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato.

## Campañas (los mejores tipos de zona según la v2)

| Campaña | Zonas | Por qué |
|---|---|---|
| IFH-LUX-CFD-NQ-R | LUX-IMB en USATECH → NQ (U1-CRUZADO) | La fuente original de la idea; la única que operó en real (JForex) |
| IFH-LUX-NQ-R | LUX-IMB sobre NQ | La réplica más positiva de la v2 (+0,12R) |
| IFH-RACIMOS-NQ-R | racimos aVolZonePOI2 en NQ | La de más eventos (320 nominadas en DESC) |

AVCL no se corre: tuvo pocos eventos (286 celdas evaluables de 3.888). Linaje: hijas de INTENTO-FALLIDO de su fuente; heredan su multiplicidad.

## Justificación económica y cómo podría refutarse

- **Justificación:** si la zona sigue siendo un imán después del intento fallido, el reacercamiento que recupera el rechazo es el segundo
  intento. La forma de las piernas (duración y profundidad) y el comercio sobre la zona deberían separar los intentos que llegan de los que no.
- **Refutación:**
  - ninguna celda nominada por FDR q 0,10 (cola t) ni pista que replique en abr–sep;
  - ninguna variable de piernas ni de volumen separa: la celda «cualquiera» rinde igual que las filtradas;
  - falla de integridad (placebo o latencia).
