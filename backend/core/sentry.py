from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

_SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "password", "passwd", "token", "secret",
    "authorization", "auth", "credential", "private_key",
})


def _scrub_dict(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: "[Filtered]" if k.lower() in _SENSITIVE_KEYS else _scrub_dict(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_dict(i) for i in obj]
    return obj


def _before_send(event: Event, hint: Hint) -> Event | None:
    for exc in (event.get("exception") or {}).get("values") or []:
        for frame in (exc.get("stacktrace") or {}).get("frames") or []:
            if "vars" in frame:
                frame["vars"] = _scrub_dict(frame["vars"])
    return event


def _before_send_transaction(event: Event, hint: Hint) -> Event | None:
    transaction_name = str(event.get("transaction", ""))
    request = event.get("request")
    url = str(request.get("url", "")) if isinstance(request, dict) else ""
    if url.endswith("/health") or url.endswith("/api/health"):
        return None
    if transaction_name in {"/health", "/api/health"}:
        return None
    return event


def init_sentry(dsn: str | None, environment: str, release: str) -> None:
    if not dsn:
        return
    is_prod = environment == "production"
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.3 if is_prod else 1.0,
        profiles_sample_rate=0.1 if is_prod else 1.0,
        send_default_pii=False,
        enable_tracing=True,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        auto_enabling_integrations=False,
        before_send=_before_send,
        before_send_transaction=_before_send_transaction,
    )
