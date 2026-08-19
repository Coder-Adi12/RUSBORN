from datetime import UTC, datetime, timedelta

from services.campaign_orchestrator import build_dispatch_failure_update


def test_dispatch_failure_schedules_a_bounded_retry() -> None:
    now = datetime(2026, 8, 19, 8, 0, tzinfo=UTC)

    update = build_dispatch_failure_update(
        attempt_number=1,
        max_attempts=3,
        retry_delay_minutes=15,
        now=now,
    )

    assert update == {
        "attempt_count": 1,
        "status": "FAILED",
        "last_error": "Failed to dispatch SIP call",
        "last_outcome": "FAILED",
        "next_attempt_at": (now + timedelta(minutes=15)).isoformat(),
    }


def test_dispatch_failure_exhausts_contact_at_retry_limit() -> None:
    update = build_dispatch_failure_update(
        attempt_number=3,
        max_attempts=3,
        retry_delay_minutes=15,
        now=datetime(2026, 8, 19, 8, 0, tzinfo=UTC),
    )

    assert update == {
        "attempt_count": 3,
        "status": "EXHAUSTED",
        "last_error": "Failed to dispatch SIP call",
        "last_outcome": "FAILED",
        "next_attempt_at": None,
    }
