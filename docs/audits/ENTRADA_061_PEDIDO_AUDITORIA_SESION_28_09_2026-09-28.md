# Entrada 061 — Opus 5.5 → Auditor: todo lo medido el 28/09 desde la 060 (pedido de auditoría)

**Repo:** `Nicodelcampo/EdgeLab`, rama `foundation/f0b-compatibility-probe`, commit `7b6cc25dbbe9fe60926512cc96ba2073b4c40701`.
**Firewall:** outcomes sí (cada corrida con OK explícito de Nico en el chat), holdout intacto (nada ≥ sesión 1-oct-2026),
replicaciones A3 no abiertas. Registro vivo: `docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` (anexo 28/09).

## 1. Resultados (acta de cada uno en `docs/research/RESULTADO_*`)
| Estudio | Veredicto | Acta |
|---|---|---|
| ESPEJO-NICO-100T (re-corrido con pool estricto, 059) | 0/8 | RESULTADO_ESPEJO_NICO_100T_DESCUBRIMIENTO |
| ESPEJO-VOLLIMP-100T | 0/24 | (registro) |
| IPC-NIVEL-MES formación | 1/8, contra el imán (techo −6,2 pp vs pivote) | RESULTADO_IPC_NIVEL_MES_DESCUBRIMIENTO |
| IPC-NIVEL-REGRESO virgen (D×V terciles) | 1/36 (piso cerca+poco volumen −6,8 pp vs pivote) | RESULTADO_IPC_NIVEL_REGRESO_MES |
| PIVOTES-BARRIDO-MES (censo 272 mil) | pivotes se barren como el azar → el +5 pp del control C-PIV era selección | RESULTADO_PIVOTES_BARRIDO_MES |
| IPC × densidad HFT (fijo y desgaste 35/100/500) | 0/16 — **exploratorio, Nico desconfía del diseño** | RESULTADO_IPC_NIVEL_HFT_MES |
| ESPEJO-CONT 25t/100t (6 instrumentos, Lucid+NT8, filtros VWAP/EMA/S2v2/no-lista/inef) | ningún R bruto positivo; cerrado | RESULTADO_ESPEJO_CONT_100T_{ES,NQ,YM,MES,MNQ,MYM} |
| ESPEJO-REV-100T cruce hacia B (idea de Nico) | NQ: 25 % del cruce +2,2 a +4,6 pp en dos muestras disjuntas; ES: por debajo del azar; GC, YM: azar | RESULTADO_ESPEJO_REV_100T_{NQ,ES,GC,YM} |
| **ESPEJO-REV-100T GC, TP 2 W / SL 1 W** | **R bruto +0,023 W; exceso empírico vs misma operación al azar +0,078 W [+0,042; +0,119]** | RESULTADO_ESPEJO_REV_100T_GC (+ control) |
| Contextos L2 NQ (4 climas) | **PASS** sin STOPs; deriva en el roll a vigilar | RESULTADO_CONTEXTOS_L2_NQ |
| Auditoría dataset Kaggle NT8 canónico | filas y catálogos idénticos; conteos del resumen del upload erróneos | AUDITORIA_KAGGLE_NT8_CANONICAL |

## 2. Errores míos detectados y corregidos (en orden)
1. Nulo de CONT arrancaba en el nivel tocado y no en el cierre de la vela de entrada (toque por mecha) → exceso sesgado en
   contra; corregido, corridas relanzadas. La lectura previa «continuación pierde ⇒ reversión gana» quedó retractada.
2. Bootstrap degenerado con n < 30 daba p = 0 (IPC-REGRESO listó 4 sobrevivientes falsos; smoke de CONT) → mínimo 30.
3. Tope de 8.000 eventos cortaba en orden cronológico (NQ usó 20/171 sesiones) → sesiones sorteadas con semilla.
4. **El nulo simulado (`simulate_null`, paseo i.i.d. de ternas 25t) no es neutro por TP y depende del instrumento**:
   calibración en velas al azar: NQ +0,012 en TP 0,25 y −0,02 en TP amplios; ES hasta **+0,108 W** en TP 2 / SL 1; GC +0,025.
   Las decenas de celdas «sobrevivientes» con TP 0,25 en NQ/YM/MYM/MNQ eran ese sesgo. Regla nueva: el exceso se lee
   contra el control empírico (misma operación en 3 velas al azar de la misma sesión).
5. Libro L2 NQ: cruce intra-lote, cruce en preapertura que vaciaba el libro, foto de 9 niveles en MBP10 (excepción
   acotada a la cola, fuera de ella sigue fallando cerrado). 0 → 1.371 minutos elegibles por sesión.
6. Detector IPC-NIVEL: zonas de 11 h inflaban el ajuste (tope 200 velas); luego picos monótonos por corrección de Nico.
7. Un commit subió velas de GC derivadas de Lucid (171 npz); retiradas del árbol en el commit siguiente, **siguen en el
   historial** (pendiente decisión de Nico sobre reescribirlo).

## 3. Preguntas al auditor
1. **Candidato GC.** Operación: límite en A a favor de B tras completar el espejo (W ≥ 100 t, 30 velas de 100t, nivel 5,
   feb-2026 excluido por ser el mes que Nico miró), llenado sólo si la vela pasó A ≥ 1 tick, TP 2 W / SL 1 W, SL primero,
   horizonte 150 velas. ¿Es válido usar el control empírico (3 velas al azar de la sesión, misma geometría) como referencia
   principal? ¿Qué sesgo puede quedar (selección de velas al azar, modelo de llenado del límite, horizonte)?
2. ¿Qué exigirías antes de la confirmación única abr–jun (Lucid): estimación de fricción GC propia, test del llenado con
   ticks, sensibilidad a W (≥ 80/120/150)? ¿Cuenta como selección que la configuración (W ≥ 100, nivel 5) salió de la
   calibración visual de Nico en febrero, aunque febrero se excluyó?
3. NQ cruce 25 %: +2–4,6 pp en dos muestras disjuntas de ~16–20 sesiones cada una (tope de cómputo). ¿Alcanza para
   pre-registrarlo por clima L2 en jul–sep (desarrollo A3) o exigís antes una corrida con todas las sesiones?
4. ¿Ves otro sesgo en `simulate_null` que explique la dependencia por instrumento (drift de centrado, colas de las ternas,
   agregación 25t→100t) y conviene reemplazarlo en todos los estudios por el control empírico?
5. Lo más probable que esté mal y la prueba barata.

Respondé en una subpágina «Entrada 062 — Auditor».
