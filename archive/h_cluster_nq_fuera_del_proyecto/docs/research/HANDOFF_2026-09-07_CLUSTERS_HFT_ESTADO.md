# Handoff 2026-09-07 — familia H-CLUSTER-NQ, estado al cierre de la jornada

> Escrito para retomar **sin acceso a la conversación**.
> Rama: `foundation/f0b-compatibility-probe`, último commit `31e839c`, pusheado.
> Holdout 2026-07-01 → 2026-12-31: **intacto**. Las herramientas lo rechazan por
> construcción.

---

## 1. Lo único que quedó a medias

**La corrida de 65 sesiones de H2 no se completó.** Se lanzó tres veces:

1. murió con `SyntaxError` (defecto mío de edición, corregido en `79ec2c1`);
2. se relanzó y la máquina se apagó accidentalmente;
3. se relanzó y se cortó a pedido de Nico, que llegó al 97 % de su límite de uso.

**No hay resultado parcial.** El runner acumula en memoria y escribe al final; no
escribió nada. El comando para retomarla, tal cual:

```
.venv\Scripts\python tools\rechazo_clusters_nq.py --sesiones 65 ^
    --desde "2026-03-23 22:00" ^
    --out data/nt8_oracles/rechazo_clusters_nq_65s.json
```

Toma del orden de **90 minutos**. Arranca el 23 de marzo porque `NQ 06-26` es front
month desde ~20 de marzo y su parquet cubre 2026-03-12 → 2026-06-18; 65 días hábiles
desde ahí terminan antes del firewall.

**Por qué 65 sesiones y no otra cifra:** el residuo medido de H2 es +0,03 y el MDE con
15 sesiones es 0,053. El MDE cae con √n, así que llevarlo a ~0,025 —la mitad del
residuo— exige aproximadamente esa cantidad. No es un número elegido: es el que hace
falta para decidir.

**Mejora recomendada antes de relanzar:** que el runner escriba resultados parciales por
sesión. Se perdieron tres corridas largas por no tenerlo.

## 2. Estado de la campaña

El registro completo, siempre actualizado, está en
**`docs/research/HFT_CLUSTERS_NQ_MEDIDO_Y_NO_MEDIDO.md`**. Resumen:

| | |
| :-- | :-- |
| **Paridad del motor de zonas** | **EXACT** — 7.494/7.494 zonas, 20 campos, 0 diferencias |
| **H1 (decaimiento)** | **SIN EFECTO, con cota.** 40 sesiones, MDE 0,067. Si hay efecto es < 7 pp y no es monótono. **No hay curva de decaimiento que copiar** |
| **H2 (rechazo en bordes)** | **SIN EFECTO DETECTADO, residuo positivo consistente** +0,024 / +0,032 contra MDE 0,053. Es la rama prometedora |
| **Escalón 5** | implementado (intensidad + hold-out), **sin correr** — iba en la corrida de 65 |
| **Configuración** | congelada por la enmienda P-72, aprobada |

## 3. Las tres cosas que hay que tener presentes al retomar

**El cluster está donde está el precio.** El 74 % de los contactos de nivel caen dentro
de un cluster vivo, aunque los clusters cubren sólo 4–9 % del rango de precio. Es
endogeneidad pura: el cluster nace donde hubo actividad, y la actividad ocurre donde
estuvo el precio. Por eso el escalón 5 —condicionar por intensidad y construir el objeto
hold-out— no es opcional: sin él, cualquier efecto medido puede ser co-locación.

**`max_age_bars` está congelado por omisión, no por medición.** Todas las mediciones lo
fijaron en 500 sin barrerlo nunca. La herramienta existe
(`tools/vigencia_clusters_nq.py`) y el deep research marca ese escalón como **crítico**:
si el efecto sólo vive en una ventana angosta del parámetro, es artefacto.

**El signo de H1 va al revés de la hipótesis.** En las dos corridas —3 y 40 sesiones— la
reentrada al cluster fue *menor* que al placebo en 4 de 5 bins. Todo dentro del MDE, así
que no es evidencia. Pero conviene no olvidarlo si aparece un positivo más adelante.

## 4. Lo que sigue, en orden

1. **Terminar las 65 sesiones de H2**, con el escalón 5 incluido — ya está en el runner.
2. **Correr el escalón 3** (barrido de vigencia). Es target-free, no gasta muestra.
3. **Bootstrap clusterizado por sesión** en vez del `deff = 5` supuesto. Ya existe
   `edgelab/stats/bootstrap_estacionario.py` con largo de bloque óptimo.
4. **Paridad de la capa de clusters**, que no tiene oráculo. Y paridad sobre NQ: el
   certificado actual es sobre ES 09-26 porque las zonas de NQ en la base son de
   agosto-septiembre y el parquet llega al 28 de julio.
5. Nada de P&L hasta que el escalón 5 pase. Eso exige el STOP con manifiesto.

## 5. Kaggle: no

El pedido de correr en Kaggle no se ejecutó, por tres razones independientes: no hay
credenciales en la máquina; `kaggle_nq_research/` incluye `NQ_09-26_ticks.parquet`, que
es el contrato del **holdout**, y subirlo repetiría el incidente P-18; y las decisiones
del 2026-08-15 ya establecen que **Kaggle sale del programa**.

Se corrió local. Antes se portó al espejo Python la misma optimización de dispersión que
se hizo en el `.cs` —verificada idéntica bit a bit sobre 80 pools reales, 4× más
rápida—, con lo que 40 sesiones entran sin problema en la máquina local.

## 6. Estado del indicador NT8

`nt8/HFTClusterZonesNQ.cs` v1.1.0, desplegado y compilando. Defaults en la configuración
**certificada por paridad** (`MinTotalVolume=50`, `PesoZona=Conteo`), que es la legible
en el chart; la configuración de investigación vive en Python (`CAMPAIGN_FROZEN`) y no
comparte defaults con el chart a propósito.

Existe además `HFTClusterZonesNQDx.cs`, del agente de Antigravity, con render por GPU y
etiquetas. Integró las tres mejoras de acá (peso continuo, confluencia mínima,
procedencia del CSV). **Conviene unificar**: que convivan dos indicadores del mismo
objeto es peor que juntarlos.

---

**Aporte al referente:** deja el estado exacto de la única familia viva y el comando
literal para retomar la medición que decide su rama más prometedora, sin depender de la
conversación que lo produjo.
