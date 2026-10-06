# AVCL-EXIT — la SALIDA de la zona como evento (dirección conocida) — manifiesto — 2026-10-06

Aprobado por Nico en el chat ("Si, probá esas configuraciones", con k ∈ {4, 8, 16}).
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información direccional, **no P&L**.

## Por qué (observación de Nico, 6 capturas de MNQ 200t)
La expansión que se ve en el chart no siempre arranca en la creación. A veces arranca enseguida, y a veces después de
que el precio consolida alrededor de la zona y **sale** por un lado. Varias SOP se forman en techos y el precio las
**atraviesa**. Todo lo medido hasta ahora estaba anclado a la creación, y eso mezcla los dos casos.

## Población (enumeración previa)
Espacio de eventos: creación (medido), roce inmediato (medido, SR-DIR), **salida de la banda** (este manifiesto),
toque n-ésimo, invalidación, expiración, confluencia, estado (no medidos). Se congela **la primera salida** de cada zona.

## Evento
- Primera barra e, en (b, b+500] de la misma sesión, cuyo **cierre** queda a ≥ k ticks fuera de la banda
  [lower, upper], con k ∈ {4, 8, 16}.
- Dirección = +1 si sale por arriba, −1 si sale por abajo.
- Se registra:
  - el lag (e − b);
  - las barras con cierre dentro de la banda antes de salir (consolidación);
  - para OFF: **ruptura** (sale por el lado opuesto al origen, atraviesa) o **rechazo** (sale por el lado de origen).
- Celda base de AVCL (p95, W10, k2, 50t, parámetros congelados), cache `edgelab-avcl-grid-mnq-k1..k4`. MNQ,
  sesiones aprobadas, RTH (la salida en RTH). Holdout no leído.

## Nulo: pseudo-zonas con la misma geometría
- Bloques sin zona (a más de 20 barras de una creación), 3 por zona real.
- A cada uno se le asigna la geometría de una zona real **del mismo tipo (AT/OFF) y la misma franja de 30 min**
  (borde inferior y superior relativos al close de creación).
- Misma regla de salida.

Pregunta: ¿la salida de una banda con anomalía de volumen se comporta distinto que la de una banda idéntica sin ella?

## Resultados (en la barra de salida e)
- `c_H = dir × (close[e+H] − close[e])` en ticks: continuación (+) o falla (−).
- `y_rg_H` en la salida = log(rango [e+1, e+H] / rango [e−H, e−1]).
- Colas de continuación (c_H ≥ 1R) y de falla (c_H ≤ −1R), con R = rango [e−H, e−1].

Estimador: β de real contra pseudo, con FE (contrato × franja × decil de volumen de la barra de salida, decil de int10,
decil de |retorno de 10 barras previo a la salida], para no confundir con el momentum de la ruptura). SE por sesión.

## Pruebas formales (9, Holm, bilaterales)
Para cada k ∈ {4, 8, 16}:
- media de c_10;
- media de c_50;
- `y_rg_10` en la salida.

## Descriptivos
- Colas de continuación y falla.
- AT contra OFF.
- Ruptura contra rechazo (OFF).
- Salida inmediata (lag ≤ 10) contra salida tras consolidar (≥ 5 cierres dentro).
- Dosis (anomaly_ratio), ancho, H200.
- Tasa de salida y lag.

## Justificación económica
Si la salida de una zona continúa más que la de una banda equivalente, hay una entrada direccional con información
conocida en el momento: entrar a favor de la salida, con el stop del otro lado de la banda.

## Cómo podría refutarse
c_H real ≈ c_H pseudo (MDE publicado): lo que se ve en el chart sería el momentum de cualquier ruptura de rango, no
algo propio de la zona.

## Registro
9 pruebas, familia `AVCL_EXIT`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
