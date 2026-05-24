from core.prompt_loader import prompt_loader
from langchain_core.prompts import PromptTemplate

_SYSTEM_PROMPT = prompt_loader.get("doc_qa")

REACT_PROMPT_TEMPLATE = prompt_loader.get("chat")

react_prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)
