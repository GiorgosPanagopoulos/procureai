import anthropic as anthropic_sdk
from config import settings
from langchain_anthropic import ChatAnthropic
from openai import OpenAI
from pydantic import SecretStr

from llm.callbacks import _UsageCallback
from llm.pricing import MODEL_NAME

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
_raw_anthropic = anthropic_sdk.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

claude_llm = ChatAnthropic(  # type: ignore[call-arg]
    model=MODEL_NAME,
    api_key=SecretStr(settings.ANTHROPIC_API_KEY),
    temperature=0,
    max_tokens=1024,
    callbacks=[_UsageCallback()],
)
