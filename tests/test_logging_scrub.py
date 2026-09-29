from app.logging_config import scrub_event


def test_scrub_event_redacts_nested_values() -> None:
    event = {
        "event": "response_sent",
        "payload": {"messages": ["Email: student@example.com", {"note": "CCCD: 012345678901"}]},
    }

    scrubbed = scrub_event(None, "info", event)

    assert "student@example.com" not in str(scrubbed)
    assert "012345678901" not in str(scrubbed)
    assert "[REDACTED_EMAIL]" in str(scrubbed)
    assert "[REDACTED_CCCD]" in str(scrubbed)
