from src.formpilot.design_spec import DesignSpec
from src.formpilot.validator import calculate_base_size, validate_spec


def make_spec(**overrides) -> DesignSpec:
    values = dict(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=180,
    )
    return DesignSpec(**(values | overrides))


def test_side_by_side_width_is_deterministic():
    width, depth = calculate_base_size(make_spec())
    assert width == 156.0
    assert depth == 55.0


def test_front_back_uses_narrower_base():
    report = validate_spec(make_spec(layout="front_back", max_base_width=120))
    assert report.passed


def test_rejects_layout_that_exceeds_user_limit():
    report = validate_spec(make_spec(max_base_width=150))
    assert not report.passed
    assert report.issues[0].code == "base_width_exceeded"
    assert "front_back" in report.issues[0].suggestion


def test_extreme_earbuds_depth_expands_each_holder_envelope():
    side_width, side_depth = calculate_base_size(
        make_spec(earbuds_thickness=50, clearance=2.5)
    )
    front_width, front_depth = calculate_base_size(
        make_spec(layout="front_back", earbuds_thickness=50, clearance=2.5)
    )

    assert (side_width, side_depth) == (156.0, 61.0)
    assert (front_width, front_depth) == (82.0, 119.0)
