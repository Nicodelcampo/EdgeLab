"""Freeze a causal A/B candidate; expose progress landmarks without outcomes."""
from dataclasses import dataclass


@dataclass
class Candidate:
    id: str
    a_tick: int
    b_tick: int
    a_available_row: int
    b_available_row: int
    fraction: float = .5
    invalidated: bool = False
    emitted: bool = False
    last_row: int = -1

    def __post_init__(self):
        if self.a_tick==self.b_tick:raise ValueError("ZERO_IMPULSE")
        if not 0<self.fraction<1:raise ValueError("FRACTION_OUTSIDE_0_1")
        if self.a_available_row>self.b_available_row:raise ValueError("A_NOT_KNOWN_AT_B")
        self._geometry=(self.a_tick,self.b_tick,self.a_available_row,
                        self.b_available_row,self.fraction)

    def observe(self,price_tick,row):
        if self._geometry!=(self.a_tick,self.b_tick,self.a_available_row,
                           self.b_available_row,self.fraction):
            raise ValueError("GEOMETRY_CHANGED_AFTER_REGISTRATION")
        if row<self.last_row:raise ValueError("ROW_INVERSION")
        self.last_row=row
        if row<self.b_available_row or self.invalidated or self.emitted:return None
        progress=(self.b_tick-price_tick)/(self.b_tick-self.a_tick)
        if progress<0:
            self.invalidated=True;return None
        if progress>=self.fraction:
            self.emitted=True
            return {"id":self.id,"a_tick":self.a_tick,"b_tick":self.b_tick,
                    "fraction":self.fraction,"progress_observed":progress,
                    "available_row":row,"b_available_row":self.b_available_row,
                    "landmark_timing":"ALREADY_REACHED_AT_B_CONFIRMATION" if row==self.b_available_row else
                                      "OBSERVED_AFTER_B_CONFIRMATION",
                    "target_already_reached":progress>=1,
                    "status":"LANDMARK_ONLY_NO_PREDICTED_OUTCOME"}
        return None

    def snapshot(self):
        """Caller appends EVERY candidate state, not only completed mirrors."""
        return dict(id=self.id,a_tick=self._geometry[0],b_tick=self._geometry[1],
                    a_available_row=self._geometry[2],b_available_row=self._geometry[3],
                    fraction=self._geometry[4],last_row=self.last_row,
                    status="INVALID_BEFORE_LANDMARK" if self.invalidated else
                           "LANDMARK_OBSERVED" if self.emitted else "PENDING")