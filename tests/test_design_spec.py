import pytest
from pydantic import ValidationError

from src.formpilot.design_spec import DesignSpec, Layout


def valid_payload() -> dict:
    return {
        "layout": "side_by_side",
        "phone_width": 76,
        "phone_thickness": 10,
        "earbuds_width": 65,
        "earbuds_thickness": 28,
        "max_base_width": 180,
    }


def test_defaults_are_visible_and_in_millimetres():
    spec = DesignSpec(**valid_payload())
    assert spec.layout is Layout.SIDE_BY_SIDE
    assert spec.clearance == 1.2
    assert spec.base_thickness == 5.0
    assert spec.cable_hole_diameter == 8.0


def test_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        DesignSpec(**valid_payload(), secret_scale=10)


def test_rejects_out_of_range_phone_thickness():
    payload = valid_payload() | {"phone_thickness": 30}
    with pytest.raises(ValidationError):
        DesignSpec(**payload)
