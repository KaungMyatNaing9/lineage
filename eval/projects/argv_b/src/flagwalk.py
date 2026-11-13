"""Hand-rolled argv walk. Not a table-driven parser."""


class Flags:
    def __init__(self):
        self.verbose = False
        self.jobs = 1
        self.paths = []

    def as_dict(self):
        return {"verbose": self.verbose, "jobs": self.jobs, "paths": list(self.paths)}


def walk(argv):
    flags = Flags()
    cursor = 0
    while cursor < len(argv):
        item = argv[cursor]
        if item in ("-v", "--verbose"):
            flags.verbose = True
            cursor += 1
            continue
        if item == "--jobs":
            cursor += 1
            if cursor >= len(argv):
                raise RuntimeError("flagwalk: --jobs needs a number")
            flags.jobs = _jobs(argv[cursor])
            cursor += 1
            continue
        if item.startswith("--jobs="):
            flags.jobs = _jobs(item.split("=", 1)[1])
            cursor += 1
            continue
        if item.startswith("-"):
            raise RuntimeError("flagwalk: cannot handle %s" % item)
        flags.paths.append(item)
        cursor += 1
    if flags.jobs < 1 or flags.jobs > 64:
        raise RuntimeError("flagwalk: jobs out of range")
    return flags.as_dict()


def _jobs(text):
    try:
        return int(text)
    except ValueError as exc:
        raise RuntimeError("flagwalk: bad jobs value") from exc
