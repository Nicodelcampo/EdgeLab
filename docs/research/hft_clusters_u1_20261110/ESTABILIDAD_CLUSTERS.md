# Clusters HFT grandes — estabilidad en sub-bloques (regla de evidencia del 08/11)

Estado: RESULTADO (2026-11-10). Pedido de Nico: «efecto chico es lo esperable; a falta de potencia, estabilidad y sub-bloques».
Regla: `docs/DECISIONES_20261108.md` (unidad = sesión; 5 sub-bloques cronológicos, estable = ≥ 4/5 positivos con probabilidad de
azar < 10 %; nulo de inversión de signo por sesión que repite TODA la selección). Código: `banco_eventos.estabilidad`,
`real_menos_control`, `nulo_de_seleccion` (tests en `tests/research/test_banco_eventos.py`). Datos: `HFTC_ruptura.csv` (NQ, ES) y
`HFTC_ruptura_otros.csv` (RTY, YM, 6E, 6B), DESC. Cifras: `ESTABILIDAD_CLUSTERS.json`. Carrera ±X: +1 = atraviesa.

## 1. El cluster grande no defiende el nivel (real − control, por sesión) — **ESTABLE, también en activos independientes**
| Muestra | Sesiones | Real − control | Bloques + | p azar (media) | Por bloque |
|---|---|---|---|---|---|
| NQ + ES (donde se vio) | 199 | +0,107 | 4/5 | 0,032 | +0,15 +0,27 +0,14 +0,03 −0,06 |
| **RTY + YM + 6E + 6B (independientes)** | 158 | **+0,099** | **4/5** | **0,088** | +0,19 +0,01 −0,01 +0,01 +0,30 |
| los seis | 357 | +0,103 | 4/5 | 0,015 | +0,25 +0,18 +0,04 −0,00 +0,06 |
Por activo: NQ +0,151 (4/5, p 0,005); YM +0,108 (5/5, p 0,17); RTY +0,076 (3/5, p 0,23); **ES −0,010 (no)**.
Pasa la regla en los datos independientes (≥ 4/5 y p < 0,10). No hubo selección entre muchas candidatas en esos activos (el
control era el diagnóstico pre-registrado).

## 2. El retroceso contra la sesión atraviesa — **se debilita**
| Muestra | n | Ruptura | Bloques + | p azar | Nulo con selección |
|---|---|---|---|---|---|
| NQ + ES | 1.067 | +0,082 | 5/5 | 0,002 | **p 0,24** (elegida entre 68 celdas) |
| RTY + YM + 6E + 6B | 176 | +0,011 | 1/5 | 0,46 | — (hipótesis previa) |
Estable donde se eligió, pero al repetir la selección la probabilidad de azar es 0,24, y en activos independientes no aparece.

## 3. La cuerda que asoma: un nivel cualquiera de la sesión rebota; el cluster grande lo anula
El control (pseudo-nivel de la sesión, primer regreso tras alejarse X/2, sin un cluster grande vivo cerca) **rebota**: NQ +0,078
(4/5, p 0,023), RTY +0,100 (3/5, p 0,087), YM +0,073 (4/5, p 0,11); ES −0,072. El efecto del cluster (§1) es justamente que ese
rebote no ocurre. Hipótesis de mecanismo: el regreso a un nivel visitado 20–40 min antes revierte (liquidez pasiva en la zona ya
operada), salvo que ahí se haya ejecutado tamaño grande (cluster HFT): esa liquidez ya se consumió y el precio sigue.

## Qué sigue (como guía)
1. Canasta / confirmación congelada de «real − control > 0» (NQ, RTY, YM; ES aparte porque va en contra) en la réplica abr–sep o
   en el holdout en modo exploratorio, con esta probabilidad de azar declarada (0,088 independiente). Decisión de Nico.
2. Pre-registrar el rebote en niveles sin cluster como familia propia (`REBOTE_NIVEL_SESION`): es del orden del umbral económico
   (+0,07–0,10 en bruto), así que vale sólo si se concentra en alguna condición (lente `cuerdas`).
3. ES va al revés en los dos efectos: indagar por qué (microestructura distinta, clusters más chicos en X).
4. El retroceso queda como pista débil: no gastar réplica en él solo.
