# aVolClusterPOI — FASE 7: el residuo es chico, local y sin deriva

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_residual/residual_entry.py` (Kaggle, 44 s)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED`. Configuración fija: `p=0, L=−1, filtro ON`.

No propone mecanismo nuevo: mide **dónde** está el 85 % de error que deja el
mejor mecanismo conocido. Tres cortes mutuamente excluyentes.

## Corte 1 — magnitud: el error es CHICO

Difieren en promedio **3,5 celdas de 93,6** por bloque (3,8 %).

| celdas que difieren | 0 | 1 | 2 | 3 | 4–10 | 11+ |
|---|---:|---:|---:|---:|---:|---:|
| bloques | 3.436 | 4.680 | 4.277 | 3.063 | 5.749 | 1.302 |

El 41 % de los bloques falla por **dos celdas o menos**. No es un perfil
distinto: es el mismo perfil con un borde mal puesto.

## Corte 2 — ubicación en precio: EN EL MEDIO

Celdas que difieren en los extremos del rango: **3.839**. En el medio: **76.003**.
Sólo 482 bloques fallan exclusivamente en los extremos.

El filtro `Low/High` muerde en los extremos por construcción. **El residuo no
está ahí.** Lo que queda es asignación, no filtro — y no es un lag constante,
porque un lag constante ya está aplicado.

## Corte 3 — ubicación en la sesión: PLANO

Celdas que difieren por decil de posición del bloque en la sesión: 4,73 · 4,71 ·
4,16 · 3,99 · 3,86 · 3,84 · 4,00 · 3,91 · 4,14 · 4,52.

Sin tendencia. **No hay deriva acumulativa**: la partición no se separa y se
queda separada, se desajusta y se recupera. El defecto es **local a cada barra**.

## Firma resultante y qué la produce

Chico + local + sin deriva + de asignación. Una sola cosa produce eso: la
frontera de barra cae en un lugar levemente distinto en cada barra y se
autocorrige. Y hay un candidato medido: **el 51 % de los ticks de NQ comparte
timestamp con el anterior**. NT8 no corta una barra en el medio de un grupo de
ticks simultáneos; el parquet, contado como 120 filas consecutivas, sí lo corta.

Es el mismo hecho del feed que ya había roto a `HFTZonesNQImpulseV2_5` por otra
vía (`_timingZeroFraction` = 0,51 contra un umbral de 0,50). Aparece por segunda
vez, en otro indicador y con otra consecuencia.

FASE 8 lo prueba: cortes de 120 ticks ajustados al grupo de timestamp.

## Cómo podría refutarse

Si el corte por grupo de timestamp no mueve el 15,27 %, la firma tiene otra
causa y la conclusión pasa a ser que la paridad no se alcanza desde el parquet:
haría falta que NT8 exporte su perfil por barra. Eso es un pedido concreto de
instrumentación, no otra hipótesis.
