# Cartera viva — el centro de EdgeLab

Estado: VIGENTE. Fecha: 2026-10-31. Decisión de Nico (sesión en la nube, 31-oct): «el agente del Debian tiene que ser quien mantenga
nuestras canastas actualizadas al régimen». Referente: `docs/NORTH_STAR.md` (cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`).

## 1. La idea
El objetivo es ganar dinero en prop firms, Axi Select y capital propio. Los edges que EdgeLab encuentra son **de régimen**: funcionan
un tiempo y después dejan de funcionar. Por eso la unidad de trabajo no es "una estrategia confirmada para siempre" sino una
**cartera viva**: un grupo de estrategias que probablemente funcionan AHORA, que se reorganiza todos los días según el régimen del
mercado y según lo que cada una viene rindiendo, y que se renueva con estrategias nuevas a medida que las viejas se apagan.

El agente del Debian es el dueño de esa cartera. Todos los días, después del cierre de CME:
1. recibe el rendimiento forward de cada estrategia (papel simulado con el motor congelado, fills de demo y de cuentas reales);
2. retira en el acto lo que dejó de funcionar;
3. estima el régimen de mañana, por instrumento, con datos hasta hoy;
4. ajusta cuánto pesa cada estrategia según cómo rinde en ese régimen;
5. reparte el riesgo de cada cuenta dentro de sus reglas;
6. arma la cola de investigación con plazos para cubrir los huecos del régimen actual;
7. deja el plan del día antes de la apertura asiática y avisa en la sala lo urgente.

## 2. Urgencia, con límites
- **Todos los días.** El ciclo corre a las 17:12 ET (`deploy/debian/edgelab-cartera.timer`) y tiene que terminar antes de las 17:57.
- **Rápido para cortar y lento para sumar.** Retirar es inmediato y automático. Sumar riesgo exige evidencia acumulada.
- **Rápido para empezar a medir.** Una estrategia entra en PAPEL apenas tiene un pre-registro committeado. El papel no arriesga
  capital, así que no hay motivo para esperar.
- **Si algo falla, nadie opera a ciegas.** Un error o un ciclo fuera de plazo genera el plan en MODO SEGURO (cero contratos en todas
  las cuentas) y una alerta. Quedarse afuera nunca rompe una regla de prop firm.
- **Mirar todos los días es válido.** El seguimiento usa e-procesos (`funnel/secuencial.py`). Por la desigualdad de Ville, mirar
  todos los días no infla el error, cosa que sí haría un p-valor clásico.

## 3. Ciclo de vida de una estrategia (`edgelab/cartera/ficha.py`)
| Nivel o estado | Cómo se llega | Qué hace |
|---|---|---|
| **PAPEL** | Regla congelada con pre-registro committeado: confirmada por el embudo, canasta de pistas vivas con prueba forward o variante nominada. Al entrar se abre su ventana forward en el libro de ventanas (una por familia). | Se mide todos los días con el motor de siempre. Opera en la cuenta DEMO. |
| **REAL** | E-proceso de edge ≥ 1/`alfa_real` con al menos `min_ops_real` operaciones forward, o confirmada por el embudo con acta. | Puede recibir contratos en cuentas reales **habilitadas por una persona**. |
| **suspendida (por día)** | El régimen de mañana le da afinidad 0. | No opera mañana, pero sigue en papel y no se retira. |
| **RETIRADA** | Futilidad del e-proceso, cota estructural violada o drawdown forward > `dd_max_r` × pérdida máxima. | Sale en el acto. La misma regla congelada no vuelve sin otra confirmación en datos nuevos. |

## 4. Régimen y afinidad (`regimen.py`, `afinidad.py`)
- **Régimen de mañana por instrumento**, sólo con cierres hasta hoy:
  - volatilidad: BAJA, MEDIA o ALTA según el rango de 5 días contra el de 60, con cortes congelados una vez sobre desarrollo;
  - dirección: ALCISTA, BAJISTA o RANGO según el t de Newey-West de los retornos de 20 días. Es la t sobre retornos, nunca la de una
    regresión en niveles.
- **Afinidad** = media de la estrategia en ese régimen, contraída hacia su media global (K = 20 días), dividida por la media global,
  recortada a [0, 2]. Pocos días en un régimen no alcanzan para creerle. Un régimen nunca visto da afinidad 1.

## 5. Riesgo por cuenta (`asignacion.py`)
- **Presupuesto del día** = mínimo entre (fracción × límite de pérdida diaria) y (fracción × distancia al piso de drawdown). Si todas
  las posiciones pierden su máximo el mismo día, la cuenta no llega al piso.
- **Pesos**: riesgo igual × afinidad, con topes por estrategia y por instrumento (`funnel/canasta.py`, reutilizado).
- **Contratos** = piso(presupuesto × peso / (pérdida máxima estructural × USD por punto)). Micro por defecto, y nunca más que el
  máximo de contratos de la firma.
- **Elegibilidad de cuentas:**
  - una firma que prohíbe algoritmos no recibe posiciones automáticas;
  - una cuenta real sólo recibe estrategias REAL, y sólo si una persona la habilitó.

## 6. Investigación con plazos (`investigacion.py`)
| Prioridad | Plazo | Disparador | Acción |
|---|---|---|---|
| P0 | hoy | Retiro del día | Reemplazar |
| P0 | hoy | Hueco de régimen: un instrumento con menos de `objetivo_por_instrumento` estrategias con afinidad > 0 para mañana | Buscar en ese instrumento y régimen |
| P1 | 24 h | Familias en PISTAS_VIVAS con réplica a favor | Pre-registrar su prueba forward y darlas de alta en PAPEL |
| P1 | 24 h | Campañas bloqueadas | Destrabar |
| P2 | semana | Estrategias en PAPEL cerca de promoción | Preparar su ejecución en demo NT8 |

El agente del Debian lee la cola del plan (directiva 8) para decidir qué lanzar. Las familias nuevas siguen siendo chicas, de cientos
de celdas: la falta de potencia de las grillas de 10⁶ celdas está medida.

## 7. Qué es automático y qué es humano
| Automático (agente) | Humano (Nico / Gonza) |
|---|---|
| Alta en PAPEL con pre-registro; seguimiento; retiros; promoción a REAL por e-proceso; régimen; pesos; contratos; cola; alertas | Habilitar cuentas reales y sus montos; cambiar `alfa_real`, `min_ops_real` y `dd_max_r` (son compuertas); verificar las reglas de Axi Select; operar con dinero real |

## 8. Lo que falta para que el ciclo corra completo (en orden)
1. **Datos nuevos de futuros todos los días: resuelto el 2026-11-01, falta instalarlo en la PC de Nico.**
   - SV1 usa Kaggle: `"motor": "kaggle"` y `edgelab/cartera/motor_kaggle.py`. El papel corre como ANALIZAR_REGLA sellado, con el
     pre-registro de la ficha como acta. El régimen corre como DIARIO: el desarrollo una vez, en caché, y desde el 2026-10-01 sobre el
     dataset sellado.
   - Los ticks los graba NT8 en vivo y se suben cada día al dataset sellado (`docs/infra/LOGGER_NT8_DIARIO.md`).
   - PRERANGE-ZONAS-NQ no puede seguirse en Kaggle sellado: sus almacenes de zonas cubren sólo el desarrollo. Queda sin seguimiento,
     informado en el plan, hasta que exista el cálculo de zonas sobre el sellado.
2. **Cortes de régimen congelados** por instrumento: `python tools/cartera_diaria.py cortes --config ... --instrumento NQ`. Con el
   motor de Kaggle lanza un kernel DIARIO de desarrollo, hasta el 2026-03-31. Después se copian a `cortes_regimen` en
   `/etc/edgelab/cartera.json`. El bug del 2026-11-01 (un futuro en los cortes mandaba el ciclo a MODO SEGURO) está corregido: el
   régimen tiene su propia acta (`__regimen__`) y un instrumento sin datos queda con afinidad neutra.
3. **Reconciliar SV1 y actualizarlo** (pendiente de Gonza). Después, `install.sh` instala `edgelab-cartera.timer` y su configuración.
4. **Primeras altas en PAPEL**:
   - las reglas de la canasta de 7, después de su holdout;
   - la canasta forward de ASIA-NQ. Hoy una ficha sigue una sola celda; para una canasta de 20 pistas hay que dar de alta las 20 o
     extender la ficha a multicelda;
   - lo que salga de las campañas del 31-oct.
   - **Hecho (2026-11-01, OK de Nico):** cuatro canastas declaradas en `config/cartera/altas.json` (RANGO0100-NQ, PRERANGE-ZONAS-NQ,
     OTR930-NQ y ASIA-NQ). Las fichas ya admiten multicelda (`regla.celdas`, una observación por sesión). El ciclo las da de alta solo
     en su primera corrida. Pre-registro: `docs/research/cartera_20261101/PREREGISTRO_FORWARD_CANASTAS_PAPEL_20261101.md`.
5. **Demo NT8.** Para ejecutar en demo cada estrategia necesita su versión NinjaScript con paridad. Mientras tanto, la cuenta DEMO del
   plan es papel simulado. Los fills reales, cuando existan, entran por `fills.jsonl` y el plan reporta la brecha ejecución − papel.

## 9. Archivos
- `edgelab/cartera/`: `regimen`, `afinidad`, `ficha`, `asignacion`, `investigacion`, `papel`, `ciclo`.
- `tools/cartera_diaria.py`, `config/cartera/cartera.json`, `deploy/debian/edgelab-cartera.{service,timer}`.
- Tests: `tests/research/test_cartera_viva.py`.
