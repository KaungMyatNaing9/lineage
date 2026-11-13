"""A small recursive JSON reader. Errors name this reader on purpose."""


def loads(text):
    parser = _Parser(text)
    value = parser.parse_value()
    parser.skip()
    if not parser.done():
        raise ValueError("jmini: trailing data at %s" % parser.index)
    return value


class _Parser:
    def __init__(self, text):
        self.text = text
        self.index = 0

    def done(self):
        return self.index >= len(self.text)

    def skip(self):
        while not self.done() and self.text[self.index] in " \t\r\n":
            self.index += 1

    def peek(self):
        self.skip()
        if self.done():
            raise ValueError("jmini: unexpected end at %s" % self.index)
        return self.text[self.index]

    def parse_value(self):
        char = self.peek()
        if char == "{":
            return self.parse_object()
        if char == "[":
            return self.parse_array()
        if char == '"':
            return self.parse_string()
        if char == "t":
            return self.consume("true", True)
        if char == "f":
            return self.consume("false", False)
        if char == "n":
            return self.consume("null", None)
        if char == "-" or char.isdigit():
            return self.parse_number()
        raise ValueError("jmini: expected value at %s" % self.index)

    def parse_object(self):
        self.index += 1
        result = {}
        self.skip()
        if self.peek() == "}":
            self.index += 1
            return result
        while True:
            key = self.parse_string()
            if self.peek() != ":":
                raise ValueError("jmini: expected colon at %s" % self.index)
            self.index += 1
            result[key] = self.parse_value()
            self.skip()
            if self.peek() == "}":
                self.index += 1
                return result
            if self.peek() != ",":
                raise ValueError("jmini: expected comma at %s" % self.index)
            self.index += 1

    def parse_array(self):
        self.index += 1
        result = []
        self.skip()
        if self.peek() == "]":
            self.index += 1
            return result
        while True:
            result.append(self.parse_value())
            self.skip()
            if self.peek() == "]":
                self.index += 1
                return result
            if self.peek() != ",":
                raise ValueError("jmini: expected comma at %s" % self.index)
            self.index += 1

    def parse_string(self):
        if self.peek() != '"':
            raise ValueError("jmini: expected string at %s" % self.index)
        self.index += 1
        chars = []
        while not self.done():
            char = self.text[self.index]
            self.index += 1
            if char == '"':
                return "".join(chars)
            if char == "\\":
                chars.append(self._escape())
                continue
            chars.append(char)
        raise ValueError("jmini: unterminated string at %s" % self.index)

    def _escape(self):
        if self.done():
            raise ValueError("jmini: bad escape at %s" % self.index)
        char = self.text[self.index]
        self.index += 1
        mapping = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
        if char not in mapping:
            raise ValueError("jmini: bad escape at %s" % self.index)
        return mapping[char]

    def parse_number(self):
        start = self.index
        if self.text[self.index] == "-":
            self.index += 1
        while not self.done() and self.text[self.index].isdigit():
            self.index += 1
        if not self.done() and self.text[self.index] == ".":
            self.index += 1
            while not self.done() and self.text[self.index].isdigit():
                self.index += 1
        token = self.text[start : self.index]
        if "." in token:
            return float(token)
        return int(token)

    def consume(self, literal, value):
        if not self.text.startswith(literal, self.index):
            raise ValueError("jmini: expected value at %s" % self.index)
        self.index += len(literal)
        return value
