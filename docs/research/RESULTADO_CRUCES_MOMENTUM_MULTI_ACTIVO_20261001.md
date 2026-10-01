# Cruces menos restrictivos y profundización de momentum — protocolo congelado

Nueva pantalla exploratoria autorizada porNico en MNQ/YM/RTY. 18celdas de cruces EMA20/50 (1/5min ×BASE/SOFT200/ADX15), 6de momentum60min(5/15min). Sin L2, mismas54fechas comunesOct–Dic2025. Tres índices correlacionados, no réplicas de activos independientes.

**Antes de desenlaces:** manifest/código congelados, selftests y prefijos realesRTY PASS. Censo target-free se escribe para toda la población antes de computar cualquier salida. Umbrales mínimos100casos cruces /50momentum y20fechas activas; neto y alpha porATR con48endpoints y bootstrap20k porfecha. No tuning después de resultados.

Cambio respecto deEMA3v1: más eventos mediante cruce sin vetoEMA200, marcos1/5min y horizonte30min. SOFT200 admite precio hasta0,5ATR del lado contrario deEMA200; ADX15 alternativo. No atribuir aumento de señales exclusivamente al filtro: también cambian marco/horizonte/reserva. Los filtros no reprograman rechazos.

Momentum60min sigue el movimiento si≥ATR20simple anterior. Horizonte2h, costos y extracción porquote observada sincensura de salida1s. La nueva pantalla no es réplica exacta deRTYv3:54envez56fechas, gate de catálogo+historia consecutiva envezsesiónRTHcompleta, métricas normalizadas nuevas. Descomposiciónhora/intensidad/top5fechas sólo descriptiva; no se elige subgrupo ganador como confirmación.

Documentación: warmup heredado dice5minbarsforallTF; enmienda declarada enNotion ANTES de abrir resultados:600barras de cada temporalidad respectiva1/5/15, hasta7días anteriores porcontrato. No se cambió código ni frozenmanifestbytes.

Kernel privado Kaggle136595631, v1, edgelab-cross-momentum-multiasset-20261001. Fuente dev3913149; rama aislada research/cross-momentum-multiasset-20261001 hija deEMA3@41e2c25. Código020dabbe…, manifestf74a02d1…. API devolvió wrapperidéntico, privado. TransporteURLsfirmadas yraw no se publican. Sin Lucid/holdout/validaciónautomática ni IPC×L2deCodex tocado.

## Estado real y procedencia

**Kaggle v1 COMPLETE. 0/24 SCREEN_PASS;12 NO_SUPPORT,12 INCONCLUSIVE_SAMPLE.** Unos159s hasta resultados,167s hasta exportación, excluida cola. Antes de abrir resultados se verificó código ejecutado020dabbe… y manifestf74a02d1… exactos; wrapper devuelto porAPI idéntico y privado. Seisparquets y trescatálogos conhashes/custodiaPASS. ResultsSHA `0a6d793e176ae731574fca0cafed98d37a3aac8774a7f9ebf59f10af8320e467`.

1224 eventos BASE distintos de cuatro familias×tresactivos, todos con entrada/salida simuladas porquotes observadas;0 sinentrada,0salida desconocida. No fills reales ni cartera conjunta; las distintas familias/temporalidades pueden solaparse entre sí y los filtros reutilizan los eventos BASE. Lagmáximo entrada14.252s y salida12.928s, incluido.

Profiling tiene340.804.863 lecturas porque los mismos113.601.621 registros se escanearon tresveces para1/5/15min.456observaciones de quotes inválidas equivalen a152registros repetidos. No sumar esaslecturas como ticks únicos. Catálogos reconcilian; precios/volúmenes válidos; los recortes incluyen warmup y fechas intermedias para continuidad, no únicamente54fechasobjetivo.

Selftests PASS, cuatro chequeos de prefijosRTY sin outcomes PASS; test adicional hold30/120min y muestra100/50 PASS. Auditoría independiente de aritmética quote, costos/midalpha,identidades/subsets/timing/nooverlap;24estadísticas y límites reproducidos usando el procedimiento congelado. Esto no recertifica relojes/edadquotes ni validez teórica de bootstrap.

## Frecuencia de cruces: objetivo parcialmente resuelto

| Activo | CROSS1 BASE | CROSS1 ADX15 | CROSS1 SOFT200 | CROSS5 BASE |
|---|---:|---:|---:|---:|
| MNQ |173|135|99|42|
| YM |176|124|93|41|
| RTY |161|126|80|38|

Son casos con quote de entrada/salida. ADX15 conserva~70–78% de BASE1min; SOFT200 conserva~50–57%. Los tres BASE1min y tresADX15 superan100casos. SOFT2001min no llega100, tampoco ninguna variante5min; todas esas12celdas quedan inconclusas. **Más casos no es ventaja ni potencia suficiente garantizada**: seiscruces1min alcanzan el mínimo pero ninguno pasa ambos endpoints.

Entre cruces: YM1minADX15 media+0.751ATR y límite inferior alpha+0.022ATR, pero neto−0.219ATR; no pasa el componente económico. MNQ1minADX15+0.054ATR sin soporte; BASEMNQ−0.266ATR y RTY−0.681ATR. No es una inferencia formal de que ADX agrega valor; variantes son subconjuntos y la diferencia está expuesta a selección/multiplicidad.

## Momentum: resultado y fragilidad

| Activo | Barras min | Casos | Fechas | Neto ticks | Neto/ATR | Extra1tick/lado:neto/ATR | Sin5mejoresfechas:neto/ATR | Límite inferior neto corregido |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MNQ | 5 | 108 | 54 | +6.10 | +0.046 | +0.031 | -0.392 | -1.315 |
| MNQ | 15 | 89 | 51 | +30.39 | +0.221 | +0.210 | -0.258 | -0.890 |
| YM | 5 | 107 | 54 | +0.60 | +0.006 | -0.038 | -0.443 | -1.237 |
| YM | 15 | 95 | 51 | +11.26 | +0.222 | +0.188 | -0.160 | -0.903 |
| RTY | 5 | 108 | 54 | +34.76 | +0.892 | +0.838 | +0.310 | -0.307 |
| RTY | 15 | 86 | 48 | +38.38 | +0.652 | +0.611 | +0.289 | -0.333 |


ATR aquí es la escala de TrueRange20 anterior propia de cada marco. No es R de riesgo/retorno de cuenta, y ticks no tienen igualvalor entreactivos. Los dosmarcos prueban poblaciones/historias distintas, no duplicación independiente de muestra.

- **RTY es la mejor pista descriptiva entre los tres activos**, pero ningún momentum sobrevive los doslímites de Bonferroni48. RTY5min+0.892ATR (108casos),15min+0.652ATR(86); límites netos−0.307/−0.333ATR. MDE80aprox1.527/1.221ATR, mayor que mediasobservadas. Sólo muestra candidata, no validación ni equivalencia nula.
- RTY conserva medias positivas en prueba adicional defricción y al retirar las5mejoresfechas: +0.310/+0.289ATR. Esta retirada usa futuro para diagnóstico deconcentración, **no es un filtro operable ni una prueba estadística**. MNQ/YM se vuelvennegativos al retirar sus5mejoresfechas en losdosmarcos.
- MNQ/YM5min están cerca de cero después de costos; YM5min cambia a−0.038ATR con2ticks adicionales. MNQ/YM15min+0.221/+0.222ATR, pero límitesnegativos y dependencia delasmejoresfechas. No promocionar losdos.
- Comparado conRTYprevio, las medias netas enticks son+34.76/+38.38 en esta campaña, no+41.62/+42.66. Diferencia esperable por población54envez56fechas, publicaciónquotes, censura corregida y gates/historia; no se corrige retrospectivamente aquella acta ni se mezclan poblaciones.

### Horarios descriptivos, no optimización

| Activo | MOM5 hora10–11:30:n /netoATR | MOM5 hora11:30–12:30:n /netoATR | MOM5 desde12:30:n /netoATR |
|---|---|---|---|
| MNQ | 54 /-0.383 | 43 /+0.663 | 11 /-0.261 |
| YM | 54 /+0.040 | 48 /+0.094 | 5 /-1.207 |
| RTY | 54 /+1.346 | 45 /+0.356 | 9 /+0.841 |


RTY5min es positivo en los treshorarios observados y más alto en la primera franja; las últimas9señales no soportan conclusión propia. MNQ cambia de signo porhorario; YMúltimafranja sólo5casos. El calendario2h de bloqueo hace que hora refleje también orden deoperación/tiempo desdeprimerseñal: **no atribuir causalidad al reloj**. MOM15 tiene0casos intermediosMNQ/YM y1RTY; esosnulls no se convierten encero ni en una regla para evitar horario.

### Intensidad del movimiento previo

RTY5min: 1–2ATR n50,+0.919ATR;2–4ATR n49,+0.925;≥4ATR n9,+0.555. No hay mejora monotónica al exigir más intensidad. RTY15min: n50/26/10,+0.278/+1.114/+1.321; estratos pequeños/expuestos, no autoriza elegir2ATR como umbral ganador. MNQ yYM cambianpatrones de signo segúnmarco. Detallecompleto en momentum_descriptive.json, sin inferencia desubgrupos.

## Priorización posterior, NO ejecutada en esta entrega

1. Si se continúa, prioridad **RTY momentum**, antes que otra grilla deEMA: congelar validación nueva con datos/fechas no mirados permitidos por protocolo; conservar horizonte, costo/publicación y contar fechas independientes. No abríJan–Mar nireservas ni corrívalidaciónautomática.
2. No apilar filtros dehora/intensidad deeste desarrollo y llamar eso confirmación. Elegir como máximo unahipótesisnueva conmanifiesto y presupuesto propio.
3. EMA: en1min sí haymás señales, pero ademásmás costo relativo/ruido; elcandidatoYMADX15 orienta pero no certifica neto. No promoverlo ni seguirbajandofiltros pararescatarlo.5min sigueescaso parael mínimo100. Adaptar el evento sólo bajo pregunta nueva sin desenlaces para fijar frecuencia.
4. Mantener IPC×L2deCodex separado; no mezclar estosresultados con ventaja depicos/L2.

## Límites

Desarrollo expuesto,24nuevasceldas además de24anteriores, presupuestos porcampaña y elección sucesiva dehipótesis: no afirmación confirmatoria sobre todalabúsqueda. Índices correlacionados. Bootstrap20k encola0.05/48≈21draws, límites/MDEaproximados. Cantidad detrades no sustituye cantidad desesiones independientes. Bid/askexportado no pruebaedad,fills ni P&Lreal; costos asumidos. Holdout cerrado;sinLucid,raw,ledgerprecios o URLsfirmadas publicados.

**Aporte al referente:** se aumentó materialmente la muestra decruces envariosactivos sin encontrarventajavalidada;RTYmomentum conserva lapista descriptiva más consistente,confragilidad/inferencia documentadas antes decualquier validaciónnueva.

##24celdas completas

| Celda | Entradas con salida | Fechas activas | Neto / ATR | Neto ticks | Estado |
|---|---:|---:|---:|---:|---|
| MNQ_CROSS1_BASE | 173 | 54 | -0.266 | -19.39 | NO_SUPPORT |
| MNQ_CROSS1_SOFT200 | 99 | 46 | -0.001 | +5.89 | INCONCLUSIVE_SAMPLE |
| MNQ_CROSS1_ADX15 | 135 | 53 | +0.054 | -1.47 | NO_SUPPORT |
| MNQ_CROSS5_BASE | 42 | 31 | +0.551 | +93.22 | INCONCLUSIVE_SAMPLE |
| MNQ_CROSS5_SOFT200 | 33 | 24 | +0.523 | +92.30 | INCONCLUSIVE_SAMPLE |
| MNQ_CROSS5_ADX15 | 33 | 26 | +0.669 | +108.75 | INCONCLUSIVE_SAMPLE |
| MNQ_MOM5_BASE | 108 | 54 | +0.046 | +6.10 | NO_SUPPORT |
| MNQ_MOM15_BASE | 89 | 51 | +0.221 | +30.39 | NO_SUPPORT |
| YM_CROSS1_BASE | 176 | 54 | +0.388 | +7.29 | NO_SUPPORT |
| YM_CROSS1_SOFT200 | 93 | 41 | +0.763 | +15.52 | INCONCLUSIVE_SAMPLE |
| YM_CROSS1_ADX15 | 124 | 52 | +0.751 | +14.58 | NO_SUPPORT |
| YM_CROSS5_BASE | 41 | 31 | -0.251 | -6.63 | INCONCLUSIVE_SAMPLE |
| YM_CROSS5_SOFT200 | 35 | 25 | -0.434 | -15.27 | INCONCLUSIVE_SAMPLE |
| YM_CROSS5_ADX15 | 36 | 28 | -0.281 | -8.04 | INCONCLUSIVE_SAMPLE |
| YM_MOM5_BASE | 107 | 54 | +0.006 | +0.60 | NO_SUPPORT |
| YM_MOM15_BASE | 95 | 51 | +0.222 | +11.26 | NO_SUPPORT |
| RTY_CROSS1_BASE | 161 | 53 | -0.681 | -10.91 | NO_SUPPORT |
| RTY_CROSS1_SOFT200 | 80 | 38 | -0.418 | -5.80 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS1_ADX15 | 126 | 48 | -0.566 | -9.13 | NO_SUPPORT |
| RTY_CROSS5_BASE | 38 | 28 | +0.158 | +4.71 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS5_SOFT200 | 34 | 25 | +0.067 | +0.42 | INCONCLUSIVE_SAMPLE |
| RTY_CROSS5_ADX15 | 32 | 24 | +0.231 | +10.32 | INCONCLUSIVE_SAMPLE |
| RTY_MOM5_BASE | 108 | 54 | +0.892 | +34.76 | NO_SUPPORT |
| RTY_MOM15_BASE | 86 | 48 | +0.652 | +38.38 | NO_SUPPORT |
