import time

from auth.security import (
    clear_auth_cookie,
    create_access_token,
    decode_access_token,
    get_password_hash,
    set_auth_cookie,
    verify_password,
)
from fastapi import Response


def test_hash_and_verify_correct():
    h = get_password_hash("my-password")
    assert verify_password("my-password", h) is True


def test_verify_wrong_password():
    h = get_password_hash("correct-password")
    assert verify_password("wrong-password", h) is False


def test_hash_not_plaintext():
    h = get_password_hash("secret")
    assert h != "secret"


def test_same_password_different_hashes():
    h1 = get_password_hash("password123")
    h2 = get_password_hash("password123")
    assert h1 != h2


def test_token_roundtrip():
    token = create_access_token("user@test.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.sub == "user@test.com"


def test_token_exp_in_future():
    token = create_access_token("user@test.com")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.exp is not None
    assert payload.exp > int(time.time())


def test_decode_invalid_token():
    result = decode_access_token("not-a-valid-jwt-token")
    assert result is None


def test_decode_empty_string():
    result = decode_access_token("")
    assert result is None


def test_set_auth_cookie():
    response = Response()
    set_auth_cookie(response, "my-token-abc")
    cookie_header = response.headers.get("set-cookie", "")
    assert "access_token=my-token-abc" in cookie_header
    assert "httponly" in cookie_header.lower()


def test_clear_auth_cookie():
    response = Response()
    clear_auth_cookie(response)
    cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in cookie_header
    assert "max-age=0" in cookie_header.lower()
