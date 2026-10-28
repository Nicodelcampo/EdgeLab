# Directivas de Nico para el agente del Debian (vigentes; las lee cada rol en cada ciclo)

Detalle y contexto: docs/research/MENSAJES_AL_AGENTE_DEBIAN.md (lo más nuevo, arriba).

1. Arreglate solo: monitoreá el proyecto y a vos mismo en cada ciclo (campañas BLOQUEADA o con fallas, unidades en failed, estado sin
   publicar, CI rojo); causa raíz, arreglo con test, desbloqueo de la misma etapa, y registro en ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md.
2. Pensá fuera del molde: proponé y mejorá por iniciativa propia los análisis, tus herramientas y tu proceso, sin romper la estructura.
3. Trabajá en espiral: medir → aprender (docs/research/APRENDIZAJES_ESPIRAL.md) → investigar afuera (Internet: inspiración, nunca
   evidencia) → proponer → correr → mejorarte → contar en la sala.
4. Usá las dos cuentas de Kaggle (nicolasbuttaro y nicobuttaro) para las corridas: repartí los lanzamientos ("cuenta_kaggle": "auto")
   y, si una está llena o falla, usá la otra; medí y reportá cuánto se usa cada una.
5. Estructura que no se rompe: nada se elige mirando el holdout; todo se pre-registra y se cuenta antes de correr (contador global,
   LORD++); nunca se relaja un criterio después de ver resultados; lo refinado con datos ya mirados se confirma con datos nuevos;
   cambiar gates/FDR/mandato/archivos protegidos sigue CLAUDE.md; no se opera con dinero real.
6. Holdout global desde el 30-sep (apertura `2026-09-30 22:00 UTC` = sesión CME `20261001`) y canasta de régimen: aplica a todos los
   agentes, todos los activos y todo el proyecto. Ninguna campaña cuyo desarrollo/OOS cerró el 2026-09-30 debe usar `holdout.desde: 20261023`.
   Dado que los edges operables son de régimen, no se espera años a acumular un `n_fijo` individual gigante: el riesgo se diversifica en una
   canasta de estrategias de régimen y cada candidata se confirma para la canasta si su rendimiento en la ventana reducida de holdout
   disponible está dentro de la desviación esperada según su distribución en desarrollo/OOS.
