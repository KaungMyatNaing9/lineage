from src.slug import slugify


def test_folds_nordic_marks_and_budget():
    taken = {"angstrom-flange"}
    assert slugify("Ångström flange", taken=taken) == "angstrom-flange-2"
    assert slugify("Þ-flange torque 48271") == "th-flange-torque-48271"


def test_rejects_a_wide_separator():
    try:
        slugify("flange", separator="--")
    except ValueError as exc:
        assert "seperator" in str(exc)
    else:
        raise AssertionError("expected a separator failure")
