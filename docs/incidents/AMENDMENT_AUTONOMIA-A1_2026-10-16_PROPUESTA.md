# Enmienda AUTONOMIA-A1 — delegación de la promoción al agente — PROPUESTA (firmada en chat, pendiente de commit en NORTH_STAR)

Estado: PROPUESTA. **Firmada y aprobada por Nico en el chat el 2026-10-16** ("firmo, apruebo y mergea"): `docs/DECISIONES_20261016.md`. Sigue sin efecto en el código hasta que Nico commitee el texto en `docs/NORTH_STAR.md` (condición (d): el agente no puede tocar ese documento). Redactada por gonzasib-claude el 2026-10-16 a pedido de Nico ("la idea del sistema es que la promoción humana no sea necesaria"; "sí"). **No tiene efecto hasta que Nico la commitee como propia y agregue el texto a `docs/NORTH_STAR.md`**, refrescando la autocita del hash y `tests/test_north_star_hash.py`. Base: `docs/research/AGENTE_ESPIRAL_20261004.md` §8.3.

## Texto propuesto para `docs/NORTH_STAR.md`

> **Enmienda AUTONOMIA-A1 (2026-10-16) — Delegación al agente de investigación.** La promoción de candidatas a corrida y las decisiones de G0–G4 se delegan al agente (`edgelab/autopilot`, versión y commit citados en cada manifiesto), sin aprobación humana caso por caso, bajo condiciones no negociables:
> (a) el perímetro está en código y cubierto por tests: guardas de holdout, pre-registro committeado **antes** del lanzamiento, configuración textual en el pre-registro, archivos protegidos por hash, alpha-investing y conteo global de pruebas antes de lanzar;
> (b) ninguna salida de un LLM es evidencia. El revisor que aprueba es un modelo distinto, en sesión distinta del proponente, y sólo ve métricas públicas;
> (c) el número de pruebas se cuenta acumulado de por vida, y la riqueza de alfa es finita: sin réplicas confirmadas, el agente deja de lanzar;
> (d) el agente **no puede** modificar guardas, FDR, holdout, mandato, archivos protegidos ni este documento. Esos cambios siguen requiriendo decisión explícita del responsable;
> (e) un hallazgo del agente es exploratorio hasta replicarse en datos no usados. Operar con capital real requiere una autorización separada.
> Esta enmienda no mueve ninguna frontera de holdout.

## Qué habilita en el código

- `config["auto_promocion"] = true` en la configuración de SV1 (por defecto `false`).
- `python tools/autopilot_generate.py auto-promote --candidates /etc/edgelab/candidates.json` (timer diario): `edgelab/autopilot/promocion.py`.

## Qué no habilita

- Cambiar el modo a `execute` (lo hace el responsable una sola vez en la configuración).
- Abrir el holdout, calcular P&L sin manifiesto ni promover estrategias a cuentas.
