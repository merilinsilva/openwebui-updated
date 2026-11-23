"""CHOn (T17): specific error details and empty-reply detection.

WG-AI-PLA-00002, section 8 / PP-05: every error names the cause and the next
step, and CHOn never ends a turn with an empty reply.

- Provider errors keep their HTTP status and error code (content_filter,
  rate_limit_exceeded, context_length_exceeded, ...) so the frontend can show
  a specific message instead of a generic one.
- A finished turn with no answer text (and no generated files) gets an
  explicit error instead of an empty bubble.

The error object sent to the frontend stays backward compatible:
``{'content': <text or provider dict>, 'status'?: int, 'code'?: str,
'finish_reason'?: str}``. Older clients only read ``content``.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

from open_webui.utils.misc import get_output_text

log = logging.getLogger(__name__)

EMPTY_REPLY_CODE = 'empty_response'


class ProviderError(Exception):
    """An upstream provider error that keeps its HTTP status and error code."""

    def __init__(self, detail: str, status: Optional[int] = None, code: Optional[str] = None):
        super().__init__(detail)
        self.detail = detail
        self.status = status
        self.code = code


def _find_code(value: Any, depth: int = 0) -> Optional[str]:
    """Return the most specific error code in a provider error body."""
    if depth > 4 or not isinstance(value, dict):
        return None
    for key in ('innererror', 'inner_error', 'error'):
        nested = _find_code(value.get(key), depth + 1)
        if nested:
            return nested
    for key in ('code', 'type'):
        code = value.get(key)
        if isinstance(code, str) and code:
            return code
    return None


def get_response_error_info(response: object) -> dict:
    """Status and error code of a provider error response (JSONResponse-like)."""
    info: dict = {}
    status = getattr(response, 'status_code', None)
    if isinstance(status, int):
        info['status'] = status
    try:
        from open_webui.utils.misc import JSONCodec  # local import: avoid cycles

        body = response.body  # type: ignore[attr-defined]
        if not isinstance(body, str):
            body = body.decode('utf-8', 'replace')
        code = _find_code(JSONCodec.loads(body))
        if code:
            info['code'] = code
    except Exception:
        pass
    return info


def build_error(content: Any, status: Optional[int] = None, code: Optional[str] = None, **extra) -> dict:
    """Error object for message['error'] / chat:message:error events."""
    error: dict = {'content': content}
    if status is not None:
        error['status'] = status
    if not code and isinstance(content, dict):
        code = _find_code(content)
    if code:
        error['code'] = code
    error.update({k: v for k, v in extra.items() if v is not None})
    return error


def error_from_exception(e: Exception) -> dict:
    """Error object from an exception raised while processing a chat."""
    status = getattr(e, 'status', None) or getattr(e, 'status_code', None)
    detail = getattr(e, 'detail', None)
    content = detail if isinstance(detail, (str, dict)) else str(e)
    return build_error(content, status=status if isinstance(status, int) else None, code=getattr(e, 'code', None))


class TurnState:
    """Tracks what one assistant turn produced, for the empty-reply check."""

    def __init__(self):
        self.error_emitted = False
        self.files_emitted = False
        self.finish_reason: Optional[str] = None

    def note_finish_reason(self, finish_reason: Optional[str]):
        if finish_reason:
            self.finish_reason = finish_reason


_ERROR_EVENT_TYPES = {'chat:message:error'}
_FILE_EVENT_TYPES = {'files', 'chat:message:files', 'embeds', 'chat:message:embeds'}


def track_turn(
    event_emitter: Optional[Callable[[dict], Awaitable[Any]]], state: TurnState
) -> Optional[Callable[[dict], Awaitable[Any]]]:
    """Wrap an event emitter so the turn state sees errors and generated files."""
    if not event_emitter:
        return event_emitter

    async def emitter(event: dict):
        try:
            event_type = event.get('type')
            data = event.get('data') or {}
            if event_type in _ERROR_EVENT_TYPES or (
                event_type == 'chat:completion' and isinstance(data, dict) and data.get('error')
            ):
                state.error_emitted = True
            elif event_type in _FILE_EVENT_TYPES:
                state.files_emitted = True
        except Exception:
            pass
        return await event_emitter(event)

    return emitter


def empty_reply_error(output: Optional[list], state: TurnState, text: Optional[str] = None) -> Optional[dict]:
    """Error object when a finished turn has no answer text, else None."""
    if state.error_emitted or state.files_emitted:
        return None

    if text is None:
        text = get_output_text(output or [])
    if (text or '').strip():
        return None

    items = output or []
    used_tools = any(isinstance(i, dict) and i.get('type') == 'function_call' for i in items)
    reasoned = any(isinstance(i, dict) and i.get('type') == 'reasoning' for i in items)
    finish_reason = state.finish_reason

    if finish_reason == 'content_filter':
        content = 'The AI service blocked this answer with its safety filter.'
    elif finish_reason == 'length':
        content = 'The answer was cut off before CHOn could write it.'
    elif used_tools:
        content = 'CHOn used its tools but did not write an answer.'
    elif reasoned:
        content = 'CHOn thought about the question but did not write an answer.'
    else:
        content = 'CHOn did not return an answer.'

    log.warning('Empty assistant reply (finish_reason=%s, tools=%s)', finish_reason, used_tools)
    return build_error(content, code=EMPTY_REPLY_CODE, finish_reason=finish_reason)
