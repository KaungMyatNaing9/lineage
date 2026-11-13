"""Spec-table argument reader."""


def parse(argv, specs):
    result = {spec["name"]: spec.get("default") for spec in specs}
    by_flag = {}
    for spec in specs:
        for flag in spec.get("flags", []):
            by_flag[flag] = spec
    positionals = [spec for spec in specs if spec.get("positional")]
    pos_index = 0
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in by_flag:
            spec = by_flag[token]
            if spec.get("flag"):
                result[spec["name"]] = True
                index += 1
                continue
            if index + 1 >= len(argv):
                raise SystemExit("argtable: missing value for %s" % token)
            result[spec["name"]] = _coerce(argv[index + 1], spec.get("kind", "str"))
            index += 2
            continue
        if token.startswith("-"):
            raise SystemExit("argtable: unknown flag %s" % token)
        if pos_index >= len(positionals):
            raise SystemExit("argtable: unexpected token %s" % token)
        spec = positionals[pos_index]
        result[spec["name"]] = _coerce(token, spec.get("kind", "str"))
        pos_index += 1
        index += 1
    for spec in specs:
        if spec.get("required") and result[spec["name"]] is None:
            raise SystemExit("argtable: missing required %s" % spec["name"])
    return result


def _coerce(text, kind):
    if kind == "int":
        try:
            return int(text)
        except ValueError as exc:
            raise SystemExit("argtable: not an int: %s" % text) from exc
    return text
