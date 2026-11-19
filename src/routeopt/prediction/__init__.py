"""ETA prediction module (stub implementation)."""

from .eta_model import (
    ETAModel,
    ETAModelConfig,
    ETAModelError,
    get_osrm_duration_estimate,
    validate_eta_model,
)

__all__ = [
    "ETAModel",
    "ETAModelConfig",
    "ETAModelError",
    "get_osrm_duration_estimate",
    "validate_eta_model",
]