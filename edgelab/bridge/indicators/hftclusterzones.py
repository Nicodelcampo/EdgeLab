"""HFTClusterZones — espejo Python de `nt8/HFTClusterZonesNQ.cs`.

**Target-free: no mira retornos.** Construye el objeto; no lo evalúa.

## Qué es un cluster acá

No es un histograma de cajas. Cada zona HFT proyecta un **halo gaussiano** sobre el
eje de precio: en cada tick suma `exp(-d²/2σ²)`, donde `d` es la distancia en ticks
desde ese precio hasta el borde más cercano de la zona (0 si el precio cae dentro).
Los ticks cuya densidad acumulada llega a `min_density` se agrupan en **islas**
contiguas (tolerancia de 1 tick de hueco), y cada isla es un cluster. El POC es el
tick de máxima densidad, desempatado por volumen ponderado.

La diferencia con la caja importa: con cajas la pertenencia es binaria y el mapa sale
saturado o vacío; con el kernel hay gradación, y `σ` se vuelve un parámetro de
investigación barrible en vez de una decisión oculta.

## Ciclo de vida

Un cluster nace `ACTIVE` y muere de una de cuatro formas, que son **riesgos
competitivos** — no censura simple:

- `TOUCHED_POC`  el precio llegó al POC (no es muerte: es el evento de interés);
- `DEPLETED`     el volumen operado adentro agotó `capacity_volume`;
- `INVALIDATED`  el precio perforó el rango con menos del 80 % de capacidad consumida;
- `EXPIRED`      pasaron `max_age_bars` desde el nacimiento.

Tratar cualquiera de las tres muertes como censura simple sesga la incidencia
acumulada. Va CIF, no Kaplan-Meier.

## Divergencias del original que están replicadas a propósito

Este módulo reproduce el `.cs` **incluyendo sus rarezas**, porque su función es servir
de oráculo de paridad. Cada una está marcada en el código con `# PARIDAD:`:

1. Un cluster `EXPIRED` **sigue siendo elegible para expansión** (el filtro de
   `matching` sólo excluye `DEPLETED` e `INVALIDATED`). Su geometría se actualiza y se
   emite `EXPANDED`, pero nunca revive.
2. La expansión usa **marcas de agua**: `peak_density`, `seed_volume`,
   `capacity_volume` y `contributing_zones` sólo suben. La geometría es la unión
   histórica y nunca se encoge.
3. Con más de 300 clusters se descarta el más viejo **en silencio**, sin evento
   terminal. Acá sí se emite `EVICTED` para que el censo no tenga agujeros; el `.cs`
   no lo emite (ver `tools/paridad_hftclusterzones.py`).

## Por qué el peso continuo (variante de investigación)

El `.cs` mezcla dos criterios incompatibles. Para la **distancia** usa un kernel suave:
una zona no está o no está en un nivel, aporta `exp(-d²/2σ²)`. Para la **pertenencia**
usa un corte duro: la zona entra al campo sólo si su volumen supera un umbral.

Ese corte duro es lo que hace frágil al objeto. Medido con el test del proyecto
(±1 de volumen sobre dos tercios de los ticks), el turnover de zonas da 32-38 %, contra
un contrato de 5 %. La mediana de volumen es 64 y el umbral 50: casi todas las zonas
viven pegadas a su compuerta.

`weight_mode` aplica al eje de calidad el mismo tratamiento que ya recibe el eje de
distancia. Con `"volume"` o `"log_volume"` la zona aporta `w·exp(-d²/2σ²)`, así que una
perturbación mueve **pesos**, no membresías. Y rompe el compromiso que el corte duro
imponía: hoy la única forma de discriminar es subir el umbral, y eso mata la
estabilidad; con pesos la discriminación viene de la **concentración** del campo, y se
puede tener muchas zonas —estable— con picos igual de nítidos.

`"count"` sigue siendo el default porque es lo que reproduce el `.cs` y lo que la
paridad certifica. Las otras dos son variantes de investigación y no tienen oráculo.

**Y traen un efecto secundario que hay que acotar.** Con peso continuo, `min_density`
deja de significar "cuántas zonas confluyen": una zona con volumen ≥ `min_density` veces
la mediana alcanza el umbral **ella sola**, en los ticks de su propio interior donde el
gaussiano vale 1. Medido sobre una sesión de NQ con `min_density=3`: en modo `count`
el 0 % de los clusters tiene una sola zona contribuyente; en `volume`, el 8,7 %.

Eso importa más de lo que parece, porque un cluster de una sola zona es **trivialmente
estable** ante una perturbación de membresía — no depende de ninguna zona marginal. Así
que parte de la mejora de turnover que muestra el peso continuo podría ser degeneración
disfrazada de robustez. `min_contributing_zones` es la compuerta que lo separa: exigir
confluencia real y volver a medir. Si la mejora sobrevive, es real.

## La canibalización, y por qué `merge_excluye_expirados` existe

El filtro que busca un cluster al cual fusionarse excluye `DEPLETED` e `INVALIDATED`
pero **no** `EXPIRED`. Un cluster que no muere absorbe todo lo que solape con él —
`lower = min`, `upper = max`, sin techo — y crece hasta tragarse la sesión entera. En el
chart se ve como una sola banda gigante.

Con la invalidación activa el efecto queda tapado, porque el 99,4 % de los clusters
muere perforado antes de crecer. Pero apenas se desactiva la invalidación para poder
medir el decaimiento por consumo, la canibalización aparece: 40 clusters por sesión en
vez de cientos, y con eso no hay muestra para estimar nada.

`merge_excluye_expirados=True` corta el ciclo. Viene apagado porque el default reproduce
el `.cs`, que es lo que la paridad certifica; la campaña lo enciende.

*(El mecanismo lo identificó el agente de Antigravity revisando el chart. Acá estaba
documentado como rareza —`test_PARIDAD_un_cluster_EXPIRED_todavia_puede_expandirse`—
sin haberlo conectado con el síntoma.)*

## Cómo se usa para medir

`ClusterEngine` emite un evento por cada transición. Ese flujo de eventos **es** el
censo as-of: reproducirlo en orden reconstruye el estado exacto que el cluster tenía
en cualquier instante t, incluidos los que después se fusionaron o murieron. Leer el
estado final del objeto, en cambio, no sirve — por la marca de agua del punto 2.
"""
from __future__ import annotations

import math

NAME = "HFTClusterZones"
VERSION = "1.1"

RESEARCH_DEFAULTS = dict(
    # --- construccion del cluster ---
    halo_sigma_ticks=3.0,      # ancho de banda del kernel gaussiano
    min_density=3.0,           # densidad acumulada que dispara un cluster
    lookback_zones=100,        # zonas recientes evaluadas en el campo
    max_age_bars=500,          # edad a la que un cluster pasa a EXPIRED
    # --- consumo y muerte ---
    min_capacity_volume=1200.0,
    capacity_multiplier=2.5,
    invalidation_ticks=8,      # perforacion mas alla del rango
    # --- constantes del original, expuestas para barrerlas ---
    kernel_cutoff_sigmas=3.5,  # mas alla, el aporte se descarta
    envelope_sigmas=3.0,       # margen de la envolvente de precios
    contrib_sigmas=2.0,        # distancia para contar una zona como contribuyente
    gap_ticks=1,               # hueco tolerado al segmentar islas
    max_grid_ticks=2500,       # proteccion contra rangos anomalos
    poc_touch_ticks=0.6,       # |precio - poc| que cuenta como toque
    invalidation_capacity_pct=0.8,
    max_clusters=300,
    # --- VARIANTE DE INVESTIGACION, no esta en el .cs ---
    # "count" reproduce el original: cada zona aporta 1. Las otras dos la hacen aportar
    # segun su calidad. Ver la nota "Por que el peso continuo" en el docstring.
    weight_mode="count",        # count | volume | log_volume
    weight_ref_vol=0.0,         # 0 = normalizar por la mediana del pool
    min_contributing_zones=1,   # confluencia minima real; ver nota abajo
    merge_excluye_expirados=False,  # ver "La canibalizacion" abajo
)

# Configuracion congelada para la campana H-CLUSTER-NQ por el test de estabilidad
# target-free sobre tres sesiones. NO es el default: el default reproduce el `.cs`
# v1.0.0, que es lo unico con oraculo. Ver `docs/research/PREREGISTRO_H-CLUSTER-NQ`.
CAMPAIGN_FROZEN = dict(
    RESEARCH_DEFAULTS,
    weight_mode="volume",
    min_contributing_zones=3,
    halo_sigma_ticks=3.0,
    min_density=3.0,
    max_age_bars=500,
    merge_excluye_expirados=True,
)

ACTIVE = "Active"
TOUCHED_POC = "TouchedPOC"
DEPLETED = "Depleted"
INVALIDATED = "Invalidated"
EXPIRED = "Expired"

_MUERTOS_PARA_EXPANSION = (DEPLETED, INVALIDATED)
_VIVOS_PARA_CONSUMO = (ACTIVE, TOUCHED_POC)


def _params(overrides=None):
    p = dict(RESEARCH_DEFAULTS)
    if overrides:
        p.update({k: v for k, v in overrides.items() if v is not None})
    return p


def _pesos(zones, p):
    """Peso de cada zona en el campo. `count` = 1 para todas, como el `.cs`.

    Las variantes normalizan por un volumen de referencia para que el peso quede en el
    orden de 1 y `min_density` siga significando aproximadamente "cuántas zonas". Sin
    esa normalización, cambiar de modo obligaría a re-calibrar el umbral y los dos
    modos dejarían de ser comparables.
    """
    modo = p.get("weight_mode", "count")
    if modo == "count":
        return [1.0] * len(zones)
    vols = [float(z.get("total_vol", 0.0)) for z in zones]
    ref = float(p.get("weight_ref_vol") or 0.0)
    if ref <= 0:
        pos = sorted(v for v in vols if v > 0)
        ref = pos[len(pos) // 2] if pos else 1.0
    if modo == "volume":
        return [v / ref for v in vols]
    if modo == "log_volume":
        # comprime la cola: una zona de 10x el volumen pesa ~2x, no 10x
        return [math.log1p(v / ref) / math.log(2.0) for v in vols]
    raise ValueError("weight_mode desconocido: %r" % modo)


def halo_density(zones, tick_size, params=None):
    """Campo de densidad gaussiana por tick de precio.

    Devuelve `(density, vol_weight)`, dos dicts `tick -> valor`, con **sólo** los
    ticks que alcanzan `min_density`. Un dict vacío significa que ninguna banda de
    precio junta suficiente masa: es un resultado, no un error.

    La distancia de una zona a un precio es 0 si el precio cae dentro de la zona, y
    si no, la distancia al borde más cercano. Por eso una zona ancha aporta peso
    máximo en todo su interior.
    """
    p = _params(params)
    if len(zones) < 2:
        return {}, {}

    sigma = float(p["halo_sigma_ticks"])
    if sigma <= 0:
        raise ValueError("halo_sigma_ticks tiene que ser > 0")
    pesos = _pesos(zones, p)
    two_sigma_sq = 2.0 * sigma * sigma
    cutoff = p["kernel_cutoff_sigmas"] * sigma

    lo_p = min(z["lower"] for z in zones) - p["envelope_sigmas"] * sigma * tick_size
    hi_p = max(z["upper"] for z in zones) + p["envelope_sigmas"] * sigma * tick_size
    lo_tk = math.floor(lo_p / tick_size)
    hi_tk = math.ceil(hi_p / tick_size)
    if hi_tk - lo_tk > p["max_grid_ticks"]:
        return {}, {}

    # DISPERSION, no barrido. La version anterior recorria cada tick de la
    # envolvente preguntando por todas las zonas: O(grilla x zonas), con un exp() por
    # par. Con 7.000 nacimientos de zona por sesion eso domina todo el costo del
    # modulo. Ahora cada zona reparte su aporte sobre los ~2*radio+1 ticks de su
    # alcance, y la exponencial sale de una tabla indexada por distancia entera.
    #
    # El resultado es IDENTICO, no aproximado: cada tick acumula las zonas en el mismo
    # orden en que aparecen en `zones`, igual que el barrido, asi que la suma en punto
    # flotante se hace en el mismo orden. Importa: un empate resuelto distinto podria
    # caer del otro lado de `min_density`.
    radio = int(cutoff)
    lookup = [math.exp(-(float(d) * d) / two_sigma_sq) for d in range(radio + 1)]

    acum_d, acum_v = {}, {}
    for z, w_z in zip(zones, pesos):
        z_lo = int(round(z["lower"] / tick_size))
        z_hi = int(round(z["upper"] / tick_size))
        vol_z = z.get("total_vol", 0.0)
        desde = max(int(lo_tk), z_lo - radio)
        hasta = min(int(hi_tk), z_hi + radio)
        for tk in range(desde, hasta + 1):
            d = z_lo - tk if tk < z_lo else (tk - z_hi if tk > z_hi else 0)
            if d > radio:
                continue
            w = w_z * lookup[d]
            acum_d[tk] = acum_d.get(tk, 0.0) + w
            acum_v[tk] = acum_v.get(tk, 0.0) + w * vol_z

    density, vol_w = {}, {}
    umbral = p["min_density"]
    for tk, val in acum_d.items():
        if val >= umbral:
            density[tk] = val
            vol_w[tk] = acum_v[tk]
    return density, vol_w


def segment_islands(ticks, gap=1):
    """Agrupa ticks calificados en islas contiguas.

    Dos ticks separados por más de `gap` abren una isla nueva. El orden es
    ascendente y determinista: el desempate del POC depende de él.
    """
    out = []
    actual = []
    for tk in sorted(ticks):
        if not actual or tk - actual[-1] <= gap:
            actual.append(tk)
        else:
            out.append(actual)
            actual = [tk]
    if actual:
        out.append(actual)
    return out


def _poc(island, density, vol_w):
    """Tick de máxima densidad; empate por volumen ponderado, recorriendo ascendente.

    PARIDAD: el original compara `den > peak or (|den-peak| < 1e-4 and vw > maxvw)`.
    La tolerancia de 1e-4 y el orden ascendente definen qué tick gana un empate, así
    que se replican tal cual.
    """
    poc_tk = island[0]
    peak = 0.0
    max_vw = 0.0
    for tk in island:
        den = density[tk]
        vw = vol_w[tk]
        if den > peak or (abs(den - peak) < 1e-4 and vw > max_vw):
            peak = den
            max_vw = vw
            poc_tk = tk
    return poc_tk, peak


class ClusterEngine:
    """Motor con estado que emite un evento por cada transición de cluster.

    El flujo de eventos es el censo as-of. Cada evento lleva el estado **completo**
    del cluster en ese instante, no un delta, para que reproducirlo no exija haber
    visto los anteriores.
    """

    def __init__(self, tick_size, params=None):
        self.tick_size = float(tick_size)
        self.p = _params(params)
        self.clusters = []
        self.events = []
        self._counter = 0

    # ---------- emision ----------
    def _emit(self, nombre, c, bar, price=None):
        ev = dict(c)
        ev.pop("_", None)
        ev.update(event=nombre, bar=bar, price=price,
                  remaining_cap_pct=self.remaining_pct(c))
        self.events.append(ev)
        return ev

    def remaining_pct(self, c):
        cap = c["capacity_volume"]
        if cap <= 0:
            return 0.0
        return max(0.0, 1.0 - c["volume_inside"] / cap)

    # ---------- nacimiento y expansion ----------
    def on_zone_created(self, zones, bar, ts=None):
        """Reevalúa el campo gravitacional. Se llama cuando **nace** una zona.

        Ojo con esto al interpretar: el cluster sólo se actualiza en nacimientos de
        zona, nunca por movimiento de precio. La geometría de un cluster puede quedar
        vieja durante muchas barras si no nace ninguna zona.
        """
        p = self.p
        ts = ts if ts is not None else bar
        corte = max(0, len(zones) - max(10, int(p["lookback_zones"])))
        pool = [z for z in zones[corte:]
                if bar - z["start_bar"] <= p["max_age_bars"]]
        if len(pool) < 2:
            return []

        density, vol_w = halo_density(pool, self.tick_size, p)
        if not density:
            return []

        sigma = p["halo_sigma_ticks"]
        emitidos = []
        for island in segment_islands(density.keys(), int(p["gap_ticks"])):
            poc_tk, peak = _poc(island, density, vol_w)
            lower = min(island) * self.tick_size - self.tick_size * 0.5
            upper = max(island) * self.tick_size + self.tick_size * 0.5

            seed_vol = 0.0
            seed_cvd = 0.0
            n_zonas = 0
            start_bar = bar
            for z in pool:
                d_lo = max(0.0, (lower - z["upper"]) / self.tick_size)
                d_hi = max(0.0, (z["lower"] - upper) / self.tick_size)
                if max(d_lo, d_hi) <= p["contrib_sigmas"] * sigma:
                    seed_vol += z.get("total_vol", 0.0)
                    seed_cvd += z.get("cvd", 0.0)
                    n_zonas += 1
                    start_bar = min(start_bar, z["start_bar"])

            # Confluencia real: cuantas zonas aportan de verdad, sin importar su peso.
            # Con peso continuo una sola zona gorda puede cruzar min_density; esta
            # compuerta es lo unico que distingue un cluster de una zona redibujada.
            if n_zonas < int(p.get("min_contributing_zones", 1)):
                continue

            cap = max(p["min_capacity_volume"], seed_vol * p["capacity_multiplier"])

            # PARIDAD: se busca desde el final hacia atras y se toma el PRIMERO que
            # solapa. Los EXPIRED no se excluyen: pueden absorber una expansion.
            match = None
            for c in reversed(self.clusters):
                if c["state"] in _MUERTOS_PARA_EXPANSION:
                    continue
                if p.get("merge_excluye_expirados") and c["state"] == EXPIRED:
                    continue
                if min(upper, c["upper"]) >= max(lower, c["lower"]):
                    match = c
                    break

            if match is not None:
                # PARIDAD: marcas de agua. Nada de esto baja nunca.
                match["lower"] = min(match["lower"], lower)
                match["upper"] = max(match["upper"], upper)
                match["poc"] = poc_tk * self.tick_size      # el POC sí se pisa
                match["peak_density"] = max(match["peak_density"], peak)
                match["seed_volume"] = max(match["seed_volume"], seed_vol)
                match["capacity_volume"] = max(match["capacity_volume"], cap)
                match["contributing_zones"] = max(match["contributing_zones"], n_zonas)
                match["end_bar"] = bar
                match["end_ts"] = ts
                emitidos.append(self._emit("CLUSTER_EXPANDED", match, bar))
            else:
                self._counter += 1
                nc = dict(
                    id=self._counter, lower=lower, upper=upper,
                    poc=poc_tk * self.tick_size, start_bar=start_bar, end_bar=bar,
                    start_ts=ts, end_ts=ts, peak_density=peak, seed_volume=seed_vol,
                    seed_cvd=seed_cvd, capacity_volume=cap, volume_inside=0.0,
                    delta_inside=0.0, touched_poc=False, state=ACTIVE,
                    contributing_zones=n_zonas,
                )
                self.clusters.append(nc)
                emitidos.append(self._emit("CLUSTER_CREATED", nc, bar))

                if len(self.clusters) > int(p["max_clusters"]):
                    viejo = self.clusters.pop(0)
                    # El .cs lo descarta en silencio. Acá se emite para que el censo
                    # no tenga agujeros; el validador de paridad lo ignora.
                    emitidos.append(self._emit("CLUSTER_EVICTED", viejo, bar))
        return emitidos

    # ---------- consumo ----------
    def on_tick(self, price, vol, side, bar):
        """Un tick operado: consume capacidad, marca toque de POC, o invalida."""
        p = self.p
        margen = p["invalidation_ticks"] * self.tick_size
        emitidos = []
        for c in self.clusters:
            if c["state"] not in _VIVOS_PARA_CONSUMO:
                continue

            if price > c["upper"] + margen or price < c["lower"] - margen:
                if c["volume_inside"] < c["capacity_volume"] * p["invalidation_capacity_pct"]:
                    c["state"] = INVALIDATED
                    emitidos.append(self._emit("CLUSTER_INVALIDATED", c, bar, price))
                    continue

            if c["lower"] <= price <= c["upper"]:
                c["volume_inside"] += vol
                c["delta_inside"] += side * vol

                if (not c["touched_poc"]
                        and abs(price - c["poc"]) < self.tick_size * p["poc_touch_ticks"]):
                    c["touched_poc"] = True
                    if c["state"] == ACTIVE:
                        c["state"] = TOUCHED_POC
                    emitidos.append(self._emit("CLUSTER_TOUCHED_POC", c, bar, price))

                if self.remaining_pct(c) <= 0.0:
                    c["state"] = DEPLETED
                    emitidos.append(self._emit("CLUSTER_DEPLETED", c, bar, price))
        return emitidos

    # ---------- expiracion ----------
    def on_bar(self, bar):
        """Cierre de barra: mata por edad lo que siga vivo."""
        emitidos = []
        for c in self.clusters:
            if c["state"] in _VIVOS_PARA_CONSUMO:
                if bar - c["start_bar"] > self.p["max_age_bars"]:
                    c["state"] = EXPIRED
                    emitidos.append(self._emit("CLUSTER_EXPIRED", c, bar))
        return emitidos


def as_of(events, bar):
    """Estado de todos los clusters **tal como era** en `bar`.

    Reproduce el flujo de eventos hasta esa barra. Es lo único admisible para medir:
    leer el objeto final devuelve marcas de agua acumuladas después de `bar`, y un
    cluster que se fusionó o murió más tarde ya no estaría.
    """
    estado = {}
    for ev in events:
        if ev["bar"] > bar:
            break
        estado[ev["id"]] = {k: v for k, v in ev.items()
                            if k not in ("event", "bar", "price")}
    return estado


def census(events):
    """Resumen del ciclo de vida: cuántos clusters y cómo terminó cada uno.

    Publica el desenlace de **todos**, incluidos los que siguen vivos (`censurados`),
    porque una tabla que sólo cuenta los que murieron sobreestima la incidencia.
    """
    terminal = {"CLUSTER_DEPLETED": DEPLETED, "CLUSTER_INVALIDATED": INVALIDATED,
                "CLUSTER_EXPIRED": EXPIRED, "CLUSTER_EVICTED": "Evicted"}
    nacidos = set()
    desenlace = {}
    tocaron = set()
    for ev in events:
        if ev["event"] == "CLUSTER_CREATED":
            nacidos.add(ev["id"])
        elif ev["event"] == "CLUSTER_TOUCHED_POC":
            tocaron.add(ev["id"])
        elif ev["event"] in terminal and ev["id"] not in desenlace:
            desenlace[ev["id"]] = terminal[ev["event"]]
    out = dict(n=len(nacidos), tocaron_poc=len(tocaron),
               censurados=len(nacidos) - len(desenlace))
    for estado in (DEPLETED, INVALIDATED, EXPIRED, "Evicted"):
        out[estado.lower()] = sum(1 for v in desenlace.values() if v == estado)
    return out
