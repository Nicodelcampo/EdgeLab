# Familia TBZ: franjas de baja permanencia (registro, 2026-09-24)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Estado:** REGISTRADA (OK de Nico, 24/09: "registrala unificada pero diferenciando sus variantes"). Etapa E1 congelada abajo **antes de medir**.
**Investigación de base:** `docs/research/RESEARCH_TRANSICION_BORDE_ZONA_EXPANSION_20260924.md` (mecanismos M1–M7, población, nulos; addendum §13).
**Ledger propio:** `artifacts/hippocampus/tbz_20260924.jsonl`. No hereda resultados, poblaciones, costos ni presupuesto de BigTrap2, HP-007, 6E-REGIMES, absorción L2 ni LUX-IMB.

## El objeto común

Una **franja de precio con poca permanencia** (poco tiempo y poco volumen negociado en ese nivel) que el mercado primero **respeta** desde afuera y después **atraviesa**. La pregunta de la familia (§5.4 del research) es qué anticipa el paso de "rechazar" a "atravesar".

## Variantes (se construyen distinto y **no se transportan resultados entre ellas**)

| Variante | Qué es | Construcción | Parámetros E1 (grilla declarada) | En el visor |
|---|---|---|---|---|
| **TBZ-EXP** | La franja que deja una **expansión rápida** A→B | Detector causal sobre velas de 25 ticks: movimiento neto ≥ k·σ_W con eficiencia ≥ e; termina cuando retrocede ≥ r del recorrido. A = inicio, B = extremo; disponible al cierre de la vela que confirma el fin | W ∈ {20, 60} velas; k ∈ {2,5; 4}; e = 0,6; r = 0,3; neto ≥ 4 ticks. σ_W = mediana causal de \|cierre_t − cierre_{t−W}\| en las 3.000 velas previas. **Por defecto en el visor: W = 20, k = 2,5** | Capa nueva "Franjas TBZ" |
| **TBZ-DWELL** | **Hueco de permanencia** dentro del rango recién negociado | Cada 5 min: volumen por precio en la ventana L (el volumen de cada vela repartido parejo entre su mínimo y su máximo). Hueco = tramo contiguo de ticks con volumen < q · mediana, estrictamente **interior** al rango, de ancho ≥ w_min | L ∈ {60, 240} min; q = 0,25; w_min = 4 ticks. **Por defecto en el visor: L = 60** | Capa nueva "Franjas TBZ" |
| **TBZ-HFTGAP** | **Corredor** entre zonas HFT (HP-006/HP-007) | `density_field.py`, preset `HP007_NO_TIME_DECAY` (el del visor), intervalos de baja densidad con ancho ≥ 16 ticks, sobre las zonas `HFTZonesUniversal` `SCALED_FUNNEL_V1` del bundle | Preset y ancho del visor; muestreo cada 30 min | Ya existe: botón "Corredores" |

Diferencias que importan:
- EXP es un **evento** que nace en un instante.
- DWELL y HFTGAP son **estados** que se recalculan en el tiempo.
- HFTGAP depende de un detector con paridad NT8 solo en NQ (en MES y ES: `PARITY_ABSTAIN`).
- DWELL sale directo de las velas, sin parámetros de otro instrumento.

## Población: espacio enumerado (regla del proyecto)

El mismo que el research §6: creación, aproximación, primer contacto, contacto n-ésimo, penetración, aceptación adentro, travesía, vencimiento, confluencia y **estado continuo**. **E1 solo toca la creación y el estado continuo (construcción y solapamiento), sin ningún precio posterior.**

**Cómo podría refutarse la población:** si las tres variantes no se solapan más que franjas al azar del mismo ancho, no son "tres miradas del mismo objeto" y la unificación se deshace. Cada variante sigue como familia propia.

## Etapa E1: target-free (congelada)

**Datos:** los bundles de 25 ticks pre-holdout del visor, MES y ES (ago-2025 a jun-2026). Son las mismas velas que ve Nico, construidas desde los ticks de `research-v2`.

**E1a, censo por variante:**
- franjas por sesión;
- ancho en ticks y en unidades de σ;
- duración de la formación (EXP);
- persistencia de los huecos entre muestras consecutivas (DWELL).

Por instrumento, sin mirar el precio posterior.

**E1b, solapamiento entre variantes** (la prueba de la unificación). En cada muestra de HFTGAP (cada 30 min) se calcula:
- X = ticks cubiertos por franjas EXP vigentes (disponibles, con edad ≤ 240 min);
- D = ticks de huecos DWELL (L = 60);
- G = ticks de corredores HFTGAP.

Se reportan:
- la cobertura de cada variante por las otras, por ejemplo \|X∩G\|/\|X\|;
- el Jaccard;
- todo contra un **nulo**: las mismas franjas desplazadas al azar (misma cantidad y ancho) dentro del rango negociado de las últimas 4 h, con 20 réplicas.

**Criterio (fijado ahora):** dos variantes miden **el mismo objeto** si su cobertura mutua supera al nulo con el cociente real/nulo ≥ 1,5 en los dos instrumentos. Son **objetos distintos** si el cociente es < 1,2. Entre 1,2 y 1,5 queda **parcial**.

**Salidas para el visor** (target-free, dibujan construcción, no desenlaces):
- `viewer/nt8_bridge/bundles/tbz/<bundle_id>.json` con las franjas EXP (desde que están disponibles, extendidas 240 min o hasta el fin de sesión) y los huecos DWELL por muestra de 5 min.
- Nada en esos archivos depende de lo que hizo el precio después.

## Particiones (declaradas ahora, para E1b-respuesta y E2)

Regla de `PARTICIONES_Y_POTENCIA_L2_20260924.md` (3/4 y 1/4):

| Partición | Rol | Sesiones |
|---|---|---|
| `P-TBZ-EXP` | EXPLORATION | MES y ES, sesiones hasta el 31/03/2026 (ids `MES:<fecha>`, `ES:<fecha>`) |
| `P-TBZ-CONF` | CONFIRMATION_RESERVED | MES y ES, 01/04/2026–30/06/2026 |

MES y ES son el mismo subyacente: **no suman como sesiones independientes**. La potencia se calcula por fecha.

## Holdout

- Días excluidos de cualquier confirmación de esta familia, porque de ahí salieron las observaciones de Nico: **24/09/2026** (MES/ES).
- La decisión sobre usar el resto del holdout como confirmación ciega sigue abierta (P-86).

## Enmiendas del mismo día (antes de ver cualquier resultado de E1b)

1. **Escala por defecto del visor para EXP:** pasa de W20 · k2,5 a **W20 · k4**. W20 · k2,5 produce ~340 franjas por día en MES (censo target-free del primer bundle) y tapa el gráfico. Es una decisión de **visualización**: la medición E1 sigue usando la grilla completa.
2. **HFTGAP, hallazgo de construcción:** con el preset por defecto (`HP007_NO_TIME_DECAY`) el campo acumula **todas las zonas desde el inicio del bundle mensual** y queda saturado casi en todo el rango. Un corredor aparece solo donde no hubo ninguna zona en todo el mes, y eso no es lo mismo que los huecos locales que Nico ve en NT8. E1b mide los dos presets: `HP007_NO_TIME_DECAY` (el declarado) y `HP007_CALIBRATED` (12 h de vida media) como sensibilidad, publicados ambos.
3. **Desgaste por toque calibrable** (pedido de Nico): `density_field` acepta `wear_alpha` y `wear_exp` (peso = (1 + a·toques)^−b; de fábrica 0,5 y 0,6), con la misma implementación en Python y JS (test de paridad nuevo). En el visor son dos controles. **La calibración a ojo es de visualización** y no entra a E1. Si se congela un valor para medir, se registra como parámetro antes de usarlo.
4. **Bundles MES con parámetros literales de NQ** (`tools/build_mes_nqlit_bundles.py`, ids `*_NQLIT`), como cuando Nico aplica HFTZonesNQPureV4 sobre MES en NT8:
   - ~63 mil zonas por mes (contra ~8,5 mil del perfil escalado);
   - cada zona trae sus **toques causales** (entrada de una vela de 25 ticks al rango, después de estar disponible; hasta 40);
   - sin estos toques el desgaste no tiene efecto, porque los bundles existentes no los traen;
   - paridad NT8 en MES: `PARITY_ABSTAIN`.
