import anthropic as anthropic_sdk
from config import settings
from pydantic import SecretStr

from llm.callbacks import _UsageCallback
from llm.pricing import MODEL_NAME


def _lazy_proxy(factory):
    class LazyProxy:
        def __init__(self):
            self._factory = factory
            self._obj = None

        def _get(self):
            if self._obj is None:
                self._obj = self._factory()
            return self._obj

        def __getattr__(self, name):
            return getattr(self._get(), name)

        def __call__(self, *args, **kwargs):
            return self._get()(*args, **kwargs)

        def __repr__(self):
            return f"<LazyProxy {self._factory.__name__}>"

        def __dir__(self):
            return dir(self._get())

    return LazyProxy()


def _create_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _create_raw_anthropic():
    return anthropic_sdk.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


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
claude_llm = _lazy_proxy(_create_claude_llm)
