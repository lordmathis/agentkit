import asyncio
from dataclasses import dataclass


@dataclass
class StreamEvent:
    type: str
    data: dict


STREAM_DONE = StreamEvent(type="done", data={})
