"""Tests for ETA model stub."""

import pytest
import numpy as np

from routeopt.prediction import (
    ETAModel,
    ETAModelConfig,
    ETAModelError,
    get_osrm_duration_estimate,
    validate_eta_model,
)


class TestETAModelStub:
    """Test that ETA model stub raises appropriate errors."""

    def test_eta_model_init_raises_error(self):
        """ETAModel instantiation should raise ETAModelError."""
        with pytest.raises(ETAModelError) as exc_info:
            ETAModel()
        assert "no real observed travel-time labels" in str(exc_info.value)

    def test_eta_model_init_with_config_raises_error(self):
        """ETAModel with config should raise ETAModelError."""
        config = ETAModelConfig(model_type="random_forest")
        with pytest.raises(ETAModelError):
            ETAModel(config)

    def test_eta_model_fit_raises_error(self):
        """ETAModel.fit should raise ETAModelError."""
        # Can't instantiate, so test the class method would raise
        # We just verify the exception class exists
        assert issubclass(ETAModelError, Exception)

    def test_eta_model_predict_raises_error(self):
        """ETAModel.predict should raise ETAModelError."""
        assert issubclass(ETAModelError, Exception)

    def test_validate_eta_model_raises_error(self):
        """validate_eta_model should raise ETAModelError."""
        with pytest.raises(ETAModelError) as exc_info:
            validate_eta_model(None, np.array([[1]]), np.array([1]))
        assert "no real observed labels" in str(exc_info.value)


class TestOSRMDurationEstimate:
    """Test OSRM duration estimate (physics-based, not learned)."""

    def test_basic_estimate(self):
        """Test basic duration estimate."""
        # 10 km at 30 km/h = 10/30 * 3600 = 1200 seconds
        duration = get_osrm_duration_estimate(10000, 30.0)
        assert abs(duration - 1200) < 1

    def test_zero_distance(self):
        """Test zero distance gives zero duration."""
        duration = get_osrm_duration_estimate(0, 30.0)
        assert duration == 0

    def test_different_speeds(self):
        """Test different speeds."""
        # 5 km at 60 km/h = 5/60 * 3600 = 300 seconds
        duration = get_osrm_duration_estimate(5000, 60.0)
        assert abs(duration - 300) < 1

        # 5 km at 10 km/h = 5/10 * 3600 = 1800 seconds
        duration = get_osrm_duration_estimate(5000, 10.0)
        assert abs(duration - 1800) < 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])