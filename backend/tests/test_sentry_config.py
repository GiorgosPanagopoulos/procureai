import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import sentry_sdk
from core.sentry import _before_send_transaction, _scrub_dict, init_sentry
from structlog.testing import capture_logs

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_scrub_dict_password_key():
    result = _scrub_dict({"password": "secret123", "name": "Alice"})
    assert result["password"] == "[Filtered]"
    assert result["name"] == "Alice"


def test_scrub_dict_nested():
    data = {"user": {"token": "abc", "name": "Bob"}}
    result = _scrub_dict(data)
    assert result["user"]["token"] == "[Filtered]"
    assert result["user"]["name"] == "Bob"


def test_scrub_dict_list_of_dicts():
    data = [{"password": "x"}, {"authorization": "Bearer y", "email": "a@b.com"}]
    result = _scrub_dict(data)
    assert result[0]["password"] == "[Filtered]"
    assert result[1]["authorization"] == "[Filtered]"
    assert result[1]["email"] == "a@b.com"


def test_scrub_dict_non_sensitive_preserved():
    data = {"name": "Test", "category": "Electronics", "rating": 4.5}
    result = _scrub_dict(data)
    assert result == data


def test_before_send_transaction_health_transaction_name():
    event = {"transaction": "/health"}
    assert _before_send_transaction(event, {}) is None


def test_before_send_transaction_health_url():
    event = {"transaction": "/anything", "request": {"url": "http://test/health"}}
    assert _before_send_transaction(event, {}) is None


def test_before_send_transaction_normal_returns_event():
    event = {"transaction": "/api/suppliers", "request": {"url": "http://test/api/suppliers"}}
    result = _before_send_transaction(event, {})
    assert result is event


@pytest.mark.parametrize("dsn", [None, "", "   ", "\n\t"])
def test_init_sentry_skips_missing_dsn(dsn):
    with patch("core.sentry.sentry_sdk.init") as mock_init, capture_logs() as logs:
        init_sentry(dsn, "production", "procureai@test")
    mock_init.assert_not_called()
    assert logs == [{"event": "sentry_disabled", "reason": "empty_dsn", "log_level": "warning"}]


def test_init_sentry_survives_init_error_and_logs_type_only():
    dsn = "https://secretkey@o0.ingest.sentry.io/1"
    with (
        patch("core.sentry.sentry_sdk.init", side_effect=ValueError(dsn)) as mock_init,
        capture_logs() as logs,
    ):
        init_sentry(dsn, "production", "procureai@test")
    mock_init.assert_called_once()
    assert logs == [
        {"event": "sentry_init_failed", "error_type": "ValueError", "log_level": "warning"}
    ]


def test_init_sentry_survives_malformed_dsn_with_real_sdk():
    with capture_logs() as logs:
        init_sentry("not-a-dsn", "production", "procureai@test")
    assert logs == [{"event": "sentry_init_failed", "error_type": "BadDsn", "log_level": "warning"}]
    assert not sentry_sdk.get_client().is_active()


@pytest.mark.parametrize("dsn", ["", "   ", "not-a-dsn"])
def test_app_starts_with_unusable_dsn(dsn):
    # Import main in a fresh interpreter: init_sentry runs at import time there,
    # which is where the 3 Oct BadDsn crash happened.
    env = {**os.environ, "SENTRY_DSN": dsn}
    result = subprocess.run(
        [sys.executable, "-c", "import main; assert main.app is not None"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    expected = "sentry_disabled" if not dsn.strip() else "sentry_init_failed"
    assert expected in result.stdout + result.stderr
    if dsn.strip():
        assert dsn not in result.stdout + result.stderr


def test_init_sentry_calls_init_with_stripped_dsn():
    dsn = "https://abc123@o0.ingest.sentry.io/1"
    with patch("core.sentry.sentry_sdk.init") as mock_init:
        init_sentry(f"  {dsn}\n", "production", "procureai@test")
    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == dsn
    assert kwargs["environment"] == "production"
    assert kwargs["release"] == "procureai@test"
