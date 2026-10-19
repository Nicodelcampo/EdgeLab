# VTD-VOL-1 — VolTicksDef: expansión, cara a cara con aVolClusterPOI — manifiesto — 2026-10-06

Aprobado por Nico en el chat ("dale"). Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
**Familia propia (VTD)**: no se transportan resultados, poblaciones ni multiplicidad de aVolClusterPOI. Información de
rango/volatilidad, **no P&L**. Soporte/resistencia fuera de alcance.

## Indicador y paridad
`edgelab/bridge/indicators/volticksdef.py`, paridad NT8 PASS (MNQ 12-26 150t: 547/547 marcas, umbrales P² exactos).
Parámetros por defecto, congelados: AvgPeriod 200, percentil 99,75, reset por sesión, 30 muestras mínimas.
- **Evento:** barra marcada.
- **"Zona":** su rango [Low, High].
- **Dosis:** ratio / umbral.

## Población (enumeración previa)
Espacio de eventos de VTD: marca (creación), toques posteriores del rango, estado "zonas vivas". Se congela **sólo la
marca**, por comparabilidad con AVCL-VOL. Toques y estado quedan no medidos.

## Datos
MNQ 2025-07 → 2026-09, sesiones aprobadas (RESOLVER, re-export prioritario), RTH formal. Holdout no leído.
- bar_spec **150t** (el de uso de Nico) y **50t** (para comparar con AVCL, cuya paridad es a 50t).
- Controles: barras sin marca, a más de 2H barras de cualquier marca, submuestreadas 1 de cada 10 (para memoria),
  más todas las marcas.
- Estimador: el de AVCL-VOL-2 A1/A2 (FE S0 + int10 + int50 + vol20 + vpk, SE por sesión).
- Métricas: `y_rg`, `y_rv` y la cola sin signo, con definiciones idénticas a AVCL.

## Pruebas formales (8, Holm, bilaterales)
1–3. **150t:** `y_rg` H10 A1; `y_rg` H10 A2 (contra barras de volumen alto sin marca); cola sin signo H10 (|mov| ≥ 1R).
4–6. **50t:** lo mismo.
7. **Cara a cara 50t, AVCL sin VTD:** β `y_rg` H10 A1 de las creaciones AVCL (celda base) cuyo bloque no contiene
   ninguna marca VTD. Controles: bloques sin creación AVCL y sin marca VTD.
8. **Cara a cara 50t, VTD sin AVCL:** β `y_rg` H10 A1 de las marcas VTD que no caen en ningún bloque creador de AVCL.
   Controles: barras sin marca VTD y fuera de bloques AVCL.

Lectura pre-registrada:
- Si 7 > 0 y 8 ≈ 0 → **el nivel exacto de AVCL aporta y VTD no agrega nada propio**.
- Si 8 > 0 y 7 ≈ 0 → VTD captura lo mismo, y más simple.
- Si los dos > 0 → **son señales complementarias**.

## Descriptivos
- Dosis (quintiles de ratio/umbral).
- Ancho de la zona (angosta contra ancha).
- Solapamiento AVCL↔VTD.
- Colas con signo según la vela marcada (signo de close − open).
- ETH.

## Justificación económica
Si un indicador de una línea (volumen relativo de barra) da la misma información que el clustering por precio, el sello
es más barato de calcular, de explicar y de operar. Si no la da, queda medido cuánto vale ubicar el nivel.

## Cómo podría refutarse
VTD sin efecto en 1–6 (MDE publicado), o efecto que desaparece contra el volumen alto (A2).

## Registro
8 pruebas, familia `VTD_VOL`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
