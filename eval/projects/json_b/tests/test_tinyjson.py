from src.tinyjson import decode


def test_widget_record():
    assert decode('{"widget":"sprocket","qty":14}') == {"widget": "sprocket", "qty": 14}


def test_list_of_flags():
    assert decode("[false, null, true]") == [False, None, True]
