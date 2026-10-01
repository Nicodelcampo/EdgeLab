# RTY momentum — validación de desarrollo y herramientas EdgeLab

## Veredicto

**Ningún perfil pasa G1; G2 formal bloqueado. No hay edge validado ni autorización de operación.** Promedios positivos y resistencia a costos supuestos son pistas de desarrollo, no confirmación. Regla y 54 fechas comunes oct–dic 2025 ya expuestas se mantuvieron congeladas. No se abrieron enero–marzo ni holdout; el contrato RTY03-26 aquí se negocia en diciembre2025, NO es un estudio de marzo2026.

## Resultados

| Perfil | Trades | Ticks netos medios | Media sin 5 mejores trades | RTY12-25: n / media | RTY03-26: n / media | G1 |
|---|---:|---:|---:|---|---|---|
| MOM5 | 108 | 34.76 | 18.27 | 94 / 42.33 | 14 / -16.11 | FAIL |
| MOM15 | 86 | 38.38 | 21.16 | 78 / 39.78 | 8 / 24.73 | FAIL |

MOM5 falla concentración contractual; MOM15 falla concentración y n<100. RTY12-25 aporta106,0% y94,0% del neto total respectivamente: 106% es posible porque el otro contrato pierde. La exposición es muy desigual; esto no demuestra causalidad por vencimiento ni refuta momentum universal, pero no permite relajar el80% del contrato G1.

Los 5 mejores trades aportan49,9%/48,1%; quitarlos deja ganancia. Los 10 mejores aportan83,5%/81,5%; quitarlos aún deja media6,32/8,03 ticks. La prueba anterior quitaba mejores FECHAS: no es el gate G1 de TRADES. No rescatar con filtros sobre esas colas.

Selección cronológica MOM5/MOM15 en RTY12-25 eligeMOM5; en RTY03-26 arroja -0,478U,14trades. Es walk-forward diagnóstico sobre contratos YA expuestos, no OOS nuevo. U es la escala ATR previa de cada evento; mediaU y media ticks responden a estimandos diferentes.

### Comprobaciones favorables, con límites

- Estrés de fricción1/2/3ticks por lado: MOM5 +34,76/+32,76/+30,76ticks; MOM15 +38,38/+36,38/+34,38. ComisiónUSD2,25/lado SUPUESTA, valor tickRTYUSD5. Spread observado está en bid/ask. No fills reales ni G3 certificado.
- Ambos lados long/short muestran media positiva al seguir momentum. Siempre largo en los mismos instantes da -17,81/-8,90ticks; siempre corto +9,69/+0,93. Son contrafactuales DIRECCIONALES a igual ancla, NO controles temporales independientes.
- Oct/Nov/Dic: MOM5 +59,36/+16,16/+26,95ticks(n38/36/34); MOM15 +40,42/+48,49/+24,66(n28/31/27). No tendencia monotónica ni selección de horarios.
- MFE/MAE medianos de mid:92/57ticks y96/55,25. Cuantiles dentro del horizonte original, sin optimizar stops/targets. No liquidación ni fills; edad de quote no certificada.
- DD de saldo de trades cerrados, un contrato:USD6.111 yUSD4.118,50. NO DD mark-to-market certificado.

### Inferencia: no reemplazar gates con diagnósticos favorables

- CI percentil estacionario50.000réplicas95% sobre ratio por trade: MOM5 [0,195;1,590]U, MOM15 [0,032;1,255]U. Positivo pero NO es CIprimario G2, no corrige selección completa. La corrida previa con corrección múltiple seguía sin pasar.
- Función real bootstrap-t RECHAZA54<160sesiones. No bajamos mínimo.
- DSR diagnóstico: con54intentos nominales iid0,501/0,345; con100,0,412/0,266. DependenciaACF reduce ligeramente. Lejos de0,95, pero N_eff histórico no certificado; no llamar FAIL formal DSR ni probabilidad deedge.
- PBO48: ABSTAIN porque un subsplit tiene celda sin trades. No eliminar variantes difíciles ni imputar media0. PBO de6momentum predeclarados0,20,70splits: favorable limitado, NO auditoría de toda selección. Se excluye antiguoRTY6por ejecución censurada/no compatible; ensayos históricos restantes desconocidos.
- Sensibilidad: ABSTAIN sin malla vecina pre-registrada. No construir plateau posthoc para aprobar.
- exMCPT concentración: p0,384/0,251. Diagnóstico temporal, no test de ventaja.
- Authority de promoción: allowlist de contratosG2 vacía, distinta de allowlist de métodoDSR. No se cambia ni se intenta promoción.

## Revisión de herramientas

Inventario por rutas:626archivos código/tests/docs; búsqueda AST/palabras clave110módulos candidatos. No se ejecutaron ni auditaron semánticamente los626. Lectura dirigida de contratos, entrydocs, estadísticas, inferencia, costos, controles, cerebro y protección de reservas. Se empaquetaron12archivos módulos verificados de foundation@391314907dec889599493c4a38282171d94a2f25.

| Herramienta | Uso o decisión |
|---|---|
| stats/cluster_estimand.py | Ratio por trade, ceros de actividad por sesión, PPW, bootstrap estacionario diagnóstico; refusal real del primario160sesiones |
| research/g2_ratio.py | PBO y WF con ratio; g2.py variantes por totalPnL NO son intercambiables con conteos desiguales |
| research/g2.py | DSR no anualizado, concentración temporal, sensibilidad ABSTAIN sin vecinos |
| research/g2_decision.py + promotion.py | Contratos/promoción inspeccionados; ninguna decisión PASS emitida, authority vacía |
| research/costs.py | CostScenario RTY explícito. RTY no registrado: default6E sería incorrecto; NO usarlo. No tarifa certificada |
| research/holdout_guard.py | Compuerta real previa a leer ledgers; desarrollo autorizado, holdout cerrado |
| research/nulls.py + edge_brain/control_guard.py | Interface de nulos/controles temporales revisada; contrafactual de dirección no equivale a control temporal PASS |
| edge_brain/coverage.py + eligibility | NOT_OBSERVED no es0; faltan artefactos canónicos de cobertura/paridad. No certificación Brain fabricada |
| tools/falsification_battery.py + deep_falsification_probe.py | Fijados a NQ25T/HFT; no correrlos como RTY genérico |
| tools/ipc_robust.py | Semántica IPC/zonas distinta de MOM60; no reutilización directa |
| research/sim.py + edge_factory | Requieren semántica de estrategia/TP/SL/feed/paridad; poner stops ficticios alteraría hipótesis. No certificación simulador |
| fixed_b/cobertura + recut_holdout | Calibran métodos/seal; no son permiso de rebajar160 ni abrir reserva |
| riesgo/propfirm MonteCarlo | No promocionar con sizing o equity de edge aún no certificado |

146 tests DIRIGIDOS PASS,5,57s. Inicialmente pytest faltaba; instalado. Primera suite145PASS1FAIL por fixture de log histórico no copiado en snapshot aislado. Restaurado archivo TRACKED exacto y mismo suite pasa: sin editar lógica/gates. No suite completa. Copia de log alterada por fixtures no se publica ni se adjudica como acceso real.

## Procedencia y ejecución

Kaggle privado: https://www.kaggle.com/code/nicolasbuttaro/edgelab-rty-momentum-validation-tools-20261001 v1 COMPLETE. Script descargado(info.blob.source) igual al transporte local. is_private=true/version1. Fuente wrapper/cargas privadas NO versionada.

validate.py SHA256 e3480bc0fa9bd3ed2bc7f0e74cecae5c06607bf75343c366eae0e74ce08d9c7a.
manifestSHA256 f9f1fbd5cece3eed0659ac014525c6c392f91456095aa935e8780bd3ad48c40d.
Preflight comparado primero: script,3inputs y12módulos coinciden byte por byte; manifest remoto igual local. Dos parquets verificados por SHA antes de observar trayectorias. Archivo12-25 escaneado8.035.696filas,03-26 869.569; quotes inválidas28/3. Escaneo de trayectorias dentro del rango de entradas/salidas original; no nueva población ni periodos protegidos.

Reconciliación independiente desde bid/ask inmutables:108/86 identidades únicas, fórmulaPnL, remoción5trades, sumaspor contrato/mes PASS. La función ejecutada para batería no fue reutilizada para esa comprobación. Code/hashes/outputs agregados acompañan este documento; ledgers/precios/URLsfirmadas privados NO se publican.

Reglas generales NORTH_STAR verificadas por Git: RTYjulio–diciembre2026 sellado. Excepciones ES/NQ yL2 no aplican. MetadataJan–Mar tiene60fechas potenciales; no se leyeron outcomes. Incluso54+60=114 no llega160. No sumar así sin particiones nuevas y autorización.

## Prioridad siguiente

1. **No promover ni afinar filtros con estas ganancias.** Mantener MOM5 como candidata de desarrollo, MOM15 secundaria; ninguna aprobada.
2. Antes de datos nuevos: cerrar cobertura, paridad exacta NT8, quoteage/fills y tarifa RTY; registrar todo budget histórico de selección y authority pendiente con responsables. No confundir reparación de infraestructura con evidencia.
3. Pre-registrar réplica cronológica y cobertura contractual más equilibrada sobre datos de desarrollo autorizados. Fechas adicionales requieren aprobación y reserva intacta. No basta repetir54, ni sumar60 y declararloG2.
4. Si réplica mantiene ganancia sin concentración y soporte suficiente, ejecutar gates completos CIprimario/PBO/DSR/WF/sensibilidad; si no, archivar esta configuración, no rescatar mejor contrato/horario/stop posthoc.

Aporte al referente: el candidatoRTY positivo pierde su condición de estabilidadG1 por concentración contractual; herramientas evitan confundir bootstrap/PBO parciales con edgevalidado.
