import pytest

from app.core.models import IndicatorPreset
from app.modules.technical_analysis.presets import IndicatorParams, get_preset_params


def test_get_preset_params_investing():
    params = get_preset_params(IndicatorPreset.INVESTING)
    assert params.stoch_k == 9
    assert params.stoch_d == 6
    assert params.stoch_smooth_k == 1
    assert params.cci_length == 14


def test_get_preset_params_tradingview():
    params = get_preset_params(IndicatorPreset.TRADINGVIEW)
    assert params.stoch_k == 14
    assert params.stoch_d == 3
    assert params.stoch_smooth_k == 3
    assert params.cci_length == 20


def test_preset_params_frozen():
    params = IndicatorParams()
    with pytest.raises(AttributeError):
        params.rsi_length = 20  # type: ignore[misc]


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown preset"):
        get_preset_params("nonexistent")  # type: ignore[arg-type]


def test_all_presets_have_entries():
    for preset in IndicatorPreset:
        params = get_preset_params(preset)
        assert isinstance(params, IndicatorParams)
