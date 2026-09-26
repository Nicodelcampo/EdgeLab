"""Prop firms: reglas como datos, simulador del ciclo completo (evaluación, fondeada, retiros), esperanza matemática
del participante y requisitos de ventaja que una estrategia de EdgeLab debe cumplir para que la cuenta pague.

Base: Villahermosa (2026, SSRN 7445798), Hall (2026, SSRN 7453580) y Arias (2026, SSRN 7308022). Ver
docs/research/PROPFIRM_EV_DISENO_20260926.md.
"""
from .rules import Rules, load_catalog, save_rules  # noqa: F401
