# aVolClusterPOI — FASE 5: NT8 pierde volumen, de forma sistemática

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_conserv/conserv_entry.py` (Kaggle, 35 s)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED`.

## Por qué este test

Cualquier diferencia de **partición** se cancela al sumar: si NT8 y el parquet
ven los mismos ticks y sólo los agrupan distinto, los totales de sesión tienen
que coincidir. Si no coinciden, los conjuntos de ticks son distintos. Es la
bifurcación que decide si la paridad es alcanzable desde el parquet.

Para cada sesión: NT8 cubre `B` bloques ⇒ `10·B` barras ⇒ `1200·B` ticks desde
el primer tick de la sesión. Se compara ese total contra el volumen de los
primeros `1200·B` ticks de la sesión en el parquet.

## Resultado

| | |
|---|---|
| sesiones comparadas | 51 |
| sesiones con total exacto | **0** |
| ratio NT8/parquet, mediana | **0,996009** |
| ratio p05 – p95 | 0,993697 – 0,997224 |
| volumen NT8 total | 29.219.487 |
| volumen parquet total | 29.340.317 |
| déficit | **120.830 contratos (0,41 %)** |

**El signo es negativo en las 51 sesiones.** No es ruido y no es un desajuste de
ventana: es una **pérdida sistemática**. Un conjunto de ticks realmente distinto
daría desvíos de signo variable; una pérdida constante apunta a un lugar del
código donde el volumen se descarta.

## Consecuencia inmediata: se reabre el filtro Low/High

La FASE 3 lo había refutado, pero **bajo un supuesto que este resultado tumba**:
allí el rango `[Low[0], High[0]]` se derivaba de los mismos ticks de la barra, y
por construcción los contiene a todos, así que descartaba cero. Si el perfil de
NT8 se acumula **desfasado** respecto de la barra que lo cierra, el filtro sí
muerde y sí pierde volumen. La refutación de la FASE 3 vale sólo dentro de su
supuesto, y el supuesto se cayó acá.

Esto es la regla de alcance preciso de las muertes aplicada en la dirección
incómoda: hubo que reabrir una hipótesis propia ya declarada muerta.

## Cómo podría refutarse

Si el déficit fuera un artefacto del recorte `1200·B` (por ejemplo, sesiones
donde NT8 arranca a contar más tarde), las sesiones con `ticks_available` muy
por encima de `ticks_needed` deberían mostrar ratios distintos. No es el caso:
sesión 1 tiene 405.596 disponibles contra 405.600 necesarios y su ratio es
0,9971, dentro del mismo rango estrecho que todas las demás.
