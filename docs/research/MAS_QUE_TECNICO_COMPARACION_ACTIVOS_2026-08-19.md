# Más allá de lo técnico — comparación de activos (idea, 2026-08-19)

**Disparador:** video PEAD + Zacks. A Nico le interesa el **enfoque**, no
la estrategia concreta: decisiones que vienen de comparar activos entre sí
o de eventos, no solo de la forma del precio.

**Estado:** idea documentada. **No es una campaña.** Todo lo de abajo,
si entra, entra como familia nueva con estimando escrito ANTES de medir
(misma regla que H-ASIA-1). No toca H-Z2A, v2, F4 ni el holdout.

## Lo que el video hace bien (y vale copiar como método)

1. La regla sale de un paper (Bernard & Thomas 1989), no del gráfico.
   3 reglas, sin optimización: sorpresa → confirmación de precio →
   salida a tiempo fijo (60 días hábiles).
2. Cruza dos operaciones a mano contra TradingView antes de correr 20 acciones.
3. **Trampas que el propio video nombra de pasada y hay que leer:**
   658 eventos en 20 acciones se agrupan por fecha de balance (la N
   efectiva se achica — es P-47 otra vez); supervivencia (20 vivas);
   datos gratis scrapeados sin auditar el consenso.

## El menú (lo que se usa institucionalmente, con respaldo)

| Familia | Estimando | Horizonte | ¿Proyecto? |
|---|---|---|---|
| **TSMOM / trend** (Moskowitz–Ooi–Pedersen 2012; 58 futuros, 25 años) | signo del retorno 12 m predice el próximo | meses | **Sí** — los activos del store (6E/6J/YM) están en el universo del paper |
| **Carry** (Koijen–Moskowitz–Pedersen–Vrugt 2013) | diferencial de tasas / pendiente de curva | semanas-meses | **Sí en FX** (6E, 6J). Es THE comparación de activos: ordenás por carry |
| **Cross-sectional momentum** | rankear activos entre sí, long ganadores / short perdedores | semanas-meses | **Sí** — es literalmente "comparar activos" |
| **Pre-FOMC drift** (Lucca–Moench 2015, JoF; Kurov 2020) | retorno 14:00 día previo → anuncio | **horas** | **Sí** — índices (YM) y encaja con datos de tick propios |
| **Macro-release drift** (NFP, CPI) | sorpresa vs consenso → derrape | horas-días | **Sí** — es PEAD para futuros: la "sorpresa" es macro, no de balance |
| **Calendario** (turn-of-month, día de semana) | estacionalidad sistemática | días | Sí, débil; mucha literatura mala, exige presupuesto de multiplicidad |
| **PEAD** (Ball–Brown 1968; Bernard–Thomas 1989; Fink 2021: 224 papers) | sorpresa de EPS → drift 60 días | semanas | No directo — es acciones, necesita dataset de earnings |
| **Basis / basis-momentum** (Boons–Prado 2019) | roll yield, curva | semanas | Parcial — necesita cadena de contratos, no solo el continuo |

## Lectura para Nico

Lo que todas comparten y ninguna técnica tiene: **un "por qué" económico
escrito** (prima de riesgo, atención limitada, reacción lenta) y un
**evento o ranking** que ordena activos. Eso responde la pregunta "¿qué
activo miro hoy?" que la microestructura no contesta.

División de trabajo natural, no un reemplazo:

- **Lenta (comparación de activos):** carry, TSMOM, macro-drift → eligen
  QUÉ y CUÁNDO (dirección, día, instrumento).
- **Rápida (la tuya):** H-Z2A, H-ASIA-1 → miden CÓMO se comporta el precio
  ahí (costo de pasaje, absorción, corredores).

Las dos se conectan en un solo punto honesto: usar la lenta para elegir
eventos y la rápida para medir la ejecución, nunca para "confirmar" la
lenta con la rápida después de verla (eso sería mirar el resultado).

## Candidatas concretas si algún día entra

1. **Calendario macro en YM/6E:** drift en ventanas FOMC/CPI/NFP. Barato:
   los datos ya están; el estimando es una ventana horaria.
2. **Carry FX 6E vs 6J:** ordenar por diferencial de tasas y medir si el
   ranking predice la dirección del día. Un join contra tasas, nada más.
3. **PEAD propiamente:** fuera de alcance salvo que se compre/scrapee un
   dataset de earnings (Zacks gratis, calidad sin auditar).

Cualquiera arranca igual: protocolo escrito (confundidor incluido) →
STOP de Nico → medir. No antes.

**Aporte al referente:** la pregunta "qué activo hoy" no la responde la
forma del precio; la responden prima de riesgo, evento o ranking.
