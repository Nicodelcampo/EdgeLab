# Integración desde la información existente en EdgeLab

## Fuentes inspeccionadas

Main ab9a0540c43ad7f68a015a9f22892633a555cd6d: bridge/bars.py (1b32435a1aea9ab2b64688156eadfe79cdbe61c4), bridge/sessions.py (491211fd2720087bb8e21c86f7faae572ba66606), bridge/session_preflight.py (34b1386f55b35ecf1b2d113ef6c69217bd4dd5b3), bridge/cme_hours.py (612f1de5057f5702a402bb31ecca003dee5bef5d), bridge/universe.py (019698c563acfe0ef0f59e4413e4c809d4dad818), kaggle/sessions_cme.py (57c5d24faa9a048b5ae2d325078af526d645dbe4), data/contract_regime.py (a89827c30bb6ce6022ffa810b14247cefb2bafdc). También ambos planes Markdown de infraestructura/remediación exportados en la raíz. Son antecedentes metodológicos, no permisos para abrir períodos reservados ni certificados nuevos.

## Cambios ejecutados

Nuevo make_shadow_reader: calendario explícito hasheado, admisión completa antes del callback de fuente, ticks trade canónicos y orden original; barras [inicio,fin), etiqueta al cierre, sin ffill. Cierre de barra exactamente igual al cierre de sesión conserva ESA sesión; no se llama session_end_ns sobre ese cierre para saltar al siguiente. Exige calendario verificado y rechaza fechas/intervalos incompatibles o reservados. Cuenta huecos sin transformar falta de datos en actividad cero ni certificado de completitud.

La salida del reader se conecta a run_verified_shadow. La prueba conectada usa aprobaciones/gate MOCK sintéticos: demuestra el cableado y el bloqueo antes de lectura, NO la certificación de un dataset. El modo actual separa/censura cada sesión; NO reivindica equivalencia con un chart NT8 continuo a través de fronteras o datos faltantes. Los estados no resueltos no se cierran retrospectivamente.

Nuevo first_quote_fill: referencia independiente para orden horaria y primer tick ejecutable posterior a la información observable. Compra ask / venta bid, lado inverso en salida; presupuesto de tardanza obligatorio. Si falta tick en plazo: DATA_INCOMPLETE, nunca último tick anterior. No agrega TP/SL, no calcula PnL, no verifica fills broker. Es un componente separado; aún no un ledger completo de 60 lotes con netting/rechazos/partials.

## Lo que NO puede heredarse

universe.py usa fechas históricas medidas por volumen del día y día calendario; contract_regime.py actual exige sesión CME D-1 completa. No copiar el mismo desde al manifiesto causal. El texto antiguo declara faltantes MNQ 06-26/09-26, pero pertenece a otra extracción: contrastar con los nuevos archivos, no perpetuar automáticamente el bloqueo ni asumirlo resuelto.

El volumen histórico MNQ 03-26 citado para 2025-12-15 es 971821, contra 882925 observado en la sesión CME del dataset actual. La diferencia puede incluir definición de fecha/fuente; NO prueba corrupción por sí sola, pero impide reutilizar la evidencia como si fuera una certificación de la versión nueva.

sessions.py declara feriados no modelados; siete fronteras en HFTZones2/6E no certifican feriados, MNQ ni las órdenes de EdgeReplica. cme_hours.py cubre semana regular, no pausa diaria/feriados, y su helper reindexa sequence; una vista nueva debe preservar además identidad de origen. No alterar esos componentes históricos de paridad ni usar su loader pq.read_table como sustituto de lectura físicamente acotada antes del holdout.

## Validación y estado

52 tests EdgeReplica sintéticos PASS; 16 tests existentes de research_data_gate PASS, ejecutados separadamente. Compilación Python PASS. No se ejecutó una nueva prueba de mercado en esta etapa, ni se abrió holdout, ni se modificó el canónico de Kaggle. La QC previa de 103921542 filas sigue limitada a MNQ 03-26.

Estado: integración diagnóstica implementada; aplicación económica bloqueada hasta calendario/fuente/sesiones/roll D-1 actuales y prueba de ejecución completa. Los módulos nuevos no emiten aprobaciones, SANITIZED_VERIFIED ni PROMOTED. La suficiencia del repo para convenciones/código no debe confundirse con disponer de todos los certificados o una traza broker específica.

Reproducir: python3 -m unittest discover -s tests -p 'test_edge_replica*.py' -q
