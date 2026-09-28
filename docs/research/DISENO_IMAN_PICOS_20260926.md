# Diseño: ¿las acumulaciones de picos consecutivos son imanes? (familia IPC) — BORRADOR 2026-09-26

**Estado:** diseño, sin medir. Se congela recién después de la tanda de validación de ES y con OK de Nico (regla STOP: mira retornos).
**Detector:** `tools/peaks_rule.py` (regla de Nico: cada pico no supera al anterior), modelos de ES y NQ ajustados con sus marcas y juicios ✓/✗. **La manera de detectar es un parámetro de la corrida**, no un dato fijo.

## Lo aprendido que condiciona el diseño
- **BigTrap2 como imán ya murió (F2.8, 13/08):** el efecto «imán» desapareció contra un control **sin zona** con la misma geometría. El control primario tiene que ser ese: el mismo nivel de precio y la misma distancia, pero sin zona.
- **TBZX (25–26/09):** el control tiene que emparejar a la vez la **actividad** y el **estado** del mercado (N-REVVOL). Si no, se mide «mercado movido», no la zona.
- **Regla de población:** hay que enumerar el espacio de eventos antes de congelar cuál se mide.

## Espacio de eventos (enumerado antes de elegir)
1. **creación** de la zona (se confirma el N-ésimo pico);
2. **alejamiento** (el precio se va a una distancia D);
3. **primera aproximación** (vuelve a una distancia d < D);
4. **primer toque** (llega al nivel);
5. **toque n-ésimo**;
6. **ruptura** (supera el último pico: fin de la serie según la regla);
7. **vencimiento** (no vuelve en T);
8. **estado continuo** (en cada vela: ¿hay una zona virgen a distancia x?).

**Propuesta:** «imán» = **probabilidad y velocidad de volver al nivel** después de haberse alejado. Evento primario: **alejamiento → ¿llega al nivel antes de alejarse otro tanto?** (1 → 2 → 4). Complemento en estado (8), que tiene más potencia estadística.

## Parámetros (todos se barren en grilla pre-registrada)
- **Detector:** modelo de ES / modelo de NQ; filtro por cantidad de picos (sí / no); escala.
- **Virginidad:** la zona no fue tocada desde su creación (sí / no, o cantidad de toques previos).
- **Distancia de alejamiento:** D en ATR (por ejemplo 2, 4, 8).
- **Volumen negociado antes de acercarse:** volumen desde el alejamiento hasta la aproximación, en múltiplos del volumen normal (terciles).
- **Otros candidatos:** edad de la zona, cantidad de picos, ancho de la banda, tipo (techo o piso), hora.

## Medida y controles
- **Medida:** acierto «llega al nivel antes de alejarse D más»; tiempo hasta llegar; los dos canales (direccional y no direccional).
- **Control primario (sin zona, misma geometría):** el mismo cálculo desde el mismo precio y la misma distancia, pero hacia un nivel **sin zona**, a la misma hora y en otra sesión, con la misma actividad y el mismo estado.
- **Control geométrico:** la ruina del jugador con las mismas convenciones.
- **Multiplicidad:** BH sobre la grilla y embudo como en EVX (información → economía → robustez); la reserva abr–jun queda para 1–3 configuraciones.

## Pendiente para congelar
1. Resultado de la tanda de ES (validar el 85 %).
2. Definir con Nico qué distancia significa «se alejó», y si «tocar» es llegar al último pico o a la banda completa.
3. Registrar la familia IPC (ledger propio) y escribir el manifiesto con el número efectivo de hipótesis.

## Decisiones (26/09)
- **Alejamiento relativo (Nico):** D = k × retroceso medio entre los picos de la zona, con k ∈ {2, 4, 8}. Se usa el retroceso y no el ancho de la banda porque muchas zonas son casi horizontales (ancho ≈ 0), mientras que el retroceso mide su tamaño real.
- **Tocar y TP (lo decidió Claude a pedido de Nico), en dos niveles:**
  - **primario: el último pico** (el más cercano y reciente: liquidez nueva, y el primer objetivo de un imán);
  - **secundario: el primer pico** (barrido completo de la zona: dice si atrae la zona entera o sólo el borde).
  - «Tocar» = el máximo (o mínimo) de la vela llega al nivel. Como TP operable: atravesarlo por 1 tick.
- **Validación del detector antes de la corrida:** ES, 69 % de precisión fuera de muestra (100 juicios, 26/09); NQ, filtro nuevo (70 % en muestra) todavía sin validar. La calidad de detección entra como parámetro (variante estricta: ≥ 12 picos).
