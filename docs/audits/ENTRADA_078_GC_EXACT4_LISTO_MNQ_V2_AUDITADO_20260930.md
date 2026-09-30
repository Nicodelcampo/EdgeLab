# Entrada078 — nube → Claude/Nico: exact4 GC implementado y MNQ V2 auditado

Continúa077, con dos novedades: Nico entregó V2 y controlGC. Fuente de entrada es reporte local de Nico + ZIP; no permiso financiero. Resolver HEAD actual; blobs exactos de la entrega se consultan en commit nuevo.

## MNQ

Acta `docs/research/RESULTADO_MNQ_L2_V2_PRIMERA_SESION_TARGETFREE_20260930.md`, evidencia `artifacts/mnq_l2_v2_first_session_20260930/evidence_aggregate.json`. HashesCRLF exactos,19.569velas/31señales igualesV1+replay, fronteras de publicación en metadata PASS. Raw MNQ no aquí: no rehash independiente de parquets ni fills certificados.

26observables/6true compatibles ANTES del extremo,17/1 al publicar grupo del extremo,4/1 al confirmar; mismo31denominador.685velas bootstrap+14incompletas explican699ausencias. Candidato historia-de-pico AL CONFIRMAR; no retrotraer entrada al pico ni cambiar máscara original que sigue1true. No repetir primera sesión; no52automático/outcomes.

## GC

Control reportado: `GC_04-26_202602_25T_HFT__nq__n4__precio`, ×3,51,1.459zonas reportadas no recontadas. Parámetros efectivos corroborados por fuente: w1,gap30,step49,pull25,nmin4,conf28,sentinel-dmax1M,total/stepmin0. Bundle/hash privado aún pendiente.

**Exact4 YA IMPLEMENTADO en nube, no en visor local aún.** `tools/escalonadas_exact4.py`, `tools/gc_exact4_variants.py`, `tools/gc_exact4_prepare.py`,26tests. No necesita queClaude reimplemente la regla. Cinco perfiles numéricos en `artifacts/gc_exact4_preparation_20260930/gc_resolved_profiles.json`; reporte y límites de smoke0enGC `docs/research/PREPARACION_GC_ESCALONADAS_EXACT4_20260930.md`.

Handoff mínimo `docs/research/HANDOFF_LOCAL_GC_EXACT4_CODIGO_LISTO_20260930.md`: tests, capturar bundle/meta/hash, adapter/censo MISMAS barrasGC con perfilactual, devolver a nube. Integración canónica del visor todavía pendiente. C0 con detector original, no sustituto; sin backfill/crecimiento exact4, sin rescate5º ni veto futuro.

## Restricciones

GCejemplos mayo/junio con grano150 son smoke, no febrero25T/control actual. No trasladar frecuencias/potencia entre ellos. Confirmar cantidad útil yclusters por día antes de economía. Nada de raw/precios/Lucid repo, nada de retornos/costos/MAE/MFE/fills nuevos sin manifiesto+OK; forwardoct+intacto.

## Aporte al referente

Exact4 y variantes están listos para QA sobre la población correcta, y V2 identifica historia L2 mucho más observable sin demostrar edge todavía.
