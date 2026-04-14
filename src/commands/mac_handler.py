# src/commands/mac_handler.py
"""
Mac system integration handler
"""

import subprocess
import yaml
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent.parent.parent / "config/settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('mac_handler', {})


class MacHandler:
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        cfg = _load_config()
        self.mdfind_max_results = cfg.get('mdfind_max_results', 5)
        self.file_read_max_chars = cfg.get('file_read_max_chars', 3000)
        self.text_extensions = set(cfg.get('text_extensions', [
            '.txt', '.md', '.py', '.js', '.ts', '.json',
            '.yaml', '.yml', '.csv', '.log', '.sh'
        ]))

    def handle(self, intent: str, query: str) -> str:
        if intent == 'file_search':
            return self._file_search(query)
        elif intent == 'file_open':
            return self._file_open(query)
        elif intent == 'system_info':
            return self._system_info(query)
        return "I'm not sure how to handle that Mac request."

    def _file_search(self, query: str) -> str:
        try:
            result = subprocess.run(
                ['mdfind', '-name', query],
                capture_output=True, text=True, timeout=10
            )
            paths = [p for p in result.stdout.strip().splitlines() if p][:self.mdfind_max_results]
        except Exception as e:
            return f"File search failed: {e}"

        if not paths:
            return f"No files found matching '{query}'."

        response_lines = [f"Found {len(paths)} file(s) matching '{query}':"]
        for p in paths:
            response_lines.append(f"  • {p}")

        # If the top result is a readable text file, summarize it
        top = paths[0]
        if self._is_text_file(top):
            try:
                content = Path(top).read_text(errors='replace')[:self.file_read_max_chars]
                summary = self.ollama.complete(
                    f"Summarize this file in 1-2 sentences:\n\n{content}",
                    system_prompt="You are a concise file summarizer."
                )
                response_lines.append(f"\nTop file summary: {summary}")
            except Exception:
                pass

        return "\n".join(response_lines)

    def _file_open(self, query: str) -> str:
        try:
            subprocess.Popen(['open', query])
            return f"Opening '{query}'."
        except Exception as e:
            return f"Could not open '{query}': {e}"

    def _system_info(self, query: str) -> str:
        try:
            import psutil
        except ImportError:
            return "psutil not installed. Run: pip install psutil"

        parts = []

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            status = "charging" if battery.power_plugged else "on battery"
            parts.append(f"Battery: {battery.percent:.0f}% ({status})")

        # Memory
        mem = psutil.virtual_memory()
        parts.append(
            f"Memory: {mem.percent:.0f}% used "
            f"({_fmt_bytes(mem.used)} / {_fmt_bytes(mem.total)})"
        )

        # CPU
        cpu = psutil.cpu_percent(interval=0.5)
        parts.append(f"CPU: {cpu:.0f}% utilization")

        return " | ".join(parts) if parts else "Could not retrieve system info."

    def _is_text_file(self, path: str) -> bool:
        return Path(path).suffix.lower() in self.text_extensions


def _fmt_bytes(b: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


if __name__ == "__main__":
    from src.llm.ollama_client import OllamaClient
    client = OllamaClient()
    handler = MacHandler(client)
    print(handler._file_search("README"))
    print()
    print(handler._system_info(""))
