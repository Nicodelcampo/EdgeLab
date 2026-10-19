"""Equivalencia entre una serie sustituta (p. ej. spot de Dukascopy) y la serie de futuros sobre la que se diseñó una estrategia.
Mide, en el solape donde existen las dos, qué tan buen sustituto es; no lo da por bueno. Ver README.md."""
from .proxy import tick_bars,match_bar_size,sync_resample,signal_agreement,outcome_agreement,ema_cross_signals
