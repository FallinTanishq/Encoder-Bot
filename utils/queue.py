import asyncio

encode_queue = asyncio.Queue()
active_task = None
active_cancel_event = None
queue_items = []


def get_queue_position():
    return encode_queue.qsize()
