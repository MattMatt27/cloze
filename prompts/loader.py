"""
Prompt Loader

Reads .md files with YAML front matter and parses them into PromptEntry objects.
"""

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class PromptEntry:
    id: str
    name: str
    category: str           # "constitutional" | "domain"
    description: str
    content: str            # The actual prompt text
    tags: list = field(default_factory=list)
    version: int = 1
    order: int = 0          # For constitutional ordering


def load_prompt_file(path: str) -> PromptEntry:
    """Parse a .md file with YAML front matter into a PromptEntry."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    if not raw.startswith("---"):
        raise ValueError(f"Prompt file missing YAML front matter: {path}")

    # Split on the closing --- delimiter
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Malformed front matter in: {path}")

    front_matter = yaml.safe_load(parts[1])
    content = parts[2].strip()

    return PromptEntry(
        id=front_matter.get("id", os.path.splitext(os.path.basename(path))[0]),
        name=front_matter.get("name", ""),
        category=front_matter.get("category", "domain"),
        description=front_matter.get("description", ""),
        content=content,
        tags=front_matter.get("tags", []),
        version=front_matter.get("version", 1),
        order=front_matter.get("order", 0),
    )
