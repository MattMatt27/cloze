"""Artifact extraction — the leaf of the report-v2 pipeline.

Runs the pure analyzers once over a single conversation and persists the
result as mergeable sufficient statistics (schema in ``report/merge.py``) on
``AnalysisArtifact``. Every higher report scope folds these artifacts; nothing
above this layer touches raw messages.

Degradation contract (mirrors the analyzers themselves): a missing optional
dependency (spacy model, nltk data) or an unreachable LLM degrades that field
(zero counts / ``None``) rather than failing extraction. ``report/merge.py``
treats ``None`` co-occurrence as merge identity, so one degraded leaf never
poisons an aggregate.

The LLM seam: ``CLOZE_FAKE_LLM=1`` short-circuits summaries to a deterministic
canned string — used by the test suite and available for local dev so a full
extraction run never waits on a model.
"""

import json
import os
import time
from datetime import datetime, timezone
from itertools import combinations

from ..extensions import db
from ..models import AnalysisArtifact, Conversation
from report.merge import SCHEMA_VERSION

# Bump when analyzer behavior changes meaningfully; existing artifacts become
# stale (extraction upserts on (conversation_id, analyzer_version)).
ANALYZER_VERSION = "1"

_SUMMARY_TIMEOUT_SECONDS = 60
_SUMMARY_MAX_CHARS = 8000  # truncate transcript fed to the short-summary LLM


def build_conversation_stats(conversation, messages):
    """Pure-ish: compute the mergeable stats block for one conversation."""
    user_texts = [m.content for m in messages if m.role == "user"]

    message_counts, word_counts, by_day = {}, {}, {}
    timestamps = []
    for message in messages:
        message_counts[message.role] = message_counts.get(message.role, 0) + 1
        word_counts[message.role] = (
            word_counts.get(message.role, 0) + len(message.content.split())
        )
        timestamps.append(message.timestamp)
        day = datetime.fromtimestamp(message.timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
        by_day[day] = by_day.get(day, 0) + 1

    first_at = min(timestamps) if timestamps else None
    last_at = max(timestamps) if timestamps else None
    duration = (last_at - first_at) if timestamps else 0.0

    sentiment = _sentiment_stats(user_texts)
    voice = _voice_stats(user_texts)
    keywords = _keyword_stats(user_texts)
    cooccurrence = _cooccurrence_stats(user_texts)

    mean_sentiment = (
        sentiment["sum"] / sentiment["count"] if sentiment["count"] else None
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "conversations": 1,
        "messages": message_counts,
        "words": word_counts,
        "messages_by_day": by_day,
        "first_message_at": first_at,
        "last_message_at": last_at,
        "duration_seconds": duration,
        "sentiment": sentiment,
        "voice": voice,
        "keywords": keywords,
        "cooccurrence": cooccurrence,
        "per_conversation": [{
            "conversation_id": conversation.id,
            "mean_sentiment": mean_sentiment,
            "user_messages": message_counts.get("user", 0),
            "user_words": word_counts.get("user", 0),
            "duration_seconds": duration,
        }],
    }


def _sentiment_stats(texts):
    empty = {"sum": 0.0, "sum_sq": 0.0, "count": 0,
             "buckets": {"positive": 0, "neutral": 0, "negative": 0}}
    if not texts:
        return empty
    try:
        from report.analyzers.sentiment import SentimentAnalyzer
        result = SentimentAnalyzer().analyze(texts)
    except Exception:
        return empty
    scores = result.get("scores", [])
    distribution = result.get("sentiment_distribution", {})
    return {
        "sum": sum(scores),
        "sum_sq": sum(s * s for s in scores),
        "count": len(scores),
        "buckets": {
            "positive": distribution.get("positive", 0),
            "neutral": distribution.get("neutral", 0),
            "negative": distribution.get("negative", 0),
        },
    }


def _voice_stats(texts):
    if not texts:
        return {"active": 0, "passive": 0}
    try:
        from report.analyzers.voice_analysis import VoiceAnalyzer
        result = VoiceAnalyzer().analyze(texts)  # degrades to zeros without spacy model
    except Exception:
        return {"active": 0, "passive": 0}
    return {"active": result.get("active_count", 0), "passive": result.get("passive_count", 0)}


def _keyword_stats(texts):
    empty = {"categories": {}, "question_count": 0, "analyzed_texts": 0}
    if not texts:
        return empty
    try:
        from report.analyzers.keyword_extraction import KeywordAnalyzer
        result = KeywordAnalyzer().analyze(texts)
    except Exception:
        return empty
    return {
        "categories": dict(result.get("emotional_keywords", {})),
        "question_count": result.get("question_count", 0),
        "analyzed_texts": result.get("total_texts", len(texts)),
    }


def _cooccurrence_stats(texts):
    """Unfiltered, canonically-keyed pair counts.

    The stock analyzer filters pairs below ``min_cooccurrence`` at the leaf —
    lossy for aggregation (a pair appearing once in each of ten conversations
    would vanish everywhere). We reuse its tokenizer for parity but keep raw
    counts; thresholds and top-N are applied at render time over the *merged*
    counts. Keys are ``"a|b"`` with a < b, counted once per unordered pair.
    """
    if not texts:
        return None
    try:
        from report.analyzers.cooccurrence import CooccurrenceAnalyzer
        analyzer = CooccurrenceAnalyzer(min_cooccurrence=1)
        cleaned = analyzer._clean_text(" ".join(texts))
        sentences = analyzer._tokenize_sentences(cleaned)
    except Exception:
        return None  # nltk/data unavailable — merge identity
    if not sentences:
        return None

    pairs, words = {}, {}
    for sentence in sentences:
        for word in sentence:
            words[word] = words.get(word, 0) + 1
        for w1, w2 in combinations(sentence, 2):
            if w1 == w2:
                continue
            key = "|".join(sorted((w1, w2)))
            pairs[key] = pairs.get(key, 0) + 1
    return {"pairs": pairs, "words": words, "sentences": len(sentences)}


# --- short AI summary ---------------------------------------------------------

def short_summary(messages):
    """2-3 sentence conversation summary, or None when no LLM is reachable.

    These summaries are the leaves of the hierarchical-summary design: higher
    scopes summarize summaries, never raw transcripts.
    """
    if not messages:
        return None
    if os.environ.get("CLOZE_FAKE_LLM"):
        user_count = sum(1 for m in messages if m.role == "user")
        return (
            f"[fake-llm] Conversation with {user_count} participant message(s) "
            f"across {len(messages)} total messages."
        )

    model = _select_local_llama()
    if model is None:
        return None

    transcript = "\n".join(f"{m.role}: {m.content}" for m in messages)[:_SUMMARY_MAX_CHARS]
    prompt = (
        "Summarize the following conversation between a participant and an AI "
        "assistant in 2-3 sentences for a clinician's records. Focus on topics "
        "and emotional tone. Do not include names or identifying details.\n\n"
        f"{transcript}\n\nSummary:"
    )
    try:
        from .llm_interface import LLMInterface
        response_text, _ = LLMInterface.call_llm(
            model,
            [{"role": "user", "content": prompt}],
            config_override={"timeout": _SUMMARY_TIMEOUT_SECONDS},
        )
        return response_text.strip() or None
    except Exception:
        return None  # summary is optional; the artifact is still valid


def _select_local_llama():
    """Smallest available local Llama model (same preference order as the
    legacy AI-summary component: 1b → 3b → 7b → 8b → any llama)."""
    try:
        from ..models import Model
        candidates = [
            m for m in Model.query.filter_by(provider="local").all()
            if "llama" in (m.name or "").lower()
        ]
    except Exception:
        return None
    if not candidates:
        return None

    def size_rank(model):
        name = model.name.lower()
        for rank, tag in enumerate(("1b", "3b", "7b", "8b")):
            if tag in name:
                return rank
        return 99

    return sorted(candidates, key=size_rank)[0]


# --- persistence --------------------------------------------------------------

def extract_artifact(conversation_id, force=False):
    """Compute and upsert the artifact for one conversation. Idempotent:
    an existing ready artifact for the current ANALYZER_VERSION is returned
    untouched unless ``force``."""
    artifact = AnalysisArtifact.query.filter_by(
        conversation_id=conversation_id, analyzer_version=ANALYZER_VERSION
    ).first()
    if artifact is not None and artifact.status == "ready" and not force:
        return artifact

    conversation = db.session.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError(f"conversation {conversation_id} not found")

    messages = conversation.messages.all()
    stats = build_conversation_stats(conversation, messages)
    summary = short_summary(messages)

    if artifact is None:
        artifact = AnalysisArtifact(
            conversation_id=conversation_id, analyzer_version=ANALYZER_VERSION
        )
        db.session.add(artifact)

    artifact.artifact_data = json.dumps(stats)
    artifact.ai_summary = summary
    artifact.status = "ready"
    artifact.error = None
    artifact.computed_at = time.time()
    db.session.commit()
    return artifact


def conversations_missing_artifacts():
    """IDs of conversations lacking a ready artifact at the current version
    (drives the backfill job)."""
    have = db.session.query(AnalysisArtifact.conversation_id).filter_by(
        analyzer_version=ANALYZER_VERSION, status="ready"
    )
    rows = db.session.query(Conversation.id).filter(~Conversation.id.in_(have)).all()
    return [row[0] for row in rows]
