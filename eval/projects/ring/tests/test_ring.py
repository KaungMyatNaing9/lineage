from src.ring import Ring


def test_wraps_and_reports_latest():
    ring = Ring(3)
    for sample in (10, 20, 30, 40):
        ring.push(sample)
    assert ring.latest(2) == [40, 30]
    assert ring.mean() == (40 + 30 + 20) / 3
