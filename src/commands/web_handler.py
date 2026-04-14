# src/commands/web_handler.py
"""
Web search handler using DuckDuckGo
"""

import yaml
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent.parent.parent / "config/settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('web_search', {})


class WebHandler:
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        cfg = _load_config()
        self.max_results = cfg.get('max_results', 3)
        self.system_prompt = cfg.get(
            'system_prompt',
            "Answer the question directly in 1-2 sentences using these search results. Do not cite sources."
        )

    def handle(self, query: str) -> str:
        results = self._search(query)
        if not results:
            return f"No search results found for '{query}'."
        return self._llm_answer(query, results)

    def _search(self, query: str) -> list:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=self.max_results))
        except ImportError:
            return []
        except Exception:
            return []

    def _llm_answer(self, query: str, results: list) -> str:
        context_parts = []
        for r in results:
            title = r.get('title', '')
            body = r.get('body', '')
            context_parts.append(f"{title}: {body}")
        context = "\n\n".join(context_parts)

        prompt = f"Question: {query}\n\nSearch results:\n{context}"
        return self.ollama.complete(prompt, system_prompt=self.system_prompt)


if __name__ == "__main__":
    from src.llm.ollama_client import OllamaClient
    client = OllamaClient()
    handler = WebHandler(client)
    answer = handler.handle("What is the capital of France?")
    print(answer)
