from src.argtable import parse


def test_flange_count_flag():
    specs = [
        {"name": "count", "flags": ["--count"], "kind": "int", "required": True},
        {"name": "verbose", "flags": ["-v"], "flag": True, "default": False},
    ]
    got = parse(["--count", "17", "-v"], specs)
    assert got == {"count": 17, "verbose": True}
