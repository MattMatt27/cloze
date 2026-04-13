"""
Prompt Registry

Singleton that discovers, loads, and indexes all prompt files on startup.
Loads from subdirectories: universal/, clinical/, defaults/, and domains/.
"""

import os
from typing import Dict, List, Optional

from .loader import PromptEntry, load_prompt_file


_PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PromptRegistry:
    _instance = None

    def __init__(self):
        self._universal: List[PromptEntry] = []
        self._study_context: Dict[str, PromptEntry] = {}
        self._defaults: Dict[str, PromptEntry] = {}
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

    def _load_dir(self, directory: str) -> List[PromptEntry]:
        """Load all .md files from a directory, sorted by filename."""
        entries = []
        if not os.path.isdir(directory):
            return entries
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".md"):
                path = os.path.join(directory, filename)
                try:
                    entries.append(load_prompt_file(path))
                except Exception as e:
                    print(f"Warning: Failed to load prompt {path}: {e}")
        return entries

    def _load_all(self):
        """Scan all prompt subdirectories."""
        constitutional_dir = os.path.join(_PROMPTS_DIR, "constitutional")

        # Universal prompts (always loaded)
        self._universal = self._load_dir(os.path.join(constitutional_dir, "universal"))
        self._universal.sort(key=lambda p: p.order)

        # Study context prompts (clinical safety, PII protection — loaded conditionally)
        self._study_context: Dict[str, PromptEntry] = {}
        for entry in self._load_dir(os.path.join(constitutional_dir, "study_context")):
            self._study_context[entry.id] = entry

        # Default overridable prompts
        for entry in self._load_dir(os.path.join(constitutional_dir, "defaults")):
            self._defaults[entry.id] = entry

        # Domain prompts
        domains_dir = os.path.join(_PROMPTS_DIR, "domains")
        for entry in self._load_dir(domains_dir):
            entry.category = "domain"
            self._domains[entry.id] = entry

    # ── Public API ──

    def get_universal_prompts(self) -> List[PromptEntry]:
        """All universal prompts in order (always loaded)."""
        return list(self._universal)

    def get_study_context_prompt(self, prompt_id: str) -> Optional[PromptEntry]:
        """A single study context prompt by ID (e.g. 'clinical_safety', 'pii_protection')."""
        return self._study_context.get(prompt_id)

    def get_default_prompt(self, prompt_id: str) -> Optional[PromptEntry]:
        """A single default overridable prompt by ID."""
        return self._defaults.get(prompt_id)

    def get_domain_prompt(self, domain_id: str) -> Optional[PromptEntry]:
        """Single domain prompt by ID."""
        return self._domains.get(domain_id)

    def list_domain_prompts(self) -> List[PromptEntry]:
        """All domain prompts with metadata for UI."""
        return list(self._domains.values())

    # ── Backwards compatibility ──

    def get_constitutional_prompts(self) -> List[PromptEntry]:
        """All universal prompts (legacy alias)."""
        return self.get_universal_prompts()
