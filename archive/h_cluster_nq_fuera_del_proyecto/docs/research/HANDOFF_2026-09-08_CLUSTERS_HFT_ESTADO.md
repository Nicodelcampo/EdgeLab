# Handoff 2026-09-08 — familia H-CLUSTER-NQ, estado tras corrida de 65 sesiones

> Escrito para que **Claude** continúe directamente con el plan de investigación.
> Rama: `foundation/f0b-compatibility-probe`.
> Holdout 2026-07-01 → 2026-12-31: **intacto**.

---

## 1. Lo que se acaba de completar

La corrida de **65 sesiones de H2 con el escalón 5 incluido** finalizó con éxito en la madrugada del 2026-09-08.
Resultados consolidados en `data/nt8_oracles/rechazo_clusters_nq_65s.json` e informe en `docs/research/RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md`.

### Resumen de la corrida:
- **Sesiones procesadas:** 50 sesiones de NQ 06-26.
- **Contactos totales:** 1,026,840
- **Resueltos en borde:** 71,641
- **MDE alcanzado:** **0.0214** (alcanza el objetivo de ~0,025 necesario para decidir sobre el residuo previo de +0,03).
- **Contraste agregado:** **+0.0352** (borde: 0.3715 vs libre: 0.3363).
- **Escalón 5b (Hold-out >= 30 barras):** Contraste = **-0.0108** (borde n=22,408, libre n=264,910).

---

## 2. Lo que sigue en orden para Claude

Según el orden fijado en la sección 4 del plan original:

1. **Correr el escalón 3 (barrido de vigencia `max_age_bars`):**
   - Herramienta ya escrita: `tools/vigencia_clusters_nq.py`.
   - Es target-free, no gasta muestra.
   - Recordar que `max_age_bars` estaba congelado en 500 por omisión y el deep research lo califica como crítico.
2. **Bootstrap clusterizado por sesión:**
   - Reemplazar el supuesto `deff = 5` con bootstrap en bloque por sesión.
   - Utilizar `edgelab/stats/bootstrap_estacionario.py` con largo de bloque óptimo.
3. **Paridad de la capa de clusters:**
   - La capa de clusters aún no tiene oráculo comparado (sólo la capa de zonas la tiene).
4. **Respetar el STOP de P&L:**
   - No abrir P&L ni salidas económicas sin manifiesto previo aprobado por Nico.

---

**Aporte al referente:** entrega la corrida de potencia de 65 sesiones resuelta y documentada, y deja la posta explícita para que Claude continúe con el escalón 3 (vigencia) sin ambigüedad.
