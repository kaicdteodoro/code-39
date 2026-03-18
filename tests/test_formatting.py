from code39.formatting import format_reference, parse_reference


def test_format_reference_adds_prefix_and_zero_padding() -> None:
    assert format_reference(1) == "ATL001"
    assert format_reference(500) == "ATL500"


def test_parse_reference_returns_numeric_value() -> None:
    assert parse_reference("ATL125") == 125


def test_parse_reference_rejects_invalid_prefix() -> None:
    try:
        parse_reference("ABC125")
    except ValueError as error:
        assert "must start" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid prefix.")


def test_parse_reference_rejects_out_of_range_values() -> None:
    for reference in ("ATL000", "ATL501"):
        try:
            parse_reference(reference)
        except ValueError as error:
            assert "between" in str(error)
        else:
            raise AssertionError("Expected ValueError for out-of-range reference.")


def test_parse_reference_rejects_invalid_width() -> None:
    try:
        parse_reference("ATL01")
    except ValueError as error:
        assert "format" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid width.")
