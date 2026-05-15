from core.sentry import _before_send_transaction, _scrub_dict


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
