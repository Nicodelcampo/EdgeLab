# Pre-registro: prueba forward de la canasta congelada de ASIA-NQ (20 pistas)

Estado: VIGENTE (pre-registro; nada de la ventana se miró). Fecha: 2026-10-31. Pedido de Nico en la sesión en la nube.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa del embudo: EF5 (confirmación). Familia: `ASIA_BOS_GAPS_NQ` (campaña `ASIA-NQ`, `docs/research/asia_bos_20261029/embudo/ASIA-NQ/`).

## Por qué
La réplica OOS (2026-04-01..2026-09-25) de las 20 pistas congeladas dio veredicto `SIN_RECHAZO`: 20 de 20 pistas con media neta
positiva, canasta +4,38 pts por sesión, IC90 [−0,33; 8,82], p 0,053, 102 sesiones (nivel del paso 0,0109, sin rechazo). Es la
familia nueva con la réplica más clara a favor. `escalera.veredicto_pistas` declara que tras `SIN_RECHAZO` "el próximo paso es el
holdout de la canasta congelada", pero el embudo no tiene esa etapa: la familia quedó en `PISTAS_VIVAS` sin prueba posterior. Este
documento la define a mano, sin tocar el embudo.

## Objeto (congelado, sin cambios)
- Las 20 celdas de `pistas_replica.celdas` del `estado.json` de ASIA-NQ (mismo orden), con el código de `edgelab/research/asia_bos_gaps.py`
  y la configuración de la campaña `config/autopilot/grillas/campanas/ASIA-NQ.json`, al commit de este pre-registro.
- Cortes congelados del DESC (`cortes` del `estado.json`). Fricción canónica de NQ (`edgelab/costos.py`). Sin tope adicional,
  sin filtros, sin pesos: nada se elige después.
- Estimador: `edgelab.funnel.escalera.canasta_pistas` (P&L neto medio por pista y sesión, una serie; las pistas sin operación en la
  sesión aportan 0). Mismo estimador que dio el resultado de la réplica.
- **No** se usan las "canastas ortogonales" ASIA-NQ [2, 8, 5] del reporte del 2026-10-29: se eligieron mirando el OOS.

## Ventana
- Sesiones CME con fecha de sesión **>= 2026-11-02**, hacia adelante (datos forward, no existen todavía).
- **Octubre (2026-10-01..2026-10-30) queda excluido** aunque esté sellado: el reporte "Iteración V2" del 2026-10-29 afirma haber
  evaluado ASIA-NQ sobre "Holdout v3 (2026-10-01..2026-10-29)". La revisión de Gonza (`REVISION_SV1_20261030.md`, A2.1) concluye que
  esa tabla es sintética, pero no se puede descartar que alguien haya visto octubre real de esta familia. Ante la duda, no se usa.
- Una sola ventana por familia: queda registrada como consumida para `ASIA_BOS_GAPS_NQ` desde 2026-11-02.

## Prueba principal
- t unilateral de la media de la canasta por sesión (bootstrap por sesiones de `resumen_sesiones` como respaldo del p), con
  revisiones a **60, 120, 180 y 260 sesiones** con datos válidos.
- α = nivel LORD++ reservado para esta prueba en `docs/research/LIBRO_LORD.json` (reserva `ASIA-NQ/forward_canasta`, nivel
  0,0018859). Límites tipo O'Brien-Fleming (simulados, 2 M caminos, semilla 7): **t >= 6,062 / 4,286 / 3,500 / 2,912**.
- **CONFIRMADA** si en alguna revisión t supera su límite y la media > 0. Al confirmar se resuelve la reserva con ese p.
- **REFUTADA** si en la revisión de 120 sesiones o después la media es <= 0 (con 120 sesiones hay potencia ~0,8 para medio
  efecto del DESC con un intervalo que excluye ese efecto), o si al llegar a 260 no cruza el límite final.
- Desvío por sesión supuesto para la potencia: 28 pts (de la réplica: semiancho del IC90 4,57 × √102 / 1,645).
  Potencia: 0,35 si el efecto real es el de la réplica (4,38); 0,80 si es la mitad del DESC (6,49); 1,0 si es el del DESC (12,98).
  **Con el efecto de la réplica la prueba probablemente no concluya**: hay que leerlo así de antemano.

## Secundarios (no deciden)
Media y IC90 por pista, aporte máximo de una pista, frecuencia de sesiones con operación, peor día, comparación con la réplica.

## Cómo podría refutarse
Media de la canasta <= 0 con 120 sesiones o más, o no cruzar el límite a las 260. Justificación económica: la caja asiática
concentra órdenes que se liberan en la ruptura o el barrido del rango (ver `SPEC_ASIA_BOS_GAPS.md`); si el efecto fuera de selección
(maldición del ganador sobre 28.344 celdas evaluables), la media forward tiende a 0.

## Reglas
- Nadie mira resultados de la ventana fuera de las revisiones; quien corra la medición registra la apertura en el protocolo del
  holdout (`edgelab/autopilot/holdout_apertura.py`) antes de la primera revisión.
- No se cambia nada del objeto después de este commit. Un cambio de código que altere las operaciones invalida la prueba.
- Conteo en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (1 prueba, la canasta).
