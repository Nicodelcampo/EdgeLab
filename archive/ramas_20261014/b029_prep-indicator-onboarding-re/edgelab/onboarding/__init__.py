"""Indicator onboarding controls; no research execution lives here."""
from .registry import REGISTRY_PATH, RegistryCheck, by_id, load_registry, validate_registry
__all__ = ["REGISTRY_PATH", "RegistryCheck", "by_id", "load_registry", "validate_registry"]
