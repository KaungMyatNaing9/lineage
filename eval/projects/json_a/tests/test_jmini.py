from src.jmini import loads


def test_object_with_flange_id():
    assert loads('{"flange": 48271, "ok": true}') == {"flange": 48271, "ok": True}


def test_nested_array():
    assert loads('[1, {"name": "jmini-sample"}]') == [1, {"name": "jmini-sample"}]
