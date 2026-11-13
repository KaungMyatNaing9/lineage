from src.flagwalk import walk


def test_jobs_and_paths():
    got = walk(["--jobs", "4", "-v", "src/main.py"])
    assert got["jobs"] == 4
    assert got["verbose"] is True
    assert got["paths"] == ["src/main.py"]
