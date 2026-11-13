from __future__ import annotations

from lineage.winnow import digest_gram, select_window_minima


def test_rightmost_minimum_in_each_window() -> None:
    # Windows of 3: [3,1,4] -> 1 at index 1; [1,4,1] -> rightmost 1 at index 3;
    # [4,1,5] -> 1 at index 3.
    assert select_window_minima([3, 1, 4, 1, 5], 3) == [1, 3]


def test_minimum_slides_out_of_the_window() -> None:
    assert select_window_minima([1, 5, 4, 3], 3) == [0, 3]


def test_ties_keep_the_rightmost() -> None:
    assert select_window_minima([2, 2, 2], 2) == [1, 2]


def test_window_wider_than_the_sequence_selects_one_minimum() -> None:
    assert select_window_minima([4, 1, 3], 10) == [1]


def test_digest_is_stable() -> None:
    assert digest_gram(("def", "ID0", "(")) == digest_gram(("def", "ID0", "("))
    assert digest_gram(("def", "ID0")) != digest_gram(("def", "ID1"))
