"""Frozen causal A/B attempts, not a retrospective completed-mirror detector."""
from dataclasses import dataclass, field
from l2_asof_features import integer


@dataclass(frozen=True)
class Geometry:
    id: str
    instrument: str
    a_tick: int
    b_tick: int
    a_available_row: int
    b_available_row: int
    registration_row: int
    registration_ts_us: int
    fraction: float = .5

    def __post_init__(self):
        if not self.id or not self.instrument:
            raise ValueError("ID_AND_INSTRUMENT_REQUIRED")
        for name in ("a_tick", "b_tick", "a_available_row", "b_available_row",
                     "registration_row", "registration_ts_us"):
            integer(getattr(self, name), name)
        if self.a_tick == self.b_tick:
            raise ValueError("ZERO_FIRST_IMPULSE")
        if not 0 <= self.a_available_row <= self.b_available_row <= self.registration_row:
            raise ValueError("GEOMETRY_NOT_KNOWN_AT_REGISTRATION")
        if isinstance(self.fraction, bool) or not isinstance(self.fraction, (int, float)) or \
                not 0 < self.fraction < 1:
            raise ValueError("FRACTION_OUTSIDE_OPEN_UNIT_INTERVAL")


@dataclass
class Attempt:
    geometry: Geometry
    last_row: int = field(default=-1)
    last_ts_us: int = field(default=-1)
    status: str = field(default="REGISTERED")
    emitted: bool = field(default=False)
    eligibility: bool = field(default=False)
    observations: int = field(default=0)

    def __post_init__(self):
        self._registered_geometry = self.geometry

    def observe(self, price_tick, row, ts_us, engine=None, max_age_us=None):
        if self.geometry != self._registered_geometry:
            raise ValueError("GEOMETRY_CHANGED_AFTER_REGISTRATION")
        for label, value in (("price_tick", price_tick), ("row", row), ("ts_us", ts_us)):
            integer(value, label)
        g = self.geometry
        if row < g.registration_row or ts_us < g.registration_ts_us:
            raise ValueError("OBSERVATION_BEFORE_CAUSAL_REGISTRATION")
        if row <= self.last_row or ts_us < self.last_ts_us:
            raise ValueError("OBSERVATION_ORDER_OR_DUPLICATE")
        self.last_row, self.last_ts_us = row, ts_us
        if self.emitted or self.status == "INVALID_BEFORE_LANDMARK":
            return None
        first_observation = self.observations == 0
        self.observations += 1
        progress = (g.b_tick-price_tick)/(g.b_tick-g.a_tick)
        if progress < 0:
            self.status = "INVALID_BEFORE_LANDMARK"
            return None
        if progress < g.fraction:
            self.status = "PENDING_LANDMARK"
            return None
        self.emitted = True
        already_reached = progress >= 1
        late = first_observation
        self.eligibility = not late and not already_reached
        self.status = ("A_ALREADY_REACHED_AT_OBSERVATION" if already_reached else
                       "LANDMARK_ALREADY_REACHED_AT_FIRST_OBSERVATION" if late else
                       "CAUSAL_LANDMARK_OBSERVED")
        direction = -1 if g.b_tick > g.a_tick else 1
        packet = dict(
            id=g.id, instrument=g.instrument, a_tick=g.a_tick, b_tick=g.b_tick,
            fraction=g.fraction, progress_observed=progress,
            registration_row=g.registration_row,
            observed_row=row, observed_ts_us=ts_us, direction=direction,
            timing_status=self.status, prospective_event_eligible=self.eligibility,
            target_already_reached=already_reached,
            forecast_computed=False, outcomes_computed=False, l2=None,
            l2_observable=False)
        if engine is not None:
            packet["l2"] = engine.sample(row, ts_us, direction=direction,
                target_tick=g.a_tick, target_side="bid" if direction == -1 else "ask",
                max_age_us=max_age_us, instrument=g.instrument)
            packet["l2_observable"] = packet["l2"]["gate"] == "PASS" and \
                packet["l2"]["values"] is not None
        return packet

    def receipt(self):
        g = self.geometry
        return dict(id=g.id, instrument=g.instrument,
                    registration_row=g.registration_row, a_available_row=g.a_available_row,
                    b_available_row=g.b_available_row, status=self.status,
                    observations=self.observations, last_row=self.last_row,
                    landmark_emitted=self.emitted, prospective_event_eligible=self.eligibility,
                    forecast_computed=False, outcomes_computed=False)


class AttemptRegistry:
    def __init__(self, instrument):
        if not instrument:
            raise ValueError("INSTRUMENT_REQUIRED")
        self.instrument = instrument
        self.attempts = {}

    def register(self, geometry):
        if geometry.instrument != self.instrument:
            raise ValueError("CROSS_INSTRUMENT_REGISTRATION")
        if geometry.id in self.attempts:
            raise ValueError("ATTEMPT_ID_ALREADY_REGISTERED")
        self.attempts[geometry.id] = Attempt(geometry)
        return self.attempts[geometry.id]

    def receipts(self):
        """Return ALL attempts, including failures and those without a landmark."""
        return [attempt.receipt() for attempt in self.attempts.values()]


def geometry_from_confirmed_event(event, publication, instrument, file_id,
                                  fraction=.5):
    """Adapter contract for EspejoImpulsos IMP_CONFIRMED, not terminal records.

    An independently checked raw publication ledger must supply this bar's
    boundary. Both A/B are conservatively regarded as known only at confirmation.
    No bar_B->row backdating and no estado_final/S2/full-mirror selection.
    """
    if event.get("kind") != "IMP_CONFIRMED":
        raise ValueError("ONLY_CAUSAL_IMP_CONFIRMED_REGISTRATIONS")
    if any(k in event for k in ("estado_final","bar_final","S2","S2v2",
                               "MIRROR_COMPLETED","future_return","pnl")):
        raise ValueError("TERMINAL_OR_OUTCOME_FIELDS_FORBIDDEN")
    for name in ("bar","A","B"):
        integer(event.get(name),name)
    if event["A"] == event["B"]:
        raise ValueError("ZERO_FIRST_IMPULSE")
    if publication.get("bar_i") != event["bar"]:
        raise ValueError("CONFIRMATION_BAR_LEDGER_MISMATCH")
    if publication.get("publication_mode") != "OBSERVED_NEXT_TIMESTAMP_ROW":
        raise ValueError("RAW_PUBLICATION_LEDGER_REQUIRED")
    for name in ("bar_close_row","snapshot_asof_row","snapshot_ts_us",
                 "available_row","available_ts_us"):
        integer(publication.get(name),name)
    if not (0 <= publication["bar_close_row"] <= publication["snapshot_asof_row"]
            < publication["available_row"] and
            publication["snapshot_ts_us"] < publication["available_ts_us"]):
        raise ValueError("RAW_PUBLICATION_BOUNDARY_FAIL")
    if publication.get("instrument") != instrument or publication.get("file_id") != file_id:
        raise ValueError("CROSS_FILE_OR_INSTRUMENT_LEDGER")
    row=publication["available_row"]
    return Geometry(
        id=f'{instrument}:{file_id}:{event["bar"]}:{event["A"]}:{event["B"]}',
        instrument=instrument,a_tick=event["A"],b_tick=event["B"],
        a_available_row=row,b_available_row=row,registration_row=row,
        registration_ts_us=publication["available_ts_us"],fraction=fraction)