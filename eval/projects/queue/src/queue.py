"""Singly linked queue."""


class _Node:
    def __init__(self, value, nxt):
        self.value = value
        self.nxt = nxt


class LinkedQueue:
    def __init__(self):
        self.front = None
        self.back = None
        self.size = 0

    def enqueue(self, value):
        node = _Node(value, None)
        if self.back is None:
            self.front = node
            self.back = node
        else:
            self.back.nxt = node
            self.back = node
        self.size += 1

    def dequeue(self):
        if self.front is None:
            raise IndexError("linked queue is empty")
        node = self.front
        self.front = node.nxt
        if self.front is None:
            self.back = None
        self.size -= 1
        return node.value

    def drain(self):
        values = []
        while self.front is not None:
            values.append(self.dequeue())
        return values
