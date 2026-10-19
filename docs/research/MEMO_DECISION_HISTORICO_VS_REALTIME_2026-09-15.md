# Memo de Decisión Técnica: Semántica de Consumo Histórico vs Realtime

> **Fecha:** 2026-09-15  
> **Destinatario:** Nico / Equipo EdgeLab  
> **Objeto:** `HFTClusterZonesNQ.cs` (v2.0.0) y su espejo Python (`edgelab/bridge/indicators/hftclusterzones.py`)  
> **Referente rector:** `docs/NORTH_STAR.md` (Jerarquía de objetivos: Ejecutabilidad Real y Validez Causal > Paridad de Conveniencia)  
> **Estado:** PROPUESTA TÉCNICA - NO APLICADA EN CÓDIGO A LA ESPERA DE DECISIÓN FORMAL

---

## 1. El Defecto Técnico Diagnosticado

En el indicador actual `HFTClusterZonesNQ.cs` (v2.0.0), el consumo de liquidez de un cluster ocurre en dos métodos:
1. `ActualizarConsumoTick` (ejecutado en cada tick de la sub-serie `BarsInProgress == 1`).
2. `ActualizarConsumoBarra` (ejecutado al cierre de la barra primaria `BarsInProgress == 0`).

La desconexión ocurre en las líneas 769-771 del `.cs`:
```csharp
// ActualizarConsumoBarra
if (State == State.Realtime && BarsArray.Length > 1 && CurrentBars[1] > 0)
    return;
```

### Consecuencia Causal:
- **En tiempo real (`State == State.Realtime`):** El método detecta que está en vivo y que existe la serie de ticks, por lo que retorna temprano. El cluster es consumido **una sola vez**, tick a tick.
- **En reproducción histórica (`State == State.Historical`):** Como `State != State.Realtime`, la guarda se saltea. El cluster suma los ticks individualmente Y ADEMÁS suma el volumen total de la barra al cierre de la misma.
- **Resultado:** En histórico, todo contrato comerciado dentro del cluster se computa **dos veces**. El cluster alcanza el estado `Depleted` al doble de velocidad que en el mercado real.

---

## 2. Las Dos Alternativas

### Alternativa A: Realtime como Semántica Canónica (Recomendada)
* **Acción:** Modificar la guarda en el `.cs` eliminando la condición `State == State.Realtime`:
  ```csharp
  if (BarsArray.Length > 1 && CurrentBars[1] > 0)
      return;
  ```
* **Ventajas:**
  1. **Alineación física y causal:** Un contrato negociado en CME es un evento singular. No existen 2 contratos negociados por cada tick real.
  2. **Transferibilidad a Live Trading (North Star #1 y #4):** Si una estrategia se optimiza sobre el régimen histórico de doble conteo, en vivo experimentará un cluster con el doble de persistencia y capacidad de absorción, invalidando el dimensionamiento de posición, el tiempo de vida esperado y las salidas por agotamiento.
  3. **Unificación de objeto:** El objeto histórico y el objeto en vivo pasan a ser exactamente el mismo ente matemático.
* **Trade-off:** Requiere re-exportar oráculos previos si se desea comparar contra corridas antiguas que asumieron doble conteo.

### Alternativa B: Mantener Doble Conteo Histórico
* **Acción:** No modificar el `.cs`. Dejar documentado en los manifiestos que histórico y en vivo son dos objetos divergentes (`historical_realtime_semantics = DIVERGENT`).
* **Ventajas:** Compatibilidad retroactiva con oráculos históricos ya exportados.
* **Riesgos Críticos:**
  1. Fragilidad epistemológica: Se certifica paridad sobre un artefacto del motor que no existe en el mercado.
  2. Ruptura de paper/live: El edge no será replicable en producción sin reimplementar artificialmente el doble conteo en vivo.

---

## 3. Recomendación Formal de Antigravity

Conforme a `docs/NORTH_STAR.md` (la paridad es un medio, no el fin; el fin es encontrar edges netos, robustos y ejecutables en cuentas de trading reales), **recomendamos adoptar la Alternativa A**:

1. Mantener hoy el `.cs` intacto para registrar la línea base v2.0.0 actual con su manifiesto explícito.
2. Una vez confirmado por Nico, aplicar la modificación en `HFTClusterZonesNQ.cs` (generando v2.1.0 unificada).
3. Ajustar el switch `consumo_por_barra = False` en el arnés de paridad Python.
4. Correr la certificación final sobre la semántica unificada.

---

> **Aporte al referente:** Evita optimizar estrategias sobre un artefacto de doble conteo y establece la hoja de ruta para que el backtest represente fidedignamente la microestructura en vivo.
