# Momentum frecuente — seis celdas económicas de desarrollo

## Veredicto
**0/6 pasan el screen conjunto netU+alphaU, 0/6 pasan G1 diagnóstico. G2 formal BLOQUEADO: 54 <160 sesiones. Sin autorización de promoción.**

Acortar la reserva/salida de120 a60/30min produce más operaciones simuladas: mediana4–5 frente a8/día. No estableció una ventaja neta estable en esta población expuesta. RTY60 conserva una pista direccional, no un sistema validado.

## Procedencia y congelamiento
El manifiesto fue publicado en Notion antes de ejecutar/abrir nuevos retornos: https://app.notion.com/p/777b3431270544eaae249f433be9dcd3 . Kaggle privado `nicolasbuttaro/edgelab-mom-short-20261001` v1, kernel136603068, COMPLETE. Fuente descargada mediante notebook_info idéntica byte por byte al transporte enviado; privada y versión verificadas. Preflight leído primero: runner+manifiesto+6 parquets coinciden; `outcomes_opened_at_preflight=false`. El transporte guarda inputs bajo /tmp, no en la salida pública. Corrida financiera160,964s según log; no certificación del reloj absoluto.

Manifiesto SHA-256: `551f95252ab91507931ef1a26910824e74a14b99e853caa2e6a62774e952d417`.
Runner SHA-256: `4f46ecbe6426fb027d6db8bdfc5f635f28a5f362c19cff6f56a0456e02f9cbb8`.
Resultados privados completos SHA-256: `ab0a3b50c1978a71b001742ce7037882ca90a12585553a4f7ca07b276ad354fd`.

Dos intentos de lanzamiento fueron rechazados por el identificador sin propietario; no arrancaron kernels ni cambiaron código. Se corrigió a owner/slug y se creó v1. Los avisos de mistune/nbconvert tras DONE corresponden a conversión HTML, no error del análisis.

## Herramientas EdgeLab leídas y reutilizadas
Base nativa foundation/f0b-compatibility-probe@391314907dec889599493c4a38282171d94a2f25: `PROJECT_INDEX`, `CURRENT`, `edge_validation_contract`, `holdout_guard`, `universo_estudio`, `costs`, `cluster_estimand`, `g2_ratio`. No nueva infraestructura paralela de bootstrap/costos. La ejecución usa guardas nativas, costo explícito y estimando ratio agregado por sesión. `g2_ratio` fue leído/probado, no se corrió un nuevo walk-forward/PBO/DSR ni se finge que pasaron. Allowlist de promoción vacía, intacta.

Detector y productor exactos del censo target-free: hashes `ccd2b9ba…` y `0ecfb04c…`. Seis parquets de ticks+bid/ask, contratos12-25 y03-26 de RTY/MNQ/YM. Misma lista común de54 fechas20251007–20251231 ya examinadas; no todos los días calendario son elegibles. No L2, no fechas nuevas, no holdout, ni supuesto OOS ciego. Los contratos tienen exposiciones muy desiguales y también representan períodos distintos; la diferencia entre ellos NO identifica causalmente un efecto de rollover.

## Diseño congelado
- Seis celdas: RTY/MNQ/YM × salida60/30min; barras5min, ROC60min, umbral1×SMA TrueRange20 anterior,600 barras de calentamiento.
- Inicio10:00ET; última señal16:00−H−15min; reserva H+60s con siguiente señal estrictamente posterior. Mismo código de eventos que el censo anterior.
- Entrada primera cotización válida estrictamente posterior a señal+250ms, máximo30s. Salida primera válida desde entrada real+H, antes16ET. Bid/ask ya cobra el spread; no se suma dos veces.
- Comisión RTY USD2,25/pata y MNQ USD0,60/pata SUPUESTAS. YM USD2,40/pata del módulo nativo, tarifa histórica NO confirmada para Nico; diferencia frente a USD2,25 anterior declarada antes de abrir. Tick values RTY/YM USD5; MNQ USD0,50. Slippage1,2,3ticks por pata. Son markouts cotizados con fricción supuesta, NO fills reales ni G3.
- Dos primarias por celda: media netU/trade y alphaU direccional contra dirección opuesta en los mismos instantes; este contraste no sustituye control temporal emparejado independiente.
- U normaliza por rango previo de cada señal: media USD/trade y media U/trade son estimandos diferentes, no conversiones de una misma media.
- Bootstrap estacionario nativo, ratio sumPnL/sumTrades, todas54sesiones incluidas las de cero,50.000réplicas por primaria, seed20261001 con offsets fijos, bloque PPW automático. Límite inferior unilateral percentil.05/12; sensibilidad.05/120, presupuesto histórico total desconocido. No max-T ni certificación FWER de todo EdgeLab. G2 bootstrap-t nativo rechaza54<160; no reducir umbral.
- G1: ≥100trades, media neta en ticks positiva, total positivo quitando5mejoresTRADES, ningún contrato >80% del neto positivo. Cuando total≤0 no se interpreta el share como ganancia.

## Resultados
|Activo|Salida min|Trades simulados|Mediana/día|Neto USD/trade|Neto U/trade|Límite inferior netU Bonf12|G1 / screen|
|---|---:|---:|---:|---:|---:|---:|---|
|RTY|60|243|4.5|+69.20|+0.3353|-0.1048|FAIL / FAIL|
|RTY|30|440|8|+12.47|-0.0010|-0.1619|FAIL / FAIL|
|MNQ|60|238|4|-9.59|-0.0642|-0.4803|FAIL / FAIL|
|MNQ|30|428|8|-2.66|-0.0631|-0.2477|FAIL / FAIL|
|YM|60|245|5|-27.13|-0.0937|-0.5364|FAIL / FAIL|
|YM|30|438|8|-1.67|-0.0180|-0.2266|FAIL / FAIL|

**RTY60:** +USD69,20/trade, +0,3353U, pero límite netU corregido−0,1048U. Alpha+0,4445U, límite local corregido+0,0065U: sólo esa primaria supera el screen local; no cumple la prueba conjunta. La sensibilidad budget120 también bloquea la celda. Quitando cinco mejores operaciones queda positivo (+7,15ticks/trade restante). El contrato12-25 aporta112,9% del neto:03-26 lo reduce; G1 concentración FAIL.

**RTY30:** +USD12,47/trade pero media normalizada−0,0010U. No es una contradicción: normalización por rango variable cambia los pesos. Quitando cinco mejoresTRADES, total−16,5ticks; pierde robustez. No seleccionar la media más favorable después de ver.

**MNQ y YM:** media neta negativa en ambas salidas. Tampoco pasan la primaria direccional corregida. Todas las seis medias netU resultan negativas bajo costos adversos salvoRTY60 (+0,2807U), que sigue sin superar los gates.

## Diferencias por contrato
|Perfil|Contrato|n|Neto USD/trade|Neto U/trade|
|---|---|---:|---:|---:|
|RTY 60min|RTY 03-26|31|-69.82|-0.4067|
|RTY 60min|RTY 12-25|212|+89.53|+0.4438|
|RTY 30min|RTY 03-26|57|-44.94|-0.2561|
|RTY 30min|RTY 12-25|383|+21.01|+0.0369|
|MNQ 60min|MNQ 03-26|30|-37.83|-0.4593|
|MNQ 60min|MNQ 12-25|208|-5.52|-0.0073|
|MNQ 30min|MNQ 03-26|49|-15.31|-0.2779|
|MNQ 30min|MNQ 12-25|379|-1.02|-0.0353|
|YM 60min|YM 03-26|29|-142.39|-0.4962|
|YM 60min|YM 12-25|216|-11.65|-0.0397|
|YM 30min|YM 03-26|54|-40.73|-0.2135|
|YM 30min|YM 12-25|384|+3.82|+0.0095|

La muestra03-26 pierde en los seis perfiles;12-25 es mayor (208–384trades frente a29–57). No llamar réplica independiente a este subgrupo ya expuesto, ni utilizarlo como un holdout fresco. El filtro de concentración se aplicó sin acomodarlo a la distribución del calendario.

## QA y reconciliación
48 tests dirigidos, no suite completa. Primer intento47pasaron/1falló porque faltaba el log histórico Gaps2 en la copia mínima; se copió el fixture original de foundation y los48pasaron, sin cambiar lógica. Seis tests nuevos de replay: batch vacío, latencia estricta, deadline, salida desconocida, short, cotización inválida y costos explícitos.

36 comprobaciones de prefijo de indicadores/eventos pasaron. Los seis conteos coinciden con el censo previo: RTY243/440, MNQ238/428, YM245/438. En cada celda todos los intentos tienen entrada y salida; cero unknown exits, cero solapamientos registrados. No se hizo descarte selectivo por demora de salida.

Auditoría separada por lectura de JSONL: identidad única dentro de perfil, conteos/contratos/fechas, latencia y reserva registradas, aritmética bid/ask long/short, comisiones/slippage, USD yU, agregación y remoción de mejores5TRADES. **No es un segundo replay independiente del raw ni certificación de edad de cotización/reloj/fills.** Las estrategias se solapan entre sí; no sumar sus trades o PnL como un portafolio/una población única.

## MEDIDO / NO MEDIDO y próximo paso
MEDIDO: frecuencia y markouts bid/ask con fricción declarada, diagnóstico G1, incertidumbre exploratoria por sesión y presupuesto explícito, estabilidad descriptiva por contrato.
NO MEDIDO: ventaja confirmada fuera de muestra, G2 formal, fees reales, fills/quoteage/reloj absoluto/NT8 parity, portfolio, nuevos stops/filtros, potencia formal para promoción. Holdout general julio–diciembre2026 cerrado; enmiendas ES/NQ/L2 no abren RTY/MNQ/YM.

No seguir bajando umbral o buscando horarios para rescatar estas seis celdas sobre los mismos datos. RTY60 puede conservarse como hipótesis de investigación porque el contraste direccional da una pista, pero necesita un protocolo de nueva población todavía no expuesta, suficiente número de sesiones independientes y tarifas del usuario antes de decidir réplica. MNQ/YM de esta familia se archivan como resultados negativos en esta población; no invalida todos los momentum posibles.

Aporte al referente: mayor frecuencia conseguida sin alterar el umbral, pero sin nuevo edge validado; el problema pendiente en RTY es estabilidad y evidencia independiente, no cantidad de operaciones por sí sola.
