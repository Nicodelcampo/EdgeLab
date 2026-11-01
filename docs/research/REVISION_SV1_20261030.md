# Revisión del agente de SV1, corridas de la nube y correcciones (2026-10-30)

Estado: VIGENTE. Autor: gonzasib-claude (Gonza-PC), a pedido de Nico en la sala #CHY0V3YBS.


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
2. **PR #156 — KALMAN-FADE** (familia nueva pre-registrada, 216 celdas, NQ).
3. **Libro de ventanas del holdout restaurado.** `docs/research/HOLDOUT_VENTANAS.jsonl` es append-only y el commit `de6c3ecf` (28-10, "Cosecha Olas 6-9") lo reescribió de 34 a 10 filas: se perdieron 27 registros de ventanas **consumidas** y **aperturas** (AREAS_EXP_1_CRUZADO, LUXIMB_FADE_VISOR, U1-ORO/ES/YM/ZONAS-ES/ZONAS-NQ, ZGAP-NQ-CANASTA…). Sin ellos la guarda `holdout_ventanas.problemas` dejaba reabrir ventanas ya consumidas. Se restauró la unión (41 filas, sin duplicados) desde `ba7c2351`.
4. **CI de foundation en verde de nuevo:** MODULES.md, HERRAMIENTAS.md e índice de docs regenerados; `Estado:` en el documento de arquitectura del 28-10; fecha de CURRENT.md.
