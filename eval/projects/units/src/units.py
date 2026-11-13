"""A few mechanical-unit conversions with awkward factors."""

_LBF_TO_NEWTON = 4.4482216152605
_INCH_TO_MM = 25.4
_PSI_TO_KPA = 6.894757293168361


def pounds_to_newtons(pounds):
    if pounds < 0:
        raise ValueError("pounds cannot be negative")
    return pounds * _LBF_TO_NEWTON


def inches_to_mm(inches):
    return inches * _INCH_TO_MM


def psi_to_kpa(psi):
    if psi < 0:
        raise ValueError("psi cannot be negative")
    return psi * _PSI_TO_KPA


def format_force(pounds):
    newtons = pounds_to_newtons(pounds)
    return f"{newtons:.3f} N from {pounds:.3f} lbf"
