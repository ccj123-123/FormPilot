from src.formpilot.design_spec import DesignSpec, Feedback
from src.formpilot.revision import RevisionResult, revise_from_feedback


def make_spec(**overrides) -> DesignSpec:
    values = dict(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=180,
    )
    return DesignSpec(**(values | overrides))


def make_feedback(**overrides) -> Feedback:
    values = dict(phone_fit="good", earbuds_fit="good", stability="stable")
    return Feedback(**(values | overrides))


def test_tight_fit_and_unstable_base_change_clearance_and_thickness():
    result = revise_from_feedback(
        make_spec(), make_feedback(phone_fit="too_tight", stability="unstable")
    )
    assert isinstance(result, RevisionResult)
    assert result.spec.clearance == 1.5
    assert result.spec.base_thickness == 6.0
    assert len(result.changes) == 2
    assert any("\u95f4\u9699" in change and "1.5" in change and "mm" in change for change in result.changes)
    assert any("\u5e95\u5ea7\u539a\u5ea6" in change and "6.0" in change and "mm" in change for change in result.changes)


def test_loose_fit_reduces_clearance_to_one_mm_with_message():
    result = revise_from_feedback(make_spec(), make_feedback(phone_fit="too_loose"))
    assert result.spec.clearance == 1.0
    assert any(
        "\u95f4\u9699" in change and "1.0" in change and "mm" in change
        for change in result.changes
    )


def test_earbuds_tight_fit_also_increases_clearance():
    result = revise_from_feedback(
        make_spec(), make_feedback(phone_fit="good", earbuds_fit="too_tight")
    )
    assert result.spec.clearance == 1.5


def test_loose_fit_at_clearance_floor_stays_unchanged():
    result = revise_from_feedback(
        make_spec(clearance=0.5), make_feedback(phone_fit="too_loose")
    )
    assert result.spec.clearance == 0.5
    assert not any("间隙" in change for change in result.changes)


def test_tight_fit_at_clearance_cap_stays_unchanged():
    result = revise_from_feedback(
        make_spec(clearance=2.5), make_feedback(phone_fit="too_tight")
    )
    assert result.spec.clearance == 2.5
    assert not any("间隙" in change for change in result.changes)


def test_unstable_base_at_thickness_cap_stays_unchanged():
    result = revise_from_feedback(
        make_spec(base_thickness=10.0), make_feedback(stability="unstable")
    )
    assert result.spec.base_thickness == 10.0
    assert not any("厚度" in change for change in result.changes)


def test_all_good_and_stable_produces_no_changes():
    spec = make_spec()
    result = revise_from_feedback(spec, make_feedback())
    assert result.spec.model_dump() == spec.model_dump()
    assert result.changes == []


def test_original_spec_is_unchanged_and_result_is_new_object():
    spec = make_spec()
    result = revise_from_feedback(
        spec, make_feedback(phone_fit="too_tight", stability="unstable")
    )
    assert result.spec is not spec
    assert spec.clearance == 1.2
    assert spec.base_thickness == 5.0


def test_mixed_fit_feedback_gives_tight_precedence():
    result = revise_from_feedback(
        make_spec(), make_feedback(phone_fit="too_tight", earbuds_fit="too_loose")
    )
    assert result.spec.clearance == 1.5
