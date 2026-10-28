from datetime import UTC, datetime
from threading import Lock
from typing import Protocol

from knowledge_hub.core.clock import Clock, SystemClock
from knowledge_hub.core.errors import (
    ClockRegression,
    InvalidClock,
    SequenceExhausted,
    TimestampOutOfRange,
)
from knowledge_hub.core.identifiers import DocumentId

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_TIMESTAMP_LIMIT = 1 << 41
_SEQUENCE_LIMIT = 1 << 12


class IdGenerator(Protocol):
    def next_id(self) -> DocumentId: ...


class SnowflakeIdGenerator:
    """One shared instance per worker; deployment assigns distinct worker IDs."""

    def __init__(
        self, *, worker_id: int, offset_ms: int = 1704067200000, clock: Clock | None = None
    ) -> None:
        if type(worker_id) is not int or not 0 <= worker_id <= 1023:
            raise ValueError("worker_id must be an integer between 0 and 1023")
        if type(offset_ms) is not int or offset_ms < 0:
            raise ValueError("offset_ms must be a nonnegative integer")
        self._worker_id = worker_id
        self._offset_ms = offset_ms
        self._clock = clock if clock is not None else SystemClock()
        self._last_ms: int | None = None
        self._sequence = 0
        self._lock = Lock()

    def next_id(self) -> DocumentId:
        with self._lock:
            current_ms = self._elapsed_ms()
            if self._last_ms is not None and current_ms < self._last_ms:
                raise ClockRegression("Clock moved backwards; refusing to repeat document IDs")
            sequence = self._sequence + 1 if current_ms == self._last_ms else 0
            if sequence >= _SEQUENCE_LIMIT:
                raise SequenceExhausted("Worker exhausted 4096 IDs in one millisecond")
            value = current_ms << 22 | self._worker_id << 12 | sequence
            self._last_ms, self._sequence = current_ms, sequence
            return DocumentId(str(value))

    def _elapsed_ms(self) -> int:
        now = self._clock.now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise InvalidClock("ID clock must return a timezone-aware datetime")
        delta = now - _UNIX_EPOCH
        unix_ms = (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
        elapsed_ms = unix_ms - self._offset_ms
        if not 0 <= elapsed_ms < _TIMESTAMP_LIMIT:
            raise TimestampOutOfRange("ID timestamp is outside the signed BIGINT layout")
        return elapsed_ms
