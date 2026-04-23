import pytest
from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _StrictSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str

    @field_validator("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


def test_missing_anthropic_key():
    with pytest.raises(ValidationError):
        _StrictSettings(ANTHROPIC_API_KEY="", OPENAI_API_KEY="sk-test")


def test_valid_settings():
    s = _StrictSettings(ANTHROPIC_API_KEY="sk-ant-test", OPENAI_API_KEY="sk-test")
    assert s.ANTHROPIC_API_KEY == "sk-ant-test"


def test_missing_openai_key():
    with pytest.raises(ValidationError):
        _StrictSettings(ANTHROPIC_API_KEY="sk-ant-test", OPENAI_API_KEY="   ")
