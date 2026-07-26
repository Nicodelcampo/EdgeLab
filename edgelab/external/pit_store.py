# -*- coding: utf-8 -*-
"""Store point-in-time para predicciones de modelos externos.

## La invariante

> Una barra `t` sólo puede ver predicciones con `available_at_ns <= t`.

Suena obvio. La razón de que exista este módulo es que la forma natural de
escribir el consumo la viola sin que se note:

```python
# LO QUE TODO EL MUNDO ESCRIBE — y está mal
pred = predictor.predict(df)                 # sobre la serie entera
df["p_up"] = pred["p_up"]                    # join por índice
```

Ese `join` alinea la predicción **con la barra que describe**, no con la barra
desde la que se generó. Cada fila queda con una predicción que vio su propio
futuro. No hay ninguna línea "tramposa"; el bug está en el índice.

Acá no se puede escribir eso, porque el store no indexa por `target_ts` sino por
`available_at`, y `as_of(t)` filtra estrictamente.

## Por qué no reusar el store de zonas (F6/F8)

`edgelab.bridge.store` es point-in-time con **un** timestamp (`created_ms`), que
alcanza para una zona: nace y desde ahí existe. Una predicción tiene dos
instantes y el filtro correcto usa el que el store de zonas no tiene. Extender
aquel schema habría metido un concepto de modelo externo dentro del store
canónico de paridad NT8, que es exactamente lo que la regla "no tocar F0–F2 ni el
schema canónico" pide no hacer.
"""
from __future__ import annotations

import bisect
import json
import os

from .contract import ContractError, PredictionRecord


class LookAheadError(AssertionError):
    """Se intentó servir o guardar una predicción que vio el futuro."""


class PITFeatureStore:
    """Predicciones indexadas por `available_at_ns`, servidas as-of.

    No es una base de datos: es una estructura chica y ordenada con una sola
    responsabilidad. La persistencia va a parquet/JSONL aparte para que el
    invariante no dependa del formato de disco.
    """

    def __init__(self, model_id, *, allow_multiple_horizons=True):
        self.model_id = model_id
        self.allow_multiple_horizons = allow_multiple_horizons
        self._recs = []          # ordenado por available_at_ns
        self._avail = []         # claves paralelas, para bisect
        self._sellado = False

    # ------------------------------------------------------------------ write
    def add(self, rec: PredictionRecord):
        if self._sellado:
            raise LookAheadError(
                "store sellado: agregar predicciones después de empezar a "
                "consumir permite 'corregir' el pasado con información nueva.")
        if rec.model_id != self.model_id:
            raise ContractError(
                "model_id distinto: el store es %s y el record es %s. Mezclar "
                "modelos en un store hace que el feature no tenga identidad."
                % (self.model_id, rec.model_id))
        i = bisect.bisect_right(self._avail, rec.available_at_ns)
        self._avail.insert(i, rec.available_at_ns)
        self._recs.insert(i, rec)
        return self

    def add_many(self, recs):
        for r in recs:
            self.add(r)
        return self

    def seal(self):
        """Cierra la escritura. Después sólo se lee."""
        self._sellado = True
        return self

    # ------------------------------------------------------------------- read
    def as_of(self, t_ns):
        """La predicción MÁS RECIENTE disponible en `t_ns`, o None.

        Estrictamente `available_at_ns <= t_ns`. El `<=` y no `<` es deliberado y
        está declarado: una predicción lista exactamente en el cierre de la barra
        `t` se puede usar en `t`, igual que el kernel usa el cierre de `t`.
        Cambiar esto a `<` sería más conservador pero incoherente con el resto
        del proyecto, y las semánticas de borde se declaran, no se eligen a ojo.
        """
        i = bisect.bisect_right(self._avail, t_ns)
        if i == 0:
            return None
        return self._recs[i - 1]

    def series(self, index_ns, key, *, default=float("nan"),
               max_staleness_ns=None):
        """Serie alineada a `index_ns`, tomando en cada `t` lo disponible en `t`.

        `max_staleness_ns` es una salvaguarda que vale la pena usar siempre: sin
        ella, un hueco de cómputo (el precomputado se cortó, la GPU falló, hubo
        feriado) hace que una predicción vieja se propague hacia adelante durante
        horas y el backtest la trate como fresca. Con el límite, el feature pasa a
        NaN y la estrategia tiene que decidir explícitamente qué hacer sin él.
        """
        out = []
        for t in index_ns:
            r = self.as_of(int(t))
            if r is None:
                out.append(default)
                continue
            if (max_staleness_ns is not None
                    and int(t) - r.available_at_ns > max_staleness_ns):
                out.append(default)
                continue
            out.append(r.values.get(key, default))
        return out

    # ------------------------------------------------------------- integridad
    def audit(self):
        """Chequeos estructurales sobre TODO el contenido. Target-free.

        No mira precios ni retornos: sólo timestamps. Un store que pasa esto
        puede seguir siendo inútil, pero no puede estar leyendo el futuro.
        """
        problemas = []
        for r in self._recs:
            if r.target_ts_ns <= r.generated_at_ns:
                problemas.append(dict(tipo="TARGET_NO_ES_FUTURO",
                                      generated_at=r.generated_at_ns,
                                      target_ts=r.target_ts_ns))
            if r.available_at_ns < r.generated_at_ns:
                problemas.append(dict(tipo="DISPONIBLE_ANTES_DE_GENERARSE",
                                      generated_at=r.generated_at_ns,
                                      available_at=r.available_at_ns))
            if r.available_at_ns >= r.target_ts_ns:
                # No es un error: una predicción puede estar lista después del
                # instante que describe. Pero entonces NO SIRVE para operar ese
                # instante, y es mejor decirlo que descubrirlo en producción.
                problemas.append(dict(tipo="LISTA_DESPUES_DEL_TARGET",
                                      available_at=r.available_at_ns,
                                      target_ts=r.target_ts_ns,
                                      nota="inutilizable para operar ese target"))
        if self._avail != sorted(self._avail):
            problemas.append(dict(tipo="ORDEN_ROTO"))
        return dict(ok=not problemas, n=len(self._recs), problemas=problemas)

    def __len__(self):
        return len(self._recs)

    # ------------------------------------------------------------ persistencia
    def to_jsonl(self, path):
        """JSONL: una predicción por línea. Formato elegido por auditabilidad —
        un `diff` de git sobre esto es legible, sobre un parquet no."""
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in self._recs:
                f.write(json.dumps(dict(
                    model_id=r.model_id, generated_at_ns=r.generated_at_ns,
                    target_ts_ns=r.target_ts_ns,
                    available_at_ns=r.available_at_ns, values=r.values),
                    sort_keys=True, ensure_ascii=False) + "\n")
        return path

    @classmethod
    def from_jsonl(cls, path, model_id=None):
        st = None
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                d = json.loads(ln)
                if st is None:
                    st = cls(model_id or d["model_id"])
                st.add(PredictionRecord(**d))
        if st is None:
            raise ContractError("JSONL vacío: %s" % path)
        return st
