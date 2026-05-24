from core.prompt_loader import prompt_loader
from langchain_core.prompts import PromptTemplate


def get_react_prompt() -> PromptTemplate:
    prompt_loader.reload()
    return PromptTemplate.from_template(prompt_loader.get("chat"))


def get_doc_qa_system_prompt() -> str:
    prompt_loader.reload()
    return prompt_loader.get("doc_qa")
