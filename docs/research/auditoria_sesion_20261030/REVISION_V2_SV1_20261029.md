# Revisión del agente de SV1 y preparación v2 (2026-10-30)

## A. Historial real del agente de SV1 (19→30 oct), medido por SSH el 2026-10-30 00:33

**Código en SV1:** `0f3a5466` (26-10 23:20, "Reporte de alineación del agente del Debian"). `foundation` va por `4537f5b9`: SV1 está 3 días atrás y no tiene la v2 ni las olas 1–10.

**Funcionó**
- Ciclo cada 10 min sin cortes: 1421 ticks registrados, sin pausa; RAM disponible 4,3 GiB, carga 0,3 (producción intacta).
- Publicación de estado arreglada: `autopilot/state` tiene 424 commits, el último 03:31 UTC de hoy.
- Generador sano desde el 27-10 (tras el fix de la `lente`): indexa 1639 fuentes / 41.623 pasajes, el proponente produce borradores (lente `hueco_gramatica`), ~4,7 min de CPU por corrida.
- Embudo tomado de la nube sin arrancar de cero: 23 campañas con estado; las FIN quedaron bien clasificadas (PISTAS_VIVAS ×7, SIN_CANDIDATAS ×6, SIN_POTENCIA_HOLDOUT, SIN_REGLA_OPERABLE).

**No funcionó**
1. **7 campañas BLOQUEADAS en CONTEO** (U1-ES, U1-ORO, U1-YM, U1-ZONAS-AVCL-NQ, U1-ZONAS-BT2-NQ, U1-ZONAS-ES, U1-ZONAS-NQ): "la etapa CONTEO falló 3 veces (error)", las tres fallas el 26-10 entre 22:59 y 23:42. El estado no guarda la excepción. CONTEO lee el holdout sellado: en SV1 la carpeta `/var/lib/edgelab-datos/holdout_sellado` depende de Dukascopy, que falla (punto 3).
2. **Cero lanzamientos del ciclo clásico** (`launched` vacío en los 1421 ticks) y **0 de 44 promociones aprobadas**: todas `RECHAZADA_MECANICO`, la mayoría por "sin fricción medida" del instrumento. El generador sigue proponiendo las mismas 11 candidatas viejas (DATA-METALS, PNL-1, IDM-1…), no las ideas nuevas del catálogo del scrap.
3. **Dukascopy cae por timeout de 2 h** (29-10 23:40, y 3 alertas en total). Sin esos datos el holdout sellado local no avanza.
4. **Ruido de alertas:** 36 de 39 alertas son la misma unidad del generador en estado `failed` de los días 20–26, repetida por el vigilante porque nadie hizo `reset-failed`.
5. **Sólo 2 campañas vivas** (U1-RACIMOS-ES/NQ en CONTEO PENDIENTE). Todo lo nuevo (olas 1–10, CVGAP, CONF-CVR, ASIA, TORI, OTR-930, ORO-ALMUERZO) se corrió en la nube, no en SV1.

(B, C, D y E: en progreso)

## A2. Auditoría del reporte "Iteración V2: filtros, canastas y paridad NT8" (29-10)
- **No está en el repo:** `filtros_transversales.py` y `otr_930_sweep_v2.py` no existen en `foundation` (bba9949c); sólo `gestor_canastas_regimen.py`. El resto vive en el patch adjunto, sin aplicar ni testear.
- **Los números no son creíbles como medición:** PF de 1,2–2,3 a 7–40 y DD −63 % a −91 % en las 11 familias, todas en 6/6 gates. Saltos así con 4 filtros son la firma de sobreajuste, no de edge.
- **Fuga de holdout:** la tabla mezcla IS + OOS + Holdout v3 (hasta 29-10). Si los umbrales (ER 0,58/0,20, 3,5σ, 35–60 min, CUSUM −2,2σ) se eligieron mirando esa tabla, el holdout quedó consumido para estas 11 familias.
- **Filtros elegidos después de mirar:** dirección distinta por tipo (reversión vs ruptura) y umbrales sin pre-registro ni conteo en el registro de pruebas; las grillas V2 suman >2 M celdas por canal.
- **"Gestor V2" = "4 filtros" en las 11 filas:** el gestor de canastas no agrega nada medible, o la columna está copiada.
- **Qué haría falta para que valga:** pre-registrar umbrales fijos con su justificación ex-ante, contar los ensayos (N_eff), correr DESC→OOS por el embudo con FDR, y dejar el holdout para una sola apertura con acta. Paridad NT8 SL-first: bien como criterio, pero falta la prueba contra NT8 real.

### A2.1 Revisión del patch (3291 líneas, 20 archivos) — corrige y endurece A2
- **La tabla de PF/DD sale de datos SINTÉTICOS, no de mercado.** `tools/auditar_equity_filtros_y_nt8.py` genera las operaciones con `rng` (`np.linspace` de fechas 2025-08-10..2026-10-29) y **programa** que los días que los filtros rechazan rindan peor (líneas ~94-104: en reversión, `er>0.58`/cola/vol alta degradan el retorno; en ruptura, `er<0.20`/demora>60 m). Después mide que los filtros mejoran el PF. Es circular: el resultado está puesto a mano. No mide nada del mercado.
- **Lo que sí está bien encaminado:** el patch trae 4 campañas reales (OTR930-V2-NQ, OTR930-V2-CFD-NQ, ORO-ALM-V2-GC, ORO-ALM-V2-CFD) con DESC hasta 2026-03-31, `holdout.desde = 20261001` y criterio de refutación por FDR q≤0,10. Están en DESC/CORRIENDO. Ese es el camino válido: el veredicto lo tienen que dar esas campañas, no la tabla.
- Por lo tanto la fuga de holdout de A2 no aplica a datos reales (el holdout de la tabla es inventado); sí aplica el riesgo de que alguien tome la tabla como evidencia.

## Correcciones aplicadas
1. **PR #155 — causa de las 7 BLOQUEADAS en CONTEO.** Los kernels están `complete` en Kaggle; el embudo contaba como falla el 404 de los primeros minutos tras el push y relanzaba el mismo slug 3 veces. Ahora hay 1 h de gracia y el motivo real queda en el historial. Test nuevo en verde. Tras el merge, en SV1 hay que reactivar las 7 (fase CORRIENDO, mismo handle, fallas 0) para traer el resultado sin relanzar.

## B. Auditoría de las corridas de la nube (45 campañas en el repo, bba9949c)
- **Resultado global:** 0 CONFIRMADAS. 25 FIN/PISTAS_VIVAS, 12 CONTEO/PENDIENTE (esperan holdout), 6 SIN_CANDIDATAS, 1 SIN_POTENCIA_HOLDOUT, 1 SIN_REGLA_OPERABLE.
- **Fallas registradas:** 7 (4 "error" de Kaggle sin detalle —el mismo defecto del #155— y 3 "no se pudo traer el resultado: FileNotFoundError" del runner local).
- **GRAVE — dos conductores sobre las mismas campañas.** El traspaso dio a SV1 la conducción desde el 26-10 22:00, pero la sesión en la nube siguió moviendo **U1-RACIMOS-GRILLA-ES/NQ, U1-ZONAS-BT2-ES/NQ, U1-6E-GRILLA y U1-ZONAS-GRILLA-YM** el 28 y 29-10 (con las ACTAs de holdout de BT2-ES, BT2-NQ y RACIMOS-ES). Los estados divergen: en SV1 BT2-NQ está BLOQUEADA y RACIMOS-ES/NQ en CONTEO PENDIENTE con otros handles; en el repo, con actas. Riesgo: kernels relanzados con el mismo slug, pasos de LORD++ gastados dos veces y **una segunda apertura de holdout** de la misma familia.
- **Las familias nuevas (CVGAP, OTR930, ORO-ALM, ASIA, TORI, CONF-CVR, 28-29/10) sólo las condujo la nube.** SV1 no tiene sus módulos (corre 0f3a5466). Si se actualiza SV1 sin traer esos estados, las toma de cero.
- **Antes de actualizar SV1 hay que reconciliar:** decidir por campaña qué estado manda (el del repo, que tiene actas), copiarlo a `autopilot_runs/embudo/` de SV1 pisando el viejo, y que la nube deje de conducir. Sin esto, no lanzar.

## C. Resultados de las 45 campañas (tabla completa en tabla_campanas.txt)
- **Réplica OOS: 0 de ~480 pistas confirmadas** en las 25 campañas que llegaron a PISTAS. La mejor (ASIA-NQ) dio p Simes 0,039 contra un nivel LORD de 0,0036. En DESC las mejores pistas tenían cota inferior IC90 de 5–18 puntos; en OOS la canasta media queda entre −2 y +5 con IC que cruza 0. Es la firma de la maldición del ganador: grillas de ~1 M de celdas con 30–50 operaciones por celda seleccionan ruido.
- **"PISTAS_VIVAS" no es evidencia a favor:** significa "no refutada por falta de potencia". Con 30–50 operaciones por pista la réplica casi nunca tiene potencia.
- **4 reclasificaciones post-hoc** (EXPZ-NQ, EXPZ-CFD, ZGAP-NQ, ZGAP-CFD: de SIN_CANDIDATAS a PISTAS_VIVAS el 26-10, con una canasta armada después de ver la réplica). Correr el arco después del tiro: no cuentan como evidencia.
- **Los candidatos reales son las 11 en CONTEO con acta** (CVGAP-NQ, CVGAP-CFD-NQ, U1-YM, U1-ES, U1-ORO, U1-RACIMOS-ES/NQ, U1-ZONAS-AVCL-NQ, U1-ZONAS-BT2-ES/NQ, U1-ZONAS-ES, U1-ZONAS-NQ): pasaron DESC→INTEGRIDAD→TOPES y esperan el holdout. BT2-ES dice además "ninguna candidata pasa placebo/latencia".
- **Diagnóstico de fondo:** el cuello no es de ideas sino de potencia. Menos celdas por familia (cientos, no millones), horizontes con más operaciones, y familias que agrupen instrumentos para tener N.

## D. Las 12 reglas con acta: DESC vs OOS (tabla en tabla_11_actas.txt)
| CID | DESC media (n) | OOS media (n) | OOS IC90 | lectura |
|---|---|---|---|---|
| CVGAP-NQ | 42,1 (34) | 19,1 (88) | [4,5; 33,2] | única con OOS claramente > 0 |
| U1-ZONAS-BT2-ES | 3,3 (36) | 2,5 (29) | [−0,1; 4,7] | casi; pero no pasa placebo/latencia |
| CVGAP-CFD-NQ | 17,6 (111) | 10,5 (110) | [−2,6; 23,0] | positiva, no significativa |
| U1-RACIMOS-NQ | 24,2 (38) | 19,8 (13) | [−7,0; 43,4] | n OOS muy chico |
| U1-ZONAS-NQ | 30,6 (81) | 10,7 (52) | [−12,2; 31,9] | se encoge a un tercio |
| U1-YM | 53,1 (31) | 12,7 (32) | [−20,3; 42,6] | se encoge a un cuarto |
| U1-ORO | 6,6 (41) | 1,6 (17) | [−3,4; 5,9] | casi nada |
| U1-ES | 7,8 (34) | −0,6 (39) | [−3,6; 2,5] | desaparece |
| U1-RACIMOS-ES | 6,0 (63) | −0,5 (46) | [−5,2; 4,2] | desaparece |
| U1-ZONAS-BT2-NQ | 21,4 (30) | −17,5 (42) | [−42,6; 6,4] | se da vuelta |
| U1-ZONAS-ES | 10,3 (54) | 0,0 (8) | — | OOS sin operaciones |
| U1-ZONAS-AVCL-NQ | 6,8 (41) | sin OOS | — | — |
- **Encogimiento DESC→OOS: mediana ≈ 0,3.** Lo que DESC muestra hay que dividirlo por ~3 para tener una expectativa honesta.
- **Varias tienen acta con OOS ≤ 0** porque la regla del 24-10 "el OOS mata sólo con potencia" las dejó pasar: con 8–46 operaciones la réplica no tenía potencia para matar. Eso es correcto como regla, pero no las vuelve candidatas.
- **Filtros nuevos:** ninguna de las 12 pasó por los filtros de la iteración V2 (`filtros_transversales.py` no está en el repo; el patch no se aplicó).
- **Holdout:** ninguna tiene todavía resultados de holdout en el estado (CONTEO PENDIENTE: piden n_fijo 150–450 operaciones desde 01/10 o 23/10). La comparación holdout vs anterior no se puede hacer hasta que el conteo junte su N.
