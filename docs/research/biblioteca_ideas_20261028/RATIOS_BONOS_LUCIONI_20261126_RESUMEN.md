# Ratios de bonos argentinos (GD30/AL30 y pares de ley local contra ley extranjera), charla de Gus Lucioni en VetaCap (2026-11-26)

Estado: REFERENCIA (fuente de ideas sin validar; no es evidencia).

## Fuente
- Video: https://www.youtube.com/watch?v=qyroziWDJjs, «La clave del mercado de bonos (GD30 / AL30) con Gus Lucioni», canal VetaCap.
  Publicado el 2026-11-26, dura 38:02.
- Transcripción completa: `RATIOS_BONOS_LUCIONI_20261126_TRANSCRIPCION.md`. Son subtítulos automáticos de YouTube en español, con
  errores de reconocimiento (cifras como «0 3» = 0,3 %).
- Los fotogramas no se pudieron ver: YouTube bloquea la descarga desde el contenedor de la sesión. Lo que se muestra en pantalla se
  reconstruye de lo que dice el orador.

## Resumen de la operatoria
- **Instrumento:** el ratio (cociente de precios) entre dos bonos del mismo emisor con flujo de fondos casi idéntico, que difieren sólo
  en la legislación: ley local (AL, AE) contra ley Nueva York (GD).
  - Pares que recomienda: GD30/AL30 («el de cabecera»), GD35/AL35, GD35/AL38, GD38/AE38, AE38/GD41 y GD41/AL41.
  - Entre bonos en pesos: TZX28/TZXS8 y S8/M9.
- **Por qué no tiene dirección:** mismo flujo y mismo riesgo, así que lo que desarbitra el ratio son flujos puntuales de mercado («alguien
  saliendo o entrando»), no el riesgo país.
- **Lectura:**
  - ratio intradía en velas de 5 segundos a 30 minutos;
  - referencias: el promedio de la rueda anterior, la media de 200 y las bandas de Bollinger;
  - «cuando está muy lejos del promedio, amerita rotar»;
  - los mejores casos son cuando rompe la banda lejos del promedio.
- **Historial:** sólo uno o dos meses. Con historia más larga el nivel cambia de régimen:
  - intervención del AL30, cuando el ratio llegó a 1,32;
  - cupones que cambiaron (AE38/GD41).
- **Tamaño:** rota en tandas y nunca todo. Deja siempre un 20–25 % sin rotar, como reserva para promediar si el ratio sigue alejándose.
  - En el promedio va 50/50 (o 60/40 según el promedio de 3 meses).
  - En extremos, 80/20.
- **Márgenes:** 0,15 %–0,5 % por operación intradía; 0,7 %–1 % en swing de 2–3 días.
  - Sólo es viable sin comisión por operación (cuenta de abono mensual fijo, «flat»).
  - Hace falta venta en descubierto con bonos prestados por el broker, o bonos propios.
  - Opera en pesos porque son más líquidos que las especies en dólares.
- **Filtros que impone:**
  - los dos bonos líquidos y con liquidez pareja (el spread de 0,3 % del GD29 «mata» el ratio aunque se vea volátil);
  - misma duration: descarta GD35/AL30 y AO28/AO29, que se volvieron direccionales con el riesgo país;
  - volatilidad suficiente (descarta GD38/GD41 por quieto);
  - de 1 a 3 ratios, siempre los mismos.
- **Pista transversal:** la brecha ley NY / ley local no es pareja entre pares.
  - GD30/AL30 está en 1,03, contra 1,08–1,09 en GD35/AL35, GD38/AE38 y GD41/AL41.
  - Propone una operación calzada entre pares (long GD30/short AL30 contra long AE38/short GD38).
- **Horario:** la liquidez aparece al principio de la rueda y a las 14–15; en el almuerzo y al cierre del viernes no hay contraparte.

## Lectura para EdgeLab (sin medir)
- **Mecanismo plausible:** un mismo flujo de fondos con un precio desalineado por flujos locales, como el arbitraje de clases de un mismo
  activo. El ratio debería ser estacionario en ventanas cortas, con cambios de nivel por régimen (cepo, intervención, cupones).
- **Cómo podría refutarse:** con datos intradía y costo real (abono más spread medido de compra y venta), la regla exacta de la charla
  no deja ganancia neta. Otra forma: el ratio no vuelve a la media dentro de la sesión o del horizonte de 2–3 días.
- **Amenazas conocidas en EdgeLab:**
  - margen bruto del orden del spread, la misma familia de falla que `F-SELECCION-ADVERSA-PASIVA`;
  - historial corto elegido después de mirar;
  - selección de pares por cómo se ven hoy.
- **Qué falta para medirlo:**
  - intradía de BYMA de los pares, con puntas o spread;
  - el costo del abono y del alquiler de bonos;
  - un broker que preste los bonos.

  Es un mercado y una fuente nuevos: abrirlos es decisión de Nico.
- **No transferir a los futuros actuales:** no hay pares de mismo flujo con distinto envoltorio que se descalcen. ES/MES es el mismo
  contrato, y ES/NQ tiene distinto beta, justo lo que la charla descarta.
- **Si se mide, el orden es el de siempre:**
  1. sin mirar resultados: estacionariedad y vida media del ratio;
  2. la regla exacta con costos y bloques A5;
  3. pre-registro con potencia previa antes de cualquier P&L.
