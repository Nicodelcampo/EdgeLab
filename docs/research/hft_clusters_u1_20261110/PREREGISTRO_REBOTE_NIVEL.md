# REBOTE_NIVEL_SESION — ¿un nivel de la sesión rebota en su primer regreso, y más donde no hay zonas HFT?

Estado: PRE-REGISTRO (2026-11-10, antes de generar la tabla). Familia `REBOTE_NIVEL_SESION` (linaje `HFT_RUPTURA_OTROS`).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF2 (banco) +
EF3 (hipótesis previas). Idea de Nico (2026-11-10) a partir del control de los clusters (`ESTABILIDAD_CLUSTERS.md` §3): «rebote en
niveles sin zonas HFT, ni clusters ni individuales; "sin zonas" tiene dimensión espacial y temporal; sería un parámetro».

## 1. Espacio de eventos (enumerado antes de elegir)
Para un nivel de precio de la sesión: creación (el instante en que se fija), alejamiento, primer regreso, toques posteriores,
expiración, y el estado continuo (distancia al nivel). Se mide el **primer regreso tras alejarse X/2** (D0), por ser el evento del
que salió la pista (el control de los clusters es exactamente eso) y el de más N. Toques n-ésimos y estado continuo quedan para otra
familia.

## 2. Población (parámetros fijos, redondos, sin retornos)
- Nivel: cada 600 s desde el primer tick de la sesión, el último precio conocido; banda ± X/8 (ancho X/4). Vida 1.800 s (la de un
  cluster). Evento D0 (`hft_rebotes.eventos`). Generador: `edgelab/research/niveles_sesion.py` (test de causalidad por prefijo).
- Activos: NQ, ES, RTY, YM, GC (costo medido; X = fricción / 0,08). Ventana: **réplica abr → sep 2026**, que esta familia nunca
  usó (los niveles de DESC inspiraron la idea: no se usan para probarla).

## 3. El parámetro «sin zonas» (espacial × temporal), como rasgos para el banco
`dist_zona_600`, `dist_zona_1800`, `dist_zona_3600`: distancia (en X) a la zona HFT individual (Z_CERT) más cercana disponible en
los últimos 10, 30 o 60 min (99 = ninguna); `dist_cluster`: al cluster grande vivo más cercano (definición del E0-b del activo; GC
no tiene); `n_zonas_1x_1800`. Cortes fijos de distancia: < 0,5 X | 0,5–1 X | > 1 X (o ninguna). El banco explora todas las
combinaciones de ventana y distancia (y sus cruces con los 20 rasgos de llegada de `hft_ruptura`) en la mitad A: el valor del
parámetro no se elige a mano.

## 4. Análisis (banco, `docs/research/banco_eventos/specs/REBOTE_NIVEL_SESION.json`)
Desenlace `rompe` (+1 atraviesa, −1 rebota), dirección 0, nulo 0, umbral 0,08, k = 3, q = 0,10; estabilidad en 5 sub-bloques en
cada prueba (regla 08/11). **Hipótesis previas** (de DESC, probadas en toda la tabla):
1. sin zona individual a ≤ 1 X en 30 min (`dist_zona_1800` = estrato > 1 X) → rebote (−);
2. sin zona en 60 min (`dist_zona_3600` > 1 X) → rebote (−);
3. sin cluster vivo a ≤ 1 X (`dist_cluster` > 1 X) → rebote (−).
Lectura de mecanismo: cada celda informa `vs_resto` (¿el «sin zonas» rebota MÁS que el resto, o todo nivel rebota igual?).

## 5. Justificación económica
La liquidez pasiva que dejó el primer paso por un nivel lo defiende en el regreso (reversión de corto plazo); donde hubo ejecución
agresiva grande (zonas HFT) esa liquidez ya se consumió. Si es así, el rebote es mayor lejos de zonas y menor cerca.

## 6. Cómo podría refutarse
Las previas no se nominan ni son estables y `vs_resto` ≈ 0: la distancia a las zonas no modula el rebote. O el rebote global es
< 0,08 en todos los estratos: no paga la fricción aunque exista.

## 7. Riesgos declarados
- Niveles cada 10 min se solapan: muchos eventos por sesión correlacionados (el bootstrap y la estabilidad son por sesión).
- El rebote del control en DESC estaba en el umbral (+0,07–0,10): lo operable exige concentrarlo (lente `cuerdas`).
- La misma ventana abr–sep la usa la confirmación de «no defiende»: el banco de esta familia corre ANTES de mirar esa tabla.
