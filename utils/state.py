import asyncio

queue = asyncio.Queue()
active_tasks = {}
pending_selections = {}
cancel_flags = {}
active_process = None
current_task_id = None
