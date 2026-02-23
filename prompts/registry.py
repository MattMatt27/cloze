"""
Prompt Registry

Singleton that discovers, loads, and indexes all prompt files on startup.
Follows the same pattern as report/registry.py.
"""

import os
from typing import Dict, List, Optional

from .loader import PromptEntry, load_prompt_file


_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PromptRegistry:
    _instance = None

    def __init__(self):
        self._constitutional: List[PromptEntry] = []
        self._domains: Dict[str, PromptEntry] = {}

    @classmethod
    def instance(cls) -> "PromptRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_all()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (useful for testing)."""
        cls._instance = None

    def _load_all(self):
        """Scan constitutional/ and domains/ directories and load all .md files."""
        constitutional_dir = os.path.join(_PROMPTS_DIR, "constitutional")
        domains_dir = os.path.join(_PROMPTS_DIR, "domains")

        # Load constitutional prompts
        if os.path.isdir(constitutional_dir):
            for filename in sorted(os.listdir(constitutional_dir)):
                if filename.endswith(".md"):
                    path = os.path.join(constitutional_dir, filename)
                    try:
                        entry = load_prompt_file(path)
                        entry.category = "constitutional"
                        self._constitutional.append(entry)
                    except Exception as e:
                        print(f"Warning: Failed to load constitutional prompt {path}: {e}")

        # Sort constitutional prompts by order field
        self._constitutional.sort(key=lambda p: p.order)

        # Load domain prompts
        if os.path.isdir(domains_dir):
            for filename in sorted(os.listdir(domains_dir)):
                if filename.endswith(".md"):
                    path = os.path.join(domains_dir, filename)
                    try:
                        entry = load_prompt_file(path)
                        entry.category = "domain"
                        self._domains[entry.id] = entry
                    except Exception as e:
                        print(f"Warning: Failed to load domain prompt {path}: {e}")

    def get_constitutional_prompts(self) -> List[PromptEntry]:
        """All constitutional prompts in order."""
        return list(self._constitutional)

    def get_domain_prompt(self, domain_id: str) -> Optional[PromptEntry]:
        """Single domain prompt by ID."""
        return self._domains.get(domain_id)

    def list_domain_prompts(self) -> List[PromptEntry]:
        """All domain prompts with metadata for UI."""
        return list(self._domains.values())
