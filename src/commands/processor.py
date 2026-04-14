# src/commands/processor.py
"""
Command intent classifier and router
"""

import re
import yaml
from pathlib import Path

from src.llm.ollama_client import OllamaClient
from src.commands.mac_handler import MacHandler
from src.commands.web_handler import WebHandler


def _load_config():
    config_path = Path(__file__).parent.parent.parent / "config/settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('command_processor', {})


INTENT_SYSTEM_PROMPT = """Classify the user's command into exactly one of these intents:
file_search, file_open, system_info, web_search, general

Rules:
- file_search: looking for a file (find, search, where is, locate)
- file_open: opening a file or app (open, launch, start)
- system_info: system status (battery, memory, CPU, disk, storage)
- web_search: current events, facts, news, weather, prices, anything needing internet
- general: conversation, calculations, explanations, everything else

Respond with ONLY the intent word, nothing else."""

INTENT_EXAMPLES = [
    {"role": "user", "content": "find my resume"},
    {"role": "assistant", "content": "file_search"},
    {"role": "user", "content": "open Safari"},
    {"role": "assistant", "content": "file_open"},
    {"role": "user", "content": "how's my battery"},
    {"role": "assistant", "content": "system_info"},
    {"role": "user", "content": "who won the game last night"},
    {"role": "assistant", "content": "web_search"},
    {"role": "user", "content": "what is 15 percent of 80"},
    {"role": "assistant", "content": "general"},
]

VALID_INTENTS = {'file_search', 'file_open', 'system_info', 'web_search', 'general'}

# Regex fallback patterns
_PATTERNS = [
    (re.compile(r'\b(battery|memory|ram|cpu|disk|storage|charging)\b', re.I), 'system_info'),
    (re.compile(r'\b(find|search|locate|where is|where\'?s)\b.*(file|document|folder|pdf|note)', re.I), 'file_search'),
    (re.compile(r'\b(open|launch|start)\b', re.I), 'file_open'),
    (re.compile(r'\b(weather|news|who|what time|price|score|latest)\b', re.I), 'web_search'),
]


class CommandProcessor:
    def __init__(self):
        self.ollama = OllamaClient()
        self.mac_handler = MacHandler(self.ollama)
        self.web_handler = WebHandler(self.ollama)
        cfg = _load_config()
        self.general_system_prompt = cfg.get(
            'general_system_prompt',
            "You are JARVIS, a concise personal AI assistant for Mac. Answer in 1-2 sentences."
        )

    def is_ready(self) -> bool:
        return self.ollama.is_available()

    def process(self, command: str) -> str:
        intent = self._classify_intent(command)
        print(f"  [intent: {intent}]")

        if intent == 'file_search':
            # Extract the search term (everything after "find"/"search for" etc.)
            query = re.sub(r'^.*?\b(find|search|locate|where is|where\'?s)\b\s*', '', command, flags=re.I).strip()
            query = query or command
            return self.mac_handler.handle('file_search', query)

        elif intent == 'file_open':
            query = re.sub(r'^.*?\b(open|launch|start)\b\s*', '', command, flags=re.I).strip()
            query = query or command
            return self.mac_handler.handle('file_open', query)

        elif intent == 'system_info':
            return self.mac_handler.handle('system_info', command)

        elif intent == 'web_search':
            return self.web_handler.handle(command)

        else:  # general
            return self._handle_general(command)

    def _classify_intent(self, command: str) -> str:
        # Try LLM classification first
        messages = INTENT_EXAMPLES + [{"role": "user", "content": command}]
        result = self.ollama.chat(messages, system_prompt=INTENT_SYSTEM_PROMPT, temperature=0.0)
        result = result.strip().lower()
        if result in VALID_INTENTS:
            return result

        # Fallback to regex
        return self._keyword_classify(command)

    def _keyword_classify(self, command: str) -> str:
        for pattern, intent in _PATTERNS:
            if pattern.search(command):
                return intent
        return 'general'

    def _handle_general(self, command: str) -> str:
        return self.ollama.complete(command, system_prompt=self.general_system_prompt)


if __name__ == "__main__":
    processor = CommandProcessor()
    if not processor.is_ready():
        print("Ollama is not running. Start with: ollama serve")
        exit(1)

    test_commands = [
        "What's my battery level?",
        "Find my resume",
        "What's the weather in San Francisco?",
        "What is the square root of 144?",
        "Open Safari",
    ]
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        print(f"Response: {processor.process(cmd)}")
