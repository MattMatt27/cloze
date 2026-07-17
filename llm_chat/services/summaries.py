"""LLM synthesis for hierarchical summaries.

One level of the hierarchy: given child summaries (conversation summaries for
a window; window syntheses for an enrollment; …), produce a synthesis. Raw
transcripts never reach this layer — context stays bounded at every level.

Same seam as extraction: ``CLOZE_FAKE_LLM=1`` returns deterministic strings.
"""

import os

_SYNTHESIS_TIMEOUT_SECONDS = 120
_MAX_INPUT_CHARS = 8000


def synthesize_summaries(texts, level_label):
    """Synthesize child summaries into one narrative, or None if no LLM."""
    texts = [t for t in texts if t]
    if not texts:
        return None
    if os.environ.get("CLOZE_FAKE_LLM"):
        return f"[fake-llm] Synthesis of {len(texts)} summaries for {level_label}."

    from .artifacts import _select_local_llama
    model = _select_local_llama()
    if model is None:
        return None

    joined = "\n\n".join(f"- {t}" for t in texts)[:_MAX_INPUT_CHARS]
    prompt = (
        f"The following are summaries of parts of \"{level_label}\" in a "
        "clinical research study. Synthesize them into a 3-5 sentence "
        "narrative for a clinician: overall themes, emotional trajectory, and "
        "any notable changes over time. Do not include names or identifying "
        f"details.\n\n{joined}\n\nSynthesis:"
    )
    try:
        from .llm_interface import LLMInterface
        response_text, _ = LLMInterface.call_llm(
            model,
            [{"role": "user", "content": prompt}],
            config_override={"timeout": _SYNTHESIS_TIMEOUT_SECONDS},
        )
        return response_text.strip() or None
    except Exception:
        return None  # summaries are best-effort; stats sections still render
