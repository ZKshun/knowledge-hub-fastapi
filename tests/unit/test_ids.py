from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone

import pytest

from knowledge_hub.core.clock import SystemClock
from knowledge_hub.core.errors import (
    ClockRegression,
    InvalidClock,
    SequenceExhausted,
    TimestampOutOfRange,
)
from knowledge_hub.core.ids import SnowflakeIdGenerator

EPOCH_MS = 1704067200000
EPOCH = datetime(2024, 1, 1, tzinfo=UTC)


class ControlledClock:
    def __init__(self, now: datetime = EPOCH + timedelta(milliseconds=123)) -> None:
        self.value = now

    def now(self) -> datetime:
        return self.value


def test_bit_layout_matches_actual_legacy_worker_seven() -> None:
    generator = SnowflakeIdGenerator(worker_id=7, clock=ControlledClock())
    assert generator.next_id() == "515928064"
    assert generator.next_id() == "515928065"


def test_all_same_millisecond_ids_are_distinct_then_fail_without_wrapping() -> None:
    clock = ControlledClock()
    generator = SnowflakeIdGenerator(worker_id=1, clock=clock)
    ids = [generator.next_id() for _ in range(4096)]
    assert len(set(ids)) == 4096
    assert all(value.isdecimal() and int(value) <= 2**63 - 1 for value in ids)
    with pytest.raises(SequenceExhausted):
        generator.next_id()
    clock.value += timedelta(milliseconds=1)
    assert generator.next_id() not in ids


def test_each_worker_including_zero_and_1023_has_distinct_bits() -> None:
    ids = [
        SnowflakeIdGenerator(worker_id=w, clock=ControlledClock()).next_id() for w in range(1024)
    ]
    assert len(set(ids)) == 1024
    assert [int(value) >> 12 & 1023 for value in ids] == list(range(1024))


def test_regression_fails_and_recovery_does_not_repeat_previous_id() -> None:
    clock = ControlledClock()
    generator = SnowflakeIdGenerator(worker_id=1, clock=clock)
    previous = generator.next_id()
    clock.value -= timedelta(milliseconds=1)
    with pytest.raises(ClockRegression):
        generator.next_id()
    clock.value += timedelta(milliseconds=1)
    assert int(generator.next_id()) == int(previous) + 1


def test_shared_generator_is_safe_for_concurrent_callers() -> None:
    generator = SnowflakeIdGenerator(worker_id=5, clock=ControlledClock())
    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(lambda _: generator.next_id(), range(1024)))
    assert len(set(values)) == 1024


def test_maximum_layout_fits_signed_bigint() -> None:
    clock = ControlledClock(EPOCH + timedelta(milliseconds=2**41 - 1))
    generator = SnowflakeIdGenerator(worker_id=1023, clock=clock)
    values = [generator.next_id() for _ in range(4096)]
    assert int(values[-1]) == 2**63 - 1


@pytest.mark.parametrize("delta", [-1, 2**41])
def test_timestamp_outside_layout_fails(delta: int) -> None:
    generator = SnowflakeIdGenerator(
        worker_id=1, clock=ControlledClock(EPOCH + timedelta(milliseconds=delta))
    )
    with pytest.raises(TimestampOutOfRange):
        generator.next_id()


def test_naive_clock_is_rejected() -> None:
    generator = SnowflakeIdGenerator(worker_id=1, clock=ControlledClock(datetime(2026, 1, 1)))
    with pytest.raises(InvalidClock):
        generator.next_id()


def test_aware_offsets_and_submillisecond_precision_are_consistent() -> None:
    clock = ControlledClock(
        (EPOCH + timedelta(milliseconds=123, microseconds=999)).astimezone(
            timezone(timedelta(hours=8))
        )
    )
    assert SnowflakeIdGenerator(worker_id=7, clock=clock).next_id() == "515928064"


@pytest.mark.parametrize("worker", [-1, 1024, True])
def test_invalid_worker_is_rejected(worker: int) -> None:
    with pytest.raises(ValueError):
        SnowflakeIdGenerator(worker_id=worker, clock=ControlledClock())


@pytest.mark.parametrize("offset", [-1, True])
def test_invalid_offset_is_rejected(offset: int) -> None:
    with pytest.raises(ValueError):
        SnowflakeIdGenerator(worker_id=1, offset_ms=offset, clock=ControlledClock())


def test_offset_is_configurable() -> None:
    generator = SnowflakeIdGenerator(worker_id=7, offset_ms=EPOCH_MS + 123, clock=ControlledClock())
    assert generator.next_id() == str(7 << 12)


def test_system_clock_produces_current_utc_time() -> None:
    before = datetime.now(UTC)
    actual = SystemClock().now()
    after = datetime.now(UTC)
    assert before <= actual <= after
    assert actual.tzinfo == UTC
