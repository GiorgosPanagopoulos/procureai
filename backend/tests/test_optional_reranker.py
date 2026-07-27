import ast
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_executor_has_no_module_level_langchain_classic_import():
    """langchain_classic.agents must stay a lazy, function-scoped import in
    agent/executor.py - a module-level import would reintroduce the ~5.5s
    startup cost this PR removes. Static AST check only, no import."""
    source = (BACKEND_DIR / "agent" / "executor.py").read_text()
    tree = ast.parse(source)

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(
                    "langchain_classic"
                ), f"module-level 'import {alias.name}' defeats the lazy-import optimization"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith(
                "langchain_classic"
            ), f"module-level 'from {module} import ...' defeats the lazy-import optimization"


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_routers_chat_imports_without_sentence_transformers():
    """The default install has no sentence-transformers; importing routers.chat
    (and therefore the app) must not depend on it being present."""
    script = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_spec(self, name, path, target=None):
                if name == "sentence_transformers" or name.startswith("sentence_transformers."):
                    raise ModuleNotFoundError(name)
                return None

        sys.meta_path.insert(0, _Blocker())

        import routers.chat  # noqa: F401
        print("IMPORT_OK")
        """
    )
    result = _run(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "IMPORT_OK" in result.stdout


def test_reranker_missing_package_raises_informative_runtime_error():
    """USE_RERANKER=true without sentence-transformers installed must fail loudly
    with the exact install command, not silently skip reranking."""
    script = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_spec(self, name, path, target=None):
                if name == "sentence_transformers" or name.startswith("sentence_transformers."):
                    raise ModuleNotFoundError(name)
                return None

        sys.meta_path.insert(0, _Blocker())

        from rag.reranker import _get_reranker

        try:
            _get_reranker()
        except RuntimeError as exc:
            assert "USE_RERANKER=true" in str(exc)
            assert "pip install -r backend/requirements-rerank.txt" in str(exc)
            print("RUNTIME_ERROR_OK")
        else:
            print("NO_ERROR_RAISED")
        """
    )
    result = _run(script)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RUNTIME_ERROR_OK" in result.stdout
