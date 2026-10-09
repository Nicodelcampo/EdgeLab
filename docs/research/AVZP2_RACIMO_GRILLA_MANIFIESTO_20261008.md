# AVZP2-RACIMO-GRILLA — sensibilidad de la definición de racimo — manifiesto — 2026-10-08

Pedido de Nico: "hacé pruebas con distintos parámetros que definan lo que se considera un racimo, siempre con
configuraciones que den potencia". Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
**Información, no P&L.** Escrito antes de ver la grilla.

## Qué se varía (sólo la definición de racimo; las zonas son las mismas)
- Mínimo de zonas ∈ {4, 5, 6, 8}.
- Ventana ∈ {250, 500, 1.000} velas.
- Altura máxima ∈ {20, 30, 45} ticks.

Son **36 celdas**. La detección de zonas y las barras de 25t son las de la configuración de Nico, igual que en el
estudio base. Cada celda corre sobre las mismas zonas.

## Potencia (regla fijada antes)
- Se evalúa una celda sólo si tiene **≥ 300 racimos en descubrimiento** (el base tuvo 454; con MDE de O5 ≈ 0,05).
- Las celdas con menos racimos se listan y no se prueban.

## Desenlaces y nulo
Los mismos del estudio base (O1, O2, O3b, O4, O5): desde t0, contra pseudo-racimos apareados por ocupación previa,
con la misma altura y posición, 5 por racimo, con FE y SE por sesión.

## Corrección
- **Primaria: O5 (compresión)** en todas las celdas evaluables, con **Holm** sobre esas celdas.
- **Secundarias: O1, O2 y O3b.** Holm sobre todas las celdas × 3 desenlaces. Una dirección, seguimiento o rebote que
  aparezca sólo en alguna celda tiene que sobrevivir esa corrección.
- **Confirmación** (09-26, 12-26), una sola vez, sólo en las celdas o desenlaces que pasen. La confirmación ya se miró
  una vez para O5 en la celda base (6 / 500 / 30), y eso queda declarado.

## Qué se publica
**Todas las celdas** (evaluables y no evaluables), con β, MDE, n y tasas. No se elige "la mejor": se informa el
paisaje.

## Cómo podría refutarse
- Que la compresión aparezca sólo en la celda base o en sus vecinas inmediatas: sería sensible a la definición, no
  una propiedad de los racimos.
- Que efectos direccionales aparezcan sólo en celdas sueltas sin sobrevivir a Holm.

## NO MEDIDO
- P&L.
- Otras escalas e instrumentos.
- Otros parámetros de detección de zonas (percentil, bloque, franja).
- Mínimos de zonas mayores que 8 o ventanas mayores que 1.000 (por falta de potencia esperada).
- Interacción con el lado de formación.

## Enmienda 1 (después de ver la grilla) — auditoría de O1 por magnitud de tendencia
O1 (salida a favor de la tendencia) pasó y confirmó en varias celdas de ventana grande. El nulo apareaba el **signo**
de la tendencia de 500 velas pero no su **magnitud**. Si los racimos reales se forman en tendencias más fuertes, la
continuación puede ser momentum genérico y no efecto del racimo (misma clase de artefacto que el "alejamiento
limpio" de AVZP2-REBOTE). Auditoría:
- se re-corre la grilla guardando la magnitud de la tendencia (500 velas) y el momentum de 100 velas, en alturas de
  la franja;
- O1 se re-estima agregando FE por decil de cada una;
- **regla:** O1 se considera efecto del racimo sólo si sobrevive a ese control en descubrimiento **y** en
  confirmación. Si no, se retracta como momentum.

## Enmienda 2 (2026-10-09, escrita antes de medir) — auditoría de O5 por volumen e intensidad previos
Pedido de Nico en la sala ("corré ese control"). Hash NORTH_STAR: el del encabezado. **Información, no P&L.**

**Motivo.** El pseudo-racimo se aparea por ocupación previa, franja horaria, altura y posición, pero **no por
actividad**. Un racimo se forma donde hubo zonas de volumen anómalo, así que los racimos reales pueden venir después de
más volumen y más intensidad que sus pseudo. La hipótesis rival (nota `AVCL_LITERATURA_SSRN_Y_PASOS_20261006.md`,
punto 2, y consulta al corpus SSRN del 09/10: autoexcitación tipo Hawkes) es que la compresión posterior (O5) sea el
decaimiento de esa actividad y no una propiedad del racimo. Lección del Brain que aplica: `LESSON-RH-BIGTRAP2-MAGNET`.

**Qué se agrega (todo con datos hasta t0, la vela de formación; nada posterior).** Por evento real y pseudo:
- `vol_occ`: log del volumen de las 500 velas hasta t0 (la misma ventana que la ocupación);
- `vol_100`: log del volumen de las 100 velas hasta t0;
- `dur_occ`, `dur_100`: log del tiempo que tardaron esas 500 y 100 velas. En velas de 25 ticks el tiempo por vela es
  la intensidad de llegada de operaciones. Los saltos entre sesiones no cuentan.

**Estimación.** La misma que el manifiesto (β real − pseudo, FE contrato×franja + decil de ocupación + tercil de
amplitud, SE por sesión), agregando **FE por decil de cada una de las cuatro variables**. Nada más cambia: mismas
celdas, mismas zonas, mismos pseudo (semilla crc32), misma regla de evaluable (≥ 300 racimos), mismos contratos.

**Regla (fijada acá).**
- O5 se considera efecto del racimo en una celda sólo si, con el control, mantiene el signo negativo y Holm ≤ 0,05
  sobre las celdas evaluables, en descubrimiento **y** en confirmación. Si no, se retracta en esa celda como
  decaimiento de actividad.
- Lectura global: «propiedad robusta» se sostiene si pasan ≥ 18 de 23 celdas en descubrimiento (la misma proporción
  que 21/23 ya publicada, redondeada hacia abajo); entre 6 y 17 es «parcial, depende de la definición»; ≤ 5 se
  retracta.
- Se publica además cuánto se achica β (controlado / sin control) por celda, y el MDE de cada celda.
- Secundario, sólo informativo: O1 con los controles de la enmienda 1 más estos cuatro.

**Chequeo de integridad previo a leer el control.** Sin el control, la corrida tiene que reproducir los β publicados
de O5 (mismos datos, mismo código, misma semilla). Si no reproduce, se frena y se busca la causa antes de mirar nada.

**Alcance y límites.**
- Los contratos de confirmación ya se miraron para O5. Esto es una auditoría que **sólo puede retractar o sostener**;
  no es una confirmación nueva ni reemplaza la réplica en otro instrumento.
- Controlar por deciles no es aparear: queda heterogeneidad dentro del decil. Si O5 sobrevive, el paso siguiente
  sigue siendo el control apareado en NQ/ES.
- Pruebas: 23 (O5 controlado, descubrimiento) + las que pasen en confirmación; O1 no suma pruebas formales.
- Procedencia: cada kernel lleva incrustado el commit del código y si el árbol estaba limpio.

**Cómo podría refutarse.** Que β de O5 pierda el signo o la significancia al agregar los controles; que sobreviva
sólo en las celdas donde reales y pseudo ya tenían actividad parecida.
