# Decisiones del 2026-10-25 — SV1, escalera_v1 y conductores del embudo

Estado: VIGENTE
Fecha: 2026-10-25. Decide: Nico («sí, hacé todo vos», en respuesta a la propuesta de Claude sobre el plan de Gonza para SV1).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. PR #127 (lente duplicada en el generador): mergeado
`tools/autopilot_generate.py` pasaba `lente` explícita además de la que ya devuelve `edgelab/autopilot/contexto.py::proponer`
(línea 90): `TypeError` en cada propuesta, así que SV1 no proponía nada desde el 20-10. Verificado contra el código; CI verde; merge
`1822b54f` a `foundation/f0b-compatibility-probe`.

## 2. `escalera_v1` en SV1: autorizada por Nico
Reemplaza Holm y el alpha-investing por la escalera aprobada el 2026-10-24 (`docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md`):
FDR q 0,10 sobre celdas evaluables para nominar, réplica en lote con un paso de LORD++ (libro único `docs/research/LIBRO_LORD.json`),
OOS que mata sólo con potencia, linaje como información. Se activa con `tools/autopilot_activar_escalera.py` (primero en copia,
después `--aplicar`). Es un cambio de reglas de validación: queda autorizado por esta decisión, no por el agente.

## 3. Un solo conductor por campaña; las campañas del embudo pasan a SV1 de a una
- Regla: nunca dos conductores sobre la misma campaña (relanzan el mismo kernel con estados distintos).
- Hoy las maneja Claude en la nube (`"conductor": "local"`): U1-ORO-GRILLA (TOPES), U1-ES-GRILLA y U1-YM-GRILLA (DESC), además de
  EXPZ-NQ/EXPZ-CFD (cerradas) y U1_CRUZADO.
- Traspaso por campaña, al terminar la etapa en curso: (1) Claude frena su conductor; (2) commitea el `estado.json` y lo integra en
  `foundation`; (3) cambia `"conductor": "debian"` en el JSON de la campaña en el mismo commit; (4) SV1 hace pull y la toma. Hasta el
  paso 3, SV1 no la toca; desde el paso 3, Claude no la toca.
- El estado de las campañas que maneja SV1 se escribe en `foundation`.
- Campañas nuevas (U1-6E-GRILLA, U1-ZONAS-*) nacen con `"debian"` una vez que SV1 corrió su primer ciclo bien.

## 4. Cupo de Kaggle
La cuenta de Kaggle es una sola (≈ 5 sesiones simultáneas). Mientras Claude tenga kernels corriendo, SV1 usa **3 en paralelo**
(no 4); cuando todo el embudo esté en SV1, 4. El tope diario de 1000 corridas queda.

## 5. Recursos de SV1
Programador apagado al principio (MemoryMax 4G y suite completa con numba en un Celeron con 7,6 GiB compartidos con producción); se
prende cuando se mida su consumo. Carpeta sellada `/var/lib/edgelab-datos/holdout_sellado` con dueño `edgelab`; las unidades nuevas
también en `edgelab-ops`.
