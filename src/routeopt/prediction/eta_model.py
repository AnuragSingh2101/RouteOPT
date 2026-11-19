"""ETA Prediction Model - Stub Implementation.

This module is a documented stub as specified in the Master Implementation Prompt Phase 7.
Since no real observed travel-time labels are available (OSM geometry and OSRM estimates
are not observed labels), this module raises a clear error when used.

If real labels are supplied later, this module can be extended with:
- Time-based validation (not random split)
- MAE, RMSE, residuals reporting
- Baseline comparison against OSRM duration
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


class ETAModelError(Exception):
    """Raised when ETA model is used without real observed labels."""
    pass


@dataclass
class ETAModelConfig:
    """Configuration for ETA model (when implemented)."""
    model_type: str = "gradient_boosting"  # or "random_forest", "neural_network"
    features: list[str] = None  # e.g., ["distance", "time_of_day", "road_class", "congestion"]
    target: str = "duration_seconds"
    validation_split: float = 0.2
    time_based_split: bool = True  # Use time-based split, not random


class ETAModel:
    """
    ETA Prediction Model - STUB IMPLEMENTATION.

    This class is a placeholder for future ETA modeling work.
    It raises ETAModelError when instantiated or used because
    no real observed travel-time labels are available.

    OSRM estimates and OSM geometry are NOT observed labels -
    they are model predictions/synthetic data.
    """

    def __init__(self, config: Optional[ETAModelConfig] = None):
        """
        Initialize ETA model.

        Raises:
            ETAModelError: Always, because no real labels are available.
        """
        raise ETAModelError(
            "ETAModel is not implemented because no real observed travel-time labels are available. "
            "OSM geometry and OSRM estimates are model predictions, not ground truth observations. "
            "If real GPS trace data with observed travel times becomes available, "
            "this stub can be replaced with a proper implementation. "
            "For now, use OSRM duration estimates for planning."
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ETAModel":
        """Fit model - not implemented."""
        raise ETAModelError("Cannot fit ETA model: no real observed labels available.")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict ETAs - not implemented."""
        raise ETAModelError("Cannot predict ETAs: no real observed labels available.")

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Evaluate model - not implemented."""
        raise ETAModelError("Cannot evaluate ETA model: no real observed labels available.")


def get_osrm_duration_estimate(
    distance_meters: float,
    speed_kmh: float = 30.0,
) -> float:
    """
    Get duration estimate from OSRM distance (not a learned model).

    This is a simple physics-based estimate, not a learned ETA model.
    """
    speed_ms = speed_kmh * 1000 / 3600
    return distance_meters / speed_ms


def validate_eta_model(
    model: ETAModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """
    Validate ETA model against observed labels.

    This function documents the expected interface for when real labels exist.

    Expected metrics:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Squared Error)
    - Residuals analysis
    - Comparison against OSRM baseline

    Args:
        model: Trained ETA model
        X_test: Test features
        y_test: Observed travel times (ground truth)

    Returns:
        Dictionary with metrics
    """
    raise ETAModelError(
        "ETA validation not available: no real observed labels. "
        "When real labels are available, implement time-based validation "
        "and report MAE, RMSE, and residuals against OSRM baseline."
    )


# Example of what a real implementation would look like:
"""
class RealETAModel:
    def __init__(self, config: ETAModelConfig):
        self.config = config
        self.model = None
        self.scaler = None
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> "RealETAModel":
        # Time-based split
        if self.config.time_based_split:
            split_idx = int(len(X) * (1 - self.config.validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
        else:
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=self.config.validation_split, random_state=42
            )
        
        # Scale features
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        X_train = self.scaler.fit_transform(X_train)
        X_val = self.scaler.transform(X_val)
        
        # Train model
        if self.config.model_type == "gradient_boosting":
            from sklearn.ensemble import GradientBoostingRegressor
            self.model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        elif self.config.model_type == "random_forest":
            from sklearn.ensemble import RandomForestRegressor
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        # Validate
        val_pred = self.model.predict(X_val)
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        self.val_mae = mean_absolute_error(y_val, val_pred)
        self.val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        pred = self.predict(X)
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        return {
            "mae": mean_absolute_error(y, pred),
            "rmse": np.sqrt(mean_squared_error(y, pred)),
            "residuals": y - pred,
        }
"""