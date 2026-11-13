from src.stats import median, variance


def test_even_median_and_variance():
    assert median([4, 1, 9, 2]) == 3
    assert variance([2, 4, 4, 4, 5, 5, 7, 9]) == 4.571428571428571
