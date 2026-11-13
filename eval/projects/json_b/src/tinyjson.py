"""An iterative JSON reader with an explicit cursor. Independent of jmini."""


def decode(blob):
    cursor = _Cursor(blob)
    value = _read(cursor)
    cursor.skip_space()
    if cursor.remaining():
        raise SyntaxError("tinyjson: leftover input near %s" % cursor.position)
    return value


class _Cursor:
    def __init__(self, blob):
        self.blob = blob
        self.position = 0

    def remaining(self):
        return self.position < len(self.blob)

    def skip_space(self):
        while self.remaining() and self.blob[self.position] in " \n\r\t":
            self.position += 1

    def take(self):
        char = self.blob[self.position]
        self.position += 1
        return char


def _read(cursor):
    cursor.skip_space()
    if not cursor.remaining():
        raise SyntaxError("tinyjson: abrupt stop")
    char = cursor.blob[cursor.position]
    if char == "{":
        return _read_map(cursor)
    if char == "[":
        return _read_list(cursor)
    if char == '"':
        return _read_text(cursor)
    if char in "-0123456789":
        return _read_num(cursor)
    word = _read_word(cursor)
    if word == "true":
        return True
    if word == "false":
        return False
    if word == "null":
        return None
    raise SyntaxError("tinyjson: bad token at %s" % cursor.position)


def _read_map(cursor):
    cursor.take()
    out = {}
    cursor.skip_space()
    if cursor.remaining() and cursor.blob[cursor.position] == "}":
        cursor.take()
        return out
    while True:
        key = _read_text(cursor)
        cursor.skip_space()
        if not cursor.remaining() or cursor.take() != ":":
            raise SyntaxError("tinyjson: missing colon")
        out[key] = _read(cursor)
        cursor.skip_space()
        if not cursor.remaining():
            raise SyntaxError("tinyjson: abrupt stop")
        mark = cursor.take()
        if mark == "}":
            return out
        if mark != ",":
            raise SyntaxError("tinyjson: missing comma")


def _read_list(cursor):
    cursor.take()
    out = []
    cursor.skip_space()
    if cursor.remaining() and cursor.blob[cursor.position] == "]":
        cursor.take()
        return out
    while True:
        out.append(_read(cursor))
        cursor.skip_space()
        if not cursor.remaining():
            raise SyntaxError("tinyjson: abrupt stop")
        mark = cursor.take()
        if mark == "]":
            return out
        if mark != ",":
            raise SyntaxError("tinyjson: missing comma")


def _read_text(cursor):
    if cursor.take() != '"':
        raise SyntaxError("tinyjson: text expected")
    chars = []
    while cursor.remaining():
        char = cursor.take()
        if char == '"':
            return "".join(chars)
        if char == "\\":
            escaped = cursor.take()
            chars.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(escaped, escaped))
            continue
        chars.append(char)
    raise SyntaxError("tinyjson: text never closed")


def _read_num(cursor):
    start = cursor.position
    if cursor.blob[cursor.position] == "-":
        cursor.position += 1
    while cursor.remaining() and cursor.blob[cursor.position] in "0123456789.eE+-":
        # stop before a second sign that is not an exponent
        if cursor.blob[cursor.position] in "+-" and cursor.position > start + 1:
            prev = cursor.blob[cursor.position - 1]
            if prev not in "eE":
                break
        cursor.position += 1
    token = cursor.blob[start : cursor.position]
    if any(mark in token for mark in ".eE"):
        return float(token)
    return int(token)


def _read_word(cursor):
    start = cursor.position
    while cursor.remaining() and cursor.blob[cursor.position].isalpha():
        cursor.position += 1
    return cursor.blob[start : cursor.position]
