# Paquete para el agente del Debian — sesión del 2026-11-10

Estado: VIGENTE (2026-11-10). Para leer al configurar el Debian (SV1) y al arrancar el primer ciclo después de esta sesión.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 0. Antes que nada: que el Debian VEA este trabajo
El agente se sincroniza con `origin/foundation/f0b-compatibility-probe` (`edgelab/autopilot/sincronizador_ramas.py`). Todo lo de esta
sesión está en la rama `claude/vibrant-clarke-s9z6e2` (PR Nicodelcampo/EdgeLab#191), **35 commits adelante de foundation y 0 atrás**:
se integra con un fast-forward. Mientras no se integre, el agente del Debian no ve nada de lo que sigue (práctica 8 de
`PRACTICAS_DE_TRABAJO_20261110.md`). Al integrar:
1. `git fetch origin && git checkout foundation/f0b-compatibility-probe && git merge --ff-only origin/claude/vibrant-clarke-s9z6e2 && git push`.
2. Los archivos de estado vivo que esta sesión tocó (`docs/research/LIBRO_LORD.json`, `docs/research/LINAJES.jsonl`) los fusiona el
   sincronizador con los de `STATE_DIR` (append-only). Verificar después del primer ciclo que estén las entradas
   `HFT_RUPTURA::rep_no_defiende_20261110` (reserva de LORD++) y las familias `HFT_RUPTURA_OTROS` y `REBOTE_NIVEL_SESION`.
3. En el Debian: `.venv/bin/python tools/estado.py`, `.venv/bin/python tools/autopilot_protect.py check` (debe decir OK),
   `.venv/bin/python tools/agentes.py --write` (los presupuestos de contexto cambiaron) y
   `.venv/bin/python -m pytest tests/autopilot tests/research/test_banco_eventos.py tests/research/test_factores.py -q`.

## 1. Qué cambió en cómo piensa el agente (ya está en su núcleo de contexto)
- **Directivas 16–19** (`config/autopilot/DIRECTIVAS.md`): banco de eventos; efectos chicos y cuerdas profundas (personalidad);
  constructor además de lanzador (detectar errores, mejorar estructuras, re-medir); rasgos y generadores propios sin cupo (F9
  acotada: siguen pausados los indicadores de dibujo operables).
- **Lentes nuevas** (`edgelab/autopilot/contexto.py`): `cuerdas`, `mejorar_estructura`, `remedir` (esta entra al menos una vez cada
  cinco ciclos mientras haya candidatas).
- **Presupuestos de contexto** (`config/autopilot/AGENTES.json`): arquitecto 200.000, juez y auditor 140.000 caracteres.
- **Documentos nuevos en el núcleo:** `docs/research/BANCO_DE_EVENTOS.md` (todos), `docs/research/REMEDICIONES_CANDIDATAS.md`
  (diseño); ampliados: `METODO_DE_INVESTIGACION.md` (postura, pasos 8b y 9b), `PRACTICAS_DE_TRABAJO_20261110.md` (lecciones de la
  tarde), `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (K10–K22, O19, checklist D.12).
- **Consignas:** el revisor hace KILL a especificaciones del banco sin preflight o que reusen la mitad B, a rasgos propios sin
  contrato, a P&L con entrada límite medido con «tocó el precio» y a confirmaciones sin análisis congelado antes de la tabla.

## 2. Estructuras nuevas para usar (no reescribir)
| Qué | Dónde | Para qué |
|---|---|---|
| Banco de eventos | `edgelab/research/banco_eventos.py`, `python tools/banco_eventos.py` | muchas ideas sobre una tabla de eventos: A explora, B prueba k + 1; previas, estabilidad, real − control, nulo de selección |
| Re-mediciones | `docs/research/CAMBIOS_DE_MEDICION.jsonl`, `python tools/remediciones.py --write` | qué corridas viejas darían otro resultado con la medición de hoy (204 candidatas; verificar antes de relanzar) |
| Fills pasivos | `edgelab/research/fill_pasivo.py` | toda entrada con orden límite (modelo «atraviesa»; nulo de selección adversa ≈ −0,07 R) |
| Generador de niveles | `edgelab/research/niveles_sesion.py` | niveles de la sesión (reloj y pivote), «sin zonas» como parámetro, OP-1 |
| Guardas del lanzador HFT | `tools/hft_clusters_info.py` | `traer` rechaza código no vigente (aceptar sólo con justificación), slug sin «_», falla si el push no sale |

## 3. Qué está corriendo o pendiente (NO duplicar)
Lo lleva un chequeo agendado de esta sesión en la nube (próximo: 2026-11-11 00:01 UTC). El agente del Debian **no** debe relanzar ni
analizar estas corridas por su cuenta:
1. `hft-clusters-info-niveles-replica` → banco `REBOTE_NIVEL_SESION` (abr–sep). **Primero.**
2. `hft-clusters-info-ruptura-replica` (ya terminó) → `tools/confirmar_no_defiende.py`, una sola vez, resuelve la reserva de LORD++.
   **Después del 1.**
3. `hft-clusters-info-niveles-op-replica` → `tools/op1_niveles.py` (OP-1, desarrollo). **Después del 1.**
Pre-registros: `docs/research/hft_clusters_u1_20261110/PREREGISTRO_REBOTE_NIVEL.md`, `CONFIRMACION_NO_DEFIENDE.md`,
`PREREGISTRO_OP1.md`. Plan: `PLAN_OPERABLE_Y_CUERDAS.md`.

**Ventanas ya gastadas (no usar para elegir nada en estas familias):** DESC jul-2025 → mar-2026 de los clusters HFT en NQ, ES, RTY,
YM, 6E, 6B y GC (clusters chicos); abr → sep 2026 de NQ, ES, RTY, YM y GC para `HFT_RUPTURA` y `REBOTE_NIVEL_SESION`. Lo que queda
sin mirar para esta línea: el holdout (una apertura por familia, por protocolo) y el forward.

## 4. Qué se sabe hoy (para no redescubrirlo)
- **Pista viva principal:** donde hubo actividad HFT, el nivel de la sesión rebota MENOS que uno cualquiera (`F-HFT-ZONAS-NO-SON-SOPORTE`,
  `F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-B`: estable 4/5 en activos independientes, p 0,088); un nivel cualquiera rebota ≈ +0,08
  (`F-REBOTE-NIVEL-SESION`), del orden de la fricción.
- **No repetir:** rebote EN zonas HFT; contexto de otros clusters grandes; volumen, EMAs, expansión limpia como discriminantes de
  ruptura (ver `FACTORES_CON_VENTAJA.md`).
- **Debilitada:** el retroceso contra la sesión (p 0,24 con el nulo de selección; no aparece en otros activos).

## 5. Primeros ciclos sugeridos para el agente
1. Lente `remedir`: la primera familia de `REMEDICIONES_CANDIDATAS.md`, verificando en su carpeta que el cambio la alcanza.
2. OP-3 (veto HFT en estrategias de reversión existentes): listar en `FAMILIAS.md` las que tienen operaciones con instante de
   entrada y proponer la medición del veto en bruto.
3. Lente `mejorar_estructura`: banco con varios desenlaces por especificación (geometrías) y puente L2 para la indagación I3.
