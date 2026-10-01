# Resultado EMA20 pullback económica — 2026-10-01

## Decisión

**NO AVANZA esta configuración: 0/6 variantes pasan el screen exploratorio congelado.** Esto no demuestra que todas las EMA o todas las variantes sean inútiles, ni invita a rescatar salida/filtro mirando esta misma muestra.

Kaggle privado kernel136675763 v1 COMPLETE; DONE401,08s (~6,7min incluyendo transporte/arranque; runner376,44s). Detector, manifiesto y doce fuentes exactos. Fuente descargada MATCH. No cambio del censo al abrir resultados.

## Población y resultados

1min seleccionado target-free, salida fija30min. BASE878/975/984 operaciones simuladas completas en154/175/177 sesiones propias. Las2.837 intenciones conservan identidad; no son fills de mercado reales. SEP es subconjunto, no muestra independiente. No agrupar activos como2.837 observaciones independientes ni comparar USD como exposición igualada.

| Activo | Variante | Trades | Sesiones | Trades/sesión | Neto USD/trade | Estrés2ticks/leg USD/trade | Alpha emparejado U | Pares/Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| MNQ | BASE | 878 | 154 | 5.70 | +3.89 | +2.89 | -0.093 | 797/878 |
| MNQ | SEP | 791 | 154 | 5.14 | +4.36 | +3.36 | -0.182 | 718/791 |
| RTY | BASE | 975 | 175 | 5.57 | -2.14 | -12.14 | -0.255 | 873/975 |
| RTY | SEP | 871 | 175 | 4.98 | +7.17 | -2.83 | -0.287 | 777/871 |
| YM | BASE | 984 | 177 | 5.56 | -18.31 | -28.31 | -0.222 | 880/984 |
| YM | SEP | 889 | 177 | 5.02 | -11.76 | -21.76 | -0.350 | 791/889 |


USD por operación de UN contrato, con bidask exportado y costos asumidos: fee/side MNQ0,60/RTY2,25/YM2,40 USD, slippage base1tick/leg. Estrés2ticks/leg suma UN tick por lado respecto de base. Spread ya pagado. No son comisiones/slippage/fills verificados del usuario.

- **MNQ:** media positiva pequeña, pero IC de neto U cruza cero y los contrastes emparejados son negativos en media. Sin las mejores5operaciones BASE quedanUSD404,40, SEP574,80: G1 parcial PASS, no edge aprobado.154sesiones impiden studentized nativo (mínimo160), pero más sesiones no garantizan resultado favorable.
- **RTY:** SEP mejora media USD a+7,17, pero neto normalizado es−0,068U; diferencia de ponderación por volatilidad, no contradicción que ocultar. Quitando mejores5trades quedaUSD−1.062; concentración por contrato falla. Con1tick adicional de deslizamiento por lado quedaUSD−2,83/trade. No robusto.
- **YM:** neto negativo en ambas variantes. SEP tiene alpha emparejado−0,350U y studentized corregido12 [−0,710,−0,027], evidencia local de peor desempeño relativo, no edge positivo. No certificación de FWER de todo el proyecto.

## Controles y potencia

Se congeló y persistió el plan entero antes de replay: hasta5 momentos31–60min del ancla, misma sesión/contrato/dirección y Uratio0,5–2.3controles completos mínimo.12.745 enlaces de matching revisados; soporte entre88,98% y90,77% según variante. Controles reutilizados/solapados, no cartera ni cinco trades independientes por señal. Una media de contraste por señal, clusters de sesión. El neto cubre todos; alpha sólo soporte común: distintos denominadores explícitos.

Todos los alpha emparejados tienen media negativa; no hay evidencia de superioridad positiva de este retroceso. Algunos IC95 sin corregir de RTY/YM quedan negativos; no se venden como significancia global. Bonf12 y sensibilidad134 son del manifiesto;134 sólo escenario acotado, no N_eff histórico certificado.

| Variante | Neto U | IC95 percentil diagnóstico | Límite inferior corregido12 | Alpha U | IC95 alpha diagnóstico | G1 diagnóstico |
|---|---:|---|---:|---:|---|---|
| MNQ|BASE | +0.047 | [-0.212, +0.297] | -0.305 | -0.093 | [-0.304, +0.117] | PASS parcial |
| MNQ|SEP | +0.071 | [-0.182, +0.308] | -0.271 | -0.182 | [-0.431, +0.073] | PASS parcial |
| RTY|BASE | -0.165 | [-0.389, +0.064] | -0.464 | -0.255 | [-0.480, -0.033] | FAIL |
| RTY|SEP | -0.068 | [-0.294, +0.160] | -0.374 | -0.287 | [-0.510, -0.067] | FAIL |
| YM|BASE | -0.231 | [-0.470, +0.007] | -0.549 | -0.222 | [-0.443, -0.007] | FAIL |
| YM|SEP | -0.205 | [-0.466, +0.057] | -0.550 | -0.350 | [-0.593, -0.117] | FAIL |


Los studentized completos están en results.json. RTY/YM superan160sesiones, pero ni eso ni un IC bastan para aprobarG2. NativePBO/DSR/WFselección/neighbors/budgetcompleto no realizados. No promoción.

## Variación temporal, sin elegir meses ganadores

| Mes | MNQ BASE USD/trade | RTY BASE USD/trade | YM BASE USD/trade |
|---|---:|---:|---:|
| 2025-10 | +8.94 | +24.63 | +13.76 |
| 2025-11 | +14.33 | +59.25 | +29.39 |
| 2025-12 | -10.54 | -17.80 | -1.68 |
| 2026-01 | +9.92 | -2.34 | -64.14 |
| 2026-02 | +12.10 | +75.06 | -3.17 |
| 2026-03 | +3.28 | +1.86 | -32.92 |
| 2026-04 | -2.97 | -23.05 | -12.59 |
| 2026-05 | -13.31 | -53.33 | -40.98 |
| 2026-06 | +11.45 | -76.95 | -46.36 |


Calendarios propios y cantidades por mes en monthly.csv. Los resultados no son estables entre meses. Es desarrollo previamente expuesto, NO réplica ciega/OOS. Holdout20260701+ intacto. No mirar julio+ para rescatar.

## QA y límites

-17tests sintéticos dirigidosPASS, no fullsuite.36prefijos muestreados reproducen detector y candidatos.12custodias/parquets, manifiesto ejecutado/hashcode y ledger MATCH.
-2.837signals COMPLETE; sin entradas perdidas, salidas desconocidas ni solapamientos de posiciones simuladas. Calipers/IDs/geometría previa reconciliados.
-Recuento/sumas/costos/ticks↔USD/U/meses/mejores5/alpha por vía aritmética independientePASS.10comparaciones de quotes contra raw real: entrada+salida de primeras5señales RTY20251007; primera quote válida exactaPASS. No audit raw independiente exhaustivo.
-MAE/MFE no medidos. Quoteage, reloj absoluto, as-of publicación, fees completas reales y fills no certificados. MaxDD de trayectoria simulada, no pérdida de cartera con controles. No stop/TP ni gestión nueva medida.
-Código nativo reutilizado primero: costs,holdout_guard,universo_estudio,cluster_estimand y replaycongelado. Código/acta/agregados públicos; fuentes/productor-catálogo/precios/ledgers y URLsfirma privados. No Lucid.

## Custodia

Manifest económico `56d3f991b1d72b803c911e0a5fa369a844048521a9087ae18628886954f7ae60`. Results `b3b970b9405c7955d8190086701881396a3cca9707f153eb2f3662db7cc66e04`. Preflight `3f56e5e88d5741c29eed00da2c0a49f2c89401078ef6b21cd91f0983b7aa65fd`. Notebook sourcehash792030e3...; source exact comprobado antes de leer resultados. Evidencia completa y scripts en carpeta ema_pullback_economic_20261001. Rama research/ema-pullback-economic-20261001, sin merge. Acta y MEDIDO en el mismo commit.

## Próximo paso

Cerrar este diseño de recuperación EMA20/30min como no habilitado. Si se plantea otra hipótesis estructural (otro evento, no barrer salidas/filtros para rescatar estas ganancias), nuevo manifiesto y presupuesto antes de nuevos outcomes. No abrir holdout ni operar estas medias.

Aporte al referente: aumentar frecuencia resolvió el problema de conteo, pero no produjo ventaja atribuible al retroceso; los controles emparejados evitan confundir tendencia general con edge del setup.
