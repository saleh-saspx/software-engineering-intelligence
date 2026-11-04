import pytest

from profile import display_name, parse_age


def test_parse_age_accepts_valid_input():
    assert parse_age(" 42 ") == 42


def test_parse_age_rejects_too_large():
    with pytest.raises(ValueError):
        parse_age("200")


def test_display_name_trims():
    assert display_name(" Ada ", " Lovelace ") == "Ada Lovelace"
