from security.pii import redact_pii


def test_redact_email():
    text, count = redact_pii("Contact us at test@example.com for more info.")
    assert "[EMAIL_REDACTED]" in text
    assert count == 1


def test_redact_afm():
    text, count = redact_pii("My AFM is 123456789.")
    assert "[AFM_REDACTED]" in text
    assert count == 1


def test_redact_amka():
    text, count = redact_pii("AMKA: 12345678901")
    assert "[AMKA_REDACTED]" in text
    assert count == 1


def test_redact_greek_mobile():
    text, count = redact_pii("Call me at 6912345678.")
    assert "[PHONE_REDACTED]" in text
    assert count == 1


def test_no_pii():
    text, count = redact_pii("Compare all bids for office equipment.")
    assert count == 0
    assert text == "Compare all bids for office equipment."


def test_multiple_pii():
    text, count = redact_pii("Email: foo@bar.com, AFM: 987654321")
    assert "[EMAIL_REDACTED]" in text
    assert "[AFM_REDACTED]" in text
    assert count == 2
