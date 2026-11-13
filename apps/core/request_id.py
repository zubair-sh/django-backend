import contextvars
import re
import uuid

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_VALID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str | None) -> tuple[str, contextvars.Token]:
    """Use the caller's ID if it looks safe (so a frontend can correlate), otherwise make a new one."""
    request_id = value if value and _VALID.match(value) else uuid.uuid4().hex
    return request_id, _request_id.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    _request_id.reset(token)
