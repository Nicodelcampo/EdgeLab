# Auditoría de PICOS-DEFENDIDOS (PR Nicodelcampo/EdgeLab#200) contra los aprendizajes de la semana (2026-11-19)

Estado: VIGENTE — auditoría previa al lanzamiento (no se corrió nada con desenlaces). Pedido de Nico: «repasá todos los aprendizajes de la
semana, luego auditá esta corrida, corregí los puntos que sean necesarios y determiná si conviene que la lances y gestiones vos en esta
sesión o el otro agente en la otra». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 0. Causa raíz común
El PR se armó sobre `foundation` (5998f175), y `foundation` no tenía los 470 commits de la semana:
- la rama de esta sesión quedó sin mergear desde #199 (11-nov);
- faltaban HOLDOUT-A5, las guardas K27–K56, `LEER_ANTES_DE_CADA_CORRIDA` v4, `tools/potencia_previa.py`, `diagnostico_grilla` y el
  veredicto M1;
- `foundation` tenía otra `CLAUDE.md`, sin A5 ni K55.

El otro agente diseñó con las reglas que veía; los errores de abajo son de proceso, no de su criterio. Corrección: PR
Nicodelcampo/EdgeLab#201 (la semana a `foundation`).

## 1. Hallazgos
| # | Hallazgo | Aprendizaje que lo cubre | Gravedad | Corrección |
|---|---|---|---|---|
| 1 | DESC 2025-08 → 2026-03 (8 meses de ticks) y OOS abr–sep 2026: la partición vieja | HOLDOUT-A5 (17-nov): toda campaña nueva descubre y confirma sobre M1 largo intercalado. Elegir entre miles de celdas con 14 meses dio ganadoras de ruido (VEREDICTO_M1: −193 R en 1.453 sesiones) | Bloqueante | Versión A5 sobre M1 de NT8 2006 → 2025-07 (meses DESC/REP), calibrada contra ticks |
| 2 | 207.360 celdas por canal (× 2 canales) sobre esos 8 meses | K55/K56: número efectivo de variantes, celdas casi vacías, perillas que mueven lo mismo; la «variante rápida» de Z tenía 4 operaciones | Bloqueante | Familia chica pre-registrada: 12 definiciones × 2 ejecuciones, con el diagnóstico de mecanismo escrito antes |
| 3 | Se salta la regla exacta de la captura | Ritual «idea vista en el visor → primero la regla exacta, con costos y en todos los períodos; después los mecanismos» | Alta | PD0 = la regla de la captura (10 min, nivel PAR, tendencia a favor, disparo al alejarse), con su control (tendencia en contra) |
| 4 | Velas de 1 y 3 min: 76 % de las filas en 1 min. Riesgo mínimo 0,5 ATR(14) de 1 min ≈ 5 pts en NQ contra 1,5–2 pts de fricción canónica (0,3–0,4 R) | K4–K9: fricción en R ≤ 0,08 antes de abrir. Lo «confirmado» del 04–08/11 era fricción | Alta | 5, 10 y 15 min solamente |
| 5 | Pre-registro sin «Antecedentes:», «Potencia previa:», «Lectura previa:» ni «Diagnóstico de mecanismo:» | K32, K27–K30, guía v4, K55/K56 (`preflight.validar_preregistro`: 4 errores sobre este archivo) | Bloqueante con la cadena vigente | Pre-registro nuevo con las cuatro líneas |
| 6 | Antecedentes incompletos: cita IPC-NIVEL y DOBLE-RETROCESO, no los factores en contra más cercanos | «Reutilizar antes de construir», `tools/antecedentes.py` | Media | Se citan F-ESCALONADAS-M1-SIN-SENAL (escalera plana de picos operada a favor de la ruptura: 18/18 celdas ≈ 0 en bruto, A5 2006–2025), F-FILTRO-PICOS-NO-AGREGA y F-HFT-ZONAS-NO-SON-SOPORTE (a favor: niveles con actividad rebotan menos) |
| 7 | Fricción declarada «NQ 4,6 pts, ES 2,7 pts por viaje» | Costos sólo de `edgelab/costos.py` | Baja (el embudo usa la canónica) | La canónica es NQ 1,55 (adverso 2,05) y ES 0,89 (1,39); se corrige en el pre-registro nuevo |
| 8 | Holdout desde 2026-10-01 con N fijo 150, sin plan de potencia | K27/K49: apertura con plan de potencia; un OOS mata sólo con potencia | Media | Holdout A5 (meses HOLDOUT intercalados) con plan de potencia antes de abrir |
| 9 | Ejecución en el primer tick tras `k` | Motor único `ejecucion.py`, calibrado (K40) | OK | Se mantiene (contrato de tablas) |
| 10 | Plano antes de las 16:45 ET (Lucid) | Ejecutabilidad primero | OK | Nada cruza la sesión |
| 11 | Medir en R | Nico, 02-nov | OK | Se mantiene |
| 12 | Detección causal (tests por fuerza bruta, por cortes y por disparo) | K48, K53 | OK | Se reutiliza sin cambios (`picos_defendidos.py`) |

## 2. Qué se corrigió (rama `claude/vibrant-clarke-s9z6e2`, sin tocar los archivos del PR #200)
- `edgelab/research/picos_defendidos_a5.py`:
  - contrato de `tablas.py`;
  - reutiliza la detección del PR;
  - 12 definiciones + control;
  - temporalidades de 5, 10 y 15 min;
  - nivel PAR;
  - tendencia E20;
  - stop estructural con riesgo mínimo de 0,5 A;
  - objetivos P + 0,5 A y P + 1 A.
- `docs/research/picos_defendidos_a5_20261119/CAMPANA.json` y `PREREGISTRO.md`: NQ, ES e YM sobre M1 de NT8 2006 → 2025-07, con la
  partición A5.
- **Las campañas `PICOS-DEFENDIDOS-NQ/ES` ya estaban lanzadas cuando se escribió esto.** El otro agente las activó el 2026-11-19 a las
  19:37 UTC por la instrucción de Nico «Mergea todo y lanzalo», con conductor local porque el Debian está en PAUSE. Fue 7 minutos antes
  del comentario de esta auditoría en el PR #200.
- Siguen activas. Se agregó a cada una una decisión con la recomendación de detenerlas; no se desactivan desde acá porque las conduce otra
  sesión.
- Ningún resultado de esas campañas se promueve sin pasar por la versión A5.

## 3. ¿Quién la lanza?
- **Versión vieja:** está corriendo en la otra sesión. Detenerla o dejarla terminar lo decide Nico. Si termina, sus resultados se leen
  como exploración en 8 meses, nunca como confirmación.
- **Versión A5: esta sesión.** Razones:
- **Guardas:** la cadena A5 (`tools/a5_campana.py`, calibración M1 contra ticks y lectura DESC/REP con LORD++) y las guardas existen hoy sólo
  en esta rama, hasta que se mergee #201.
- **Experiencia:** esta sesión corrió esta semana las campañas A5 (EXTERNAS-28, ROBOQUANT, OPTION-ALPHA, FLUJOS-MACRO, ESCALONADAS-M1).
  Tiene el acceso a Kaggle verificado y el contexto de los factores en contra.
- **Un solo escritor:** el otro agente tiene el PR #200 abierto con Auto-fix vigilándolo; que lo lancen los dos duplicaría pruebas en el
  contador global. El otro agente no debería lanzar `PICOS-DEFENDIDOS-NQ/ES`.
- **Si se prefiere el otro agente:** primero tiene que mergearse #201 en `foundation` y él tiene que usar la versión A5, no la del PR.

Aporte al referente: evita gastar una campaña de 400 mil celdas sobre 8 meses en la configuración que esta semana demostró producir
ganadoras de ruido, y la reemplaza por una medición que puede refutar o sostener la idea de Nico con 18 años de datos.
