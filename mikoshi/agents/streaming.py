from dataclasses import dataclass


@dataclass(frozen=True)
class StreamEvent:
    type: str
    data: dict


STREAM_DONE = StreamEvent(type="done", data={})
