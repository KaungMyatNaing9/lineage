"""Fixed ring of sensor samples."""


class Ring:
    def __init__(self, capacity):
        if capacity < 2:
            raise ValueError("ring capacity must be at least 2")
        self.slots = [None] * capacity
        self.head = 0
        self.filled = 0

    def push(self, sample):
        self.slots[self.head] = sample
        self.head = (self.head + 1) % len(self.slots)
        if self.filled < len(self.slots):
            self.filled += 1

    def latest(self, count):
        if count > self.filled:
            count = self.filled
        out = []
        index = (self.head - 1) % len(self.slots)
        while len(out) < count:
            out.append(self.slots[index])
            index = (index - 1) % len(self.slots)
        return out

    def mean(self):
        if self.filled == 0:
            raise ValueError("ring is empty")
        total = 0
        seen = 0
        index = (self.head - 1) % len(self.slots)
        while seen < self.filled:
            total += self.slots[index]
            seen += 1
            index = (index - 1) % len(self.slots)
        return total / self.filled
