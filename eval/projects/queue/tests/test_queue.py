from src.queue import LinkedQueue


def test_fifo_order():
    queue = LinkedQueue()
    queue.enqueue("alpha")
    queue.enqueue("beta")
    assert queue.drain() == ["alpha", "beta"]
