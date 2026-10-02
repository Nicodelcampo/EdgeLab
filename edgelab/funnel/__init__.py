"""CPU/GPU discovery funnel. Screening is non-evidentiary; D2 is sealed by default."""
from .device import detect_device
from .features import FeatureStore,ema_bank_cpu
from .hypothesis import HypothesisProposal
from .runner import FunnelRunner
from .splits import make_splits,mask_for
__all__=["detect_device","FeatureStore","ema_bank_cpu","HypothesisProposal","FunnelRunner","make_splits","mask_for"]
