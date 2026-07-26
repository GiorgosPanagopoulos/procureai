import anthropic as anthropic_sdk
from config import settings
from pydantic import SecretStr
from utils.lazy import _lazy_proxy

from llm.callbacks import _UsageCallback
from llm.pricing import MODEL_NAME


def _create_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _create_raw_anthropic():
    return anthropic_sdk.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _create_raw_anthropic_async():
    return anthropic_sdk.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def _create_claude_llm():
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(  # type: ignore[call-arg]
        model=MODEL_NAME,
        api_key=SecretStr(settings.ANTHROPIC_API_KEY),
        temperature=0,
        max_tokens=1024,
        callbacks=[_UsageCallback()],
    )


openai_client = _lazy_proxy(_create_openai_client)
_raw_anthropic = _lazy_proxy(_create_raw_anthropic)
_raw_anthropic_async = _lazy_proxy(_create_raw_anthropic_async)
claude_llm = _lazy_proxy(_create_claude_llm)
