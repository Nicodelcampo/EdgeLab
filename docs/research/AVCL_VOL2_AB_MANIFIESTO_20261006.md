# AVCL-VOL-2 (A + B) — manifiesto — 2026-10-06

Aprobado por Nico en el chat del 2026-10-06 ("armá el manifiesto de A y B y correlo en kaggle").
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Target-free respecto de la dirección: mide información de volatilidad y rango, no P&L.

## Alcance (corrección de Nico)
Esto prueba **sólo** si la creación de zona anticipa expansión **más allá del pico de volumen**. **No** evalúa la
función de soporte/resistencia de las zonas, que es otra hipótesis, no medida, y queda pendiente con su propio
protocolo. Un resultado nulo acá no dice nada sobre soporte/resistencia.

## Datos e indicador
- MNQ con paridad validada, 2025-07-01 → 2026-09-30, mismas sesiones aprobadas que AVCL-VOL-1. Holdout no leído.
- aVolClusterPOI con los mismos parámetros congelados que AVCL-VOL-1, barras de 50t y footprint NT8.
- Etapa 1, un kernel por contrato, cachea por contrato:
  - barras (OHLC, volumen, inicio/fin);
  - bloques del detector;
  - zonas con todos sus campos: score, threshold, toques, MFE/MAE, para reutilizar en análisis posteriores,
    incluido el de soporte/resistencia.

## Covariables de intensidad (hipótesis rival Hawkes)
Medidas en el bloque `b`, sólo con información hasta `b`:
- `int10` y `int50`: segundos que tardaron las últimas 10 y 50 barras de 50t. Es la intensidad de llegada.
- `vol20`: vigintil del volumen del bloque, dentro de contrato.
- `vpk`: decil del volumen máximo de una barra entre las últimas 10.
- Estrato base S0, igual que en VOL-1: contrato × franja de 30 min × decil de volumen del bloque × decil de RV previa.

## A — ¿la zona agrega información sobre el pico de volumen? (formal, Holm 8)
Estimador: β de `y ~ evento + FE(S0) + FE(decil int10) + FE(decil int50) + FE(vol20) + FE(vpk)`.
- Los efectos fijos se absorben por proyecciones alternadas.
- Error estándar robusto clusterizado por sesión.
- p unilateral (β > 0), con z normal.
- Controles a más de 2H barras de cualquier creación, como en VOL-1.

Dos contrastes:
- **A1:** controles = todos los bloques sin zona.
- **A2, "volumen alto sin zona":** controles = bloques sin zona con volumen ≥ percentil 95 de su contrato × franja.
  Es el criterio de anomalía del propio detector sin la geometría del cluster.

Pruebas: {AT, OFF} × {y_rg, y_rv} × H10 × {A1, A2} = **8**, con Holm.
H50 es descriptivo. Definición de `y`: idéntica a VOL-1.

**Lectura pre-registrada:**
- Si AT·y_rg sobrevive Holm en A1 **y** en A2 → la zona agrega información de expansión más allá del volumen.
- Si no sobrevive → la expansión medida en VOL-1 se atribuye al pico de volumen o la intensidad. **Alcance:** sólo
  este estimando. No toca soporte/resistencia.

## B — curva de respuesta (descriptivo, sin regla de decisión)
- Para h = 1…200 barras: `r_h = log(rango_ticks(barra b+h) + 1) − media log(rango+1)` de las barras b−19…b.
- Efecto Δ(h) con el mismo estimador A1 (todos los h a la vez), con IC robusto por sesión.
- Curvas separadas para AT, OFF y "volumen alto sin zona" (este último contra los controles comunes).
- Se reportan:
  - el pico;
  - la vida media, con dos estimadores: el primer h donde el efecto cae a la mitad del pico, y el ajuste exponencial;
  - el exceso acumulado de rango en ticks.
- Sirve para fijar cuánto debería durar una operación que use este sello.

## Justificación económica
Si el sello sólo reproduce el pico de volumen, conviene operar con el volumen directo, que es más barato y sin
indicador. Si agrega información, la zona tiene valor propio como filtro de régimen de corto plazo.

## Cómo podría refutarse
- A1/A2 sin efecto en AT·y_rg (Holm).
- Una curva B indistinguible entre zona y "volumen alto sin zona".

## Registro
8 pruebas en `docs/research/avcl_vol1_20261005/trial_registry.jsonl`, familia `AVCL_VOL_CREATION_VOL`.
Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
