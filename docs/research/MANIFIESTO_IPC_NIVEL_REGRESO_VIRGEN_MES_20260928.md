# Manifiesto IPC-NIVEL-REGRESO: ¿el regreso a un nivel virgen, desde lejos y con volumen, lo barre o lo respeta? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** OK de Nico (28/09: «usá terciles y corrélo, más combinaciones: más y menos volumen, más y menos distancia»).
**Familia:** IPC-NIVEL, sub-familia **REGRESO**, presupuesto propio. No rescata ni extiende el resultado de la formación
(`RESULTADO_IPC_NIVEL_MES_DESCUBRIMIENTO_20260928.md`): es otro evento.

## 1. Hipótesis y refutación
- **Hipótesis (Nico):** un nivel IPC-NIVEL que quedó **virgen** (sin volver a tocarse desde que se formó), del que el precio
  se **alejó mucho** y **negoció mucho volumen** antes de volver, se comporta distinto al regreso. Bilateral: puede
  barrerse más (imán) o resistir más (lo observado en la formación).
- **Justificación:** la liquidez acumulada en el nivel sigue intacta mientras es virgen; cuanto más lejos y con más volumen
  se fue el precio, más posiciones quedaron del otro lado con stops detrás del nivel.
- **Cómo podría refutarse:** ninguna celda distancia × volumen difiere del nulo ni del pivote suelto en la misma celda.

## 2. Población (regla de población)
Eventos del nivel enumerados: formación, visitas, primer barrido, **primer regreso tras alejarse**, expiración, estado
continuo. **Se congela: el primer regreso** tras un alejamiento ≥ 14 t (la misma salida que define una visita), dentro
de la misma sesión y con el nivel virgen hasta ese momento.

## 3. Evento, rasgos y resultado
- **Nivel:** detector v2 congelado; se forma (causal) en la confirmación de la 3.ª visita. Ref = pico extremo del nivel.
- **Evento:** primera vela, posterior a la formación, en que el precio vuelve a ≤ 2 t del ref habiéndose alejado antes
  ≥ 14 t, sin haber tocado el ref en el medio (virgen). Si lo barre antes de alejarse, no hay evento.
- **Rasgos (causales, entre la formación y el evento):** D = distancia máxima al ref (ticks); V = volumen negociado ÷
  (mediana de volumen por vela de la sesión antes de la formación). Descriptivo: velas afuera.
- **Terciles** de D y de V fijados sobre los eventos de zona del descubrimiento, sin mirar resultados → 9 celdas.
- **Resultado:** barre (≥ 2 t más allá del ref) antes de rebotar 14 t desde el ref; horizonte 200 velas o fin de sesión.
- **Nulo:** `simulate_null` con ternas 25t estrictamente anteriores a la vela del evento, sin agrupar.
- **Control:** pivotes sueltos del zigzag (fuera de toda zona) con el mismo proceso (virgen, alejamiento ≥ 14 t, primer
  regreso), clasificados con los mismos cortes de D y V.

## 4. Pruebas
Por lado (techo, piso) y celda (D tercil × V tercil): P1 = barre − p0 (zona); P2 = (barre − p0) zona − control.
**36 pruebas**, bilaterales, BH q = 0,10, bootstrap por sesión. Se publican las 36, con n, MDE y los dos canales.

## 5. Datos
MES 25t (Lucid, precio de trade), ago-2025 → mar-2026, 171 sesiones. Confirmación única abr–jun 2026. Holdout oct+.

## 6. Riesgos
- 36 celdas: muchas quedarán sin potencia; se publica el MDE de cada una.
- Precio de trade (sin midquote en MES): barrido exige 2 t.
- D y V están correlacionados (más lejos suele ser más volumen): las celdas fuera de la diagonal tendrán menos eventos.
