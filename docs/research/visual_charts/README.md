# Clasificación de Artefactos Visuales: visual_charts

> [!WARNING]
> **SUPERSEDED_NON_CAUSAL_VISUAL_ARTIFACT: VIEWPORT_DEPENDENCY_AND_NON_CAUSAL_VREF_DEFECTS**
>
> Los archivos PNG contenidos inicialmente en esta carpeta (`HP007_VISUAL_SESS_*.png`) fueron generados bajo la implementación preliminar de `tools/generate_visual_inspection_charts.py`.
>
> **Defectos confirmados en los artefactos iniciales:**
> 1. Las zonas se dibujaban extendidas horizontalmente a lo largo de toda la sesión sin corte as-of en $t_{\text{ref}}$.
> 2. No se fijaba un instante de evaluación $t_{\text{ref}}$ explícito.
> 3. No se filtraba por `available_ts <= tRef`.
> 4. El perfil lateral $F(p)$ se evaluaba incorporando zonas posteriores al tiempo visible o analizado.
> 5. El normalizador $V_{\text{ref}}$ utilizaba la mediana de todas las zonas de la sesión (información futura).
>
> **Estado de estos archivos:**
> Se conservan como evidencia histórica y trazabilidad del proceso de diseño visual target-free.
> Han sido superados por la versión causal e invariante regenerada en la Fase H.
