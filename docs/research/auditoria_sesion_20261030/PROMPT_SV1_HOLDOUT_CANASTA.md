# Pedido para el Claude Code de SV1: holdout único de la canasta de 12 reglas
Autoriza Nico (dueño del repo), 2026-10-30. Se ejecuta UNA sola vez.

Reglas: no arranques ni despauses timers o servicios edgelab. No cambies gates, FDR ni mandato. No muestres credenciales. No imprimas resultados por regla ni por sesión antes del paso 5. Si algo no coincide con esto, frená y reportá sin abrir datos.

1. Sin tocar datos sellados, reportá commit actual, `git status` y si hay cambios locales. No descartes nada. Usá un worktree nuevo en origin/foundation/f0b-compatibility-probe (debe contener docs/research/canasta_12_20261030/PREREGISTRO.md). Para git como otro usuario, usá `git -c safe.directory=/opt/edgelab/EdgeLab`, sin cambiar la configuración global.
2. Leé PREREGISTRO.md y canasta_12.py. Ubicá la configuración sellada de `lectores_sellados`. Listá las 12 actas (cid, celda, tope, sha256 de cada acta). Reportá y ESPERÁ confirmación de Gonza antes de seguir.
3. Con confirmación, corré una vez, para cada regla, la REP sobre datos sellados desde 20261001 con LocalRunner y `acta_requerida=True`, usando la misma celda, cortes y tope (solo CVGAP-CFD-NQ, CVGAP-NQ y U1-ZONAS-AVCL-NQ con tope). Si una acta falta o una regla no tiene dato sellado, frená ANTES de calcular la canasta.
4. Usá como desvío de cada regla la tabla fija del anexo de PREREGISTRO.md: R = neto / desvío. No lo recalcules. Una regla sin operaciones en el holdout aporta 0, no frena. Sumá R por sesión y aplicá stop diario de -2 R recortando el total del día.
5. Evaluá: media por operación, t por sesión, drawdown en R y aporte máximo por regla. Veredicto: APRUEBA si media > 0, t >= 1,28, drawdown <= 10 R y aporte máximo <= 50 %; PAPEL si media > 0 sin lo anterior; NO APRUEBA si media <= 0.
6. Guardá el JSON del resultado y no vuelvas a correr nada aunque falle el criterio.

CONFIRMACION-HOLDOUT-CANASTA
commit_worktree:
sha256_preregistro:
sha256_canasta_12:
actas: cid + sha256 (12)
ruta_y_sha256_resultado:
sesiones / operaciones:
media / t / drawdown_R / aporte_max:
veredicto:
timers_edgelab_siguen_pausados: (salida de systemctl)
cambios_fuera_del_worktree:
pendiente:
FIN
