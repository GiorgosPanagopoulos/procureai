import re
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import BaseModel

DEFAULT_PROMPT_VERSION = "v1"

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptMetadata(BaseModel):
    use_case: str
    version: str
    created: str
    description: str


class LoadedPrompt(BaseModel):
    metadata: PromptMetadata
    text: str


class PromptLoader:
    """Loads all prompts from the filesystem at startup and caches them in memory."""

    def __init__(self, prompts_dir: Path = _PROMPTS_DIR) -> None:
        self._dir = prompts_dir
        self._cache: Dict[Tuple[str, str], LoadedPrompt] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._cache.clear()
        if not self._dir.exists():
            return
        for use_case_dir in self._dir.iterdir():
            if not use_case_dir.is_dir():
                continue
            use_case = use_case_dir.name
            for prompt_file in sorted(use_case_dir.glob("*.txt")):
                version = prompt_file.stem
                self._cache[(use_case, version)] = self._parse_file(prompt_file, use_case, version)

    def _parse_file(self, path: Path, use_case: str, version: str) -> LoadedPrompt:
        content = path.read_text(encoding="utf-8")
        default_meta = {
            "use_case": use_case,
            "version": version,
            "created": "",
            "description": "",
        }

        lines = content.split("\n")
        sep_line: int | None = None
        for i, line in enumerate(lines):
            if line.strip() == "---":
                sep_line = i
                break

        if sep_line is None:
            return LoadedPrompt(
                metadata=PromptMetadata(**default_meta),
                text=content.strip(),
            )

        header_lines = lines[:sep_line]
        text = "\n".join(lines[sep_line + 1 :]).strip()

        meta = dict(default_meta)
        for line in header_lines:
            m = re.match(r"^#\s*(\w+):\s*(.+)$", line.strip())
            if m:
                key, value = m.group(1), m.group(2).strip()
                if key in meta:
                    meta[key] = value

        return LoadedPrompt(metadata=PromptMetadata(**meta), text=text)

    def get(self, use_case: str, version: str = DEFAULT_PROMPT_VERSION) -> str:
        """Return prompt text only, raising ValueError if not found."""
        try:
            return self._cache[(use_case, version)].text
        except KeyError:
            available = sorted(f"{uc}/{v}" for uc, v in self._cache)
            raise ValueError(f"Prompt '{use_case}/{version}' not found. Available: {available}")

    def get_with_metadata(
        self, use_case: str, version: str = DEFAULT_PROMPT_VERSION
    ) -> LoadedPrompt:
        """Return prompt text and parsed metadata, raising ValueError if not found."""
        try:
            return self._cache[(use_case, version)]
        except KeyError:
            available = sorted(f"{uc}/{v}" for uc, v in self._cache)
            raise ValueError(f"Prompt '{use_case}/{version}' not found. Available: {available}")

    def list_versions(self, use_case: str) -> List[str]:
        """Return sorted list of available versions for a given use case."""
        return sorted(v for uc, v in self._cache if uc == use_case)

    def list_use_cases(self) -> List[str]:
        """Return sorted list of all loaded use cases."""
        return sorted({uc for uc, _ in self._cache})

    def reload(self) -> None:
        """Hot-reload all prompts from disk without restarting."""
        self._load_all()


prompt_loader = PromptLoader()
