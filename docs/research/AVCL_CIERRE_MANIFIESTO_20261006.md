# AVCL-CIERRE — 200t, grilla de sensibilidad, delta de la zona y asimetría de regreso — manifiesto — 2026-10-06

Pedido de Nico: "primero terminá con avolcluster". Cierra lo pendiente de la iteración 2 (H-g, H-h, H-j) y la hipótesis
descriptiva de DIST (regreso en alta anomalía).
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información, **no P&L**. Soporte/resistencia fuera de alcance.

## Datos y código
- MNQ 2025-07 → 2026-09, sesiones aprobadas (RESOLVER, re-export prioritario). Holdout no leído.
- Indicador: `run_full_fast`, idéntico a `run_full` y con paridad NT8 50t 934/934 y 200t 338/338
  (`AVCL_OPTIMIZACION_20261006.md`).
- Estimador: el de VOL-2 A1/A2 (FE S0 + int10 + int50 + vol20 + vpk, SE por sesión). Colas: el de DIST.

## Celdas (H-g y H-h)
Base = p95 · W10 · k2,0 · m2 · 50t (parámetros congelados de VOL-1). 13 celdas:
- base;
- percentil 90 / 98;
- W 5 / 20;
- multiplicador 1,5 / 3,0;
- min_cluster 4;
- **200t base**;
- esquinas p90·W5, p90·W20, p98·W5, p98·W20.

Por celda: AT y OFF, `y_rg` H10 con A1 y A2, más las colas de alejamiento y regreso (OFF H10, umbral 1R).
**Landscape descriptivo completo, sin elegir celda.** La pregunta es si el signo y el orden de magnitud se sostienen.

## Delta de la zona (H-j)
- Agresor por tick: compra si precio ≥ ask, venta si ≤ bid.
- Delta de la zona = Σ volumen comprador − vendedor de los ticks del bloque creador cuyo precio cae dentro de la banda de
  la zona. Asignación tick→barra por la partición de las barras (no por la regla de subserie NT8). Es un atributo de
  research, no de paridad.
- `dnorm` = delta / volumen de la banda ∈ [−1, 1]. Dirección del delta = signo(delta).
- `s_d = signo(delta) × (close[b+H] − close[b]) / R_H`: desplazamiento en el sentido del delta.

## Pruebas formales (8, Holm, bilaterales)
**Delta, celda base (4).** H10, RTH. Para AT y para OFF:
- media de `s_d` (β contra controles con pseudo-signo = signo del retorno de las 10 barras previas);
- cola 1[s_d ≥ 1] (β).

Esto pregunta si el delta le da dirección a la expansión. AT importa especialmente, porque no tiene lado.

**Asimetría de regreso (1).** OFF H10, quintil superior de `anomaly_ratio` (umbral = percentil 80 de los eventos de la
celda base): β(cola regreso) − β(cola alejamiento), con SE por bootstrap de sesiones (2.000).

**Réplica en 200t (3).**
- AT `y_rg` H10, A2;
- OFF cola de alejamiento H10;
- OFF cola de regreso H10.

¿Se replica la expansión bidireccional?

## Descriptivos
- Toda la grilla.
- Delta por quintil de |dnorm|.
- Delta contra lado en OFF: ¿el delta coincide con el lado?
- Las 8 pruebas formales repetidas en ETH.

## Justificación económica
- Si el delta orienta la expansión, el sello pasa de "se mueve" a "se mueve hacia": habilita entradas direccionales.
- Si la grilla es estable, el indicador no depende de una calibración frágil.
- Si 200t replica, el efecto existe en una escala más barata de operar.

## Cómo podría refutarse
- El delta no orienta (β ≈ 0 con MDE chico).
- La grilla cambia de signo entre celdas: la base sería frágil.
- 200t sin efecto.

## Registro
8 pruebas: familia `AVCL_CIERRE`. El landscape de la grilla se publica completo y no suma pruebas formales, porque no se
selecciona celda. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
