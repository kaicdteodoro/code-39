import pytest

from code39.service import build_batch_plan, find_duplicates, next_available_reference


def test_build_batch_plan_full_range_with_limit() -> None:
    plan = build_batch_plan(limit=5)
    assert plan.quantity == 5
    assert plan.first_reference == "ATL001"
    assert plan.last_reference == "ATL005"


def test_build_batch_plan_single_reference() -> None:
    plan = build_batch_plan(reference="ATL125")
    assert plan.references == ["ATL125"]


def test_build_batch_plan_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        build_batch_plan(start=10, end=5)


def test_build_batch_plan_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        build_batch_plan(start=0, end=10)

    with pytest.raises(ValueError):
        build_batch_plan(start=1, end=501)


def test_build_batch_plan_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        build_batch_plan(limit=0)


def test_find_duplicates_returns_existing_values() -> None:
    duplicates = find_duplicates(["ATL001", "ATL002", "ATL003"], {"ATL002"})
    assert duplicates == ["ATL002"]


def test_next_available_reference_returns_first_gap() -> None:
    assert next_available_reference({"ATL001", "ATL002"}) == "ATL003"
