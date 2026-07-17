"""Component registry v2 — the component × scope matrix. Pure.

Each component declares which scopes it supports and builds its section from
an AggregationContext (report/aggregate.py). Builders never touch the DB or
raw messages — they consume merged stats, group aggregates, resolver metadata,
and (for summaries) the injected LLM seam.

Matrix (design doc §Registry v2):

    component            conv  window  enrollment  participant  flow  account
    descriptive_stats     ✓      ✓        ✓            ✓          ✓      ✓
    sentiment_analysis    ✓      ✓        ✓            ✓          ✓      ✓
    voice_analysis        ✓      ✓        ✓            ✓          ✓      ✓
    keyword_analysis      ✓      ✓        ✓            ✓          ✓      ✓
    cooccurrence          ✓      ✓        ✓            ✓          ✓      —
    ai_summary            ✓      —        —            —          —      —
    hierarchical_summary  —      ✓        ✓            ✓          ✓      ✓
    trend_analysis        —      —        ✓            ✓          ✓      ✓
    phase_comparison      —      —        ✓            ✓          —      —
    completion_analysis   —      —        —            —          ✓      ✓
    engagement_overview   —      —        —            —          —      ✓
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Optional

from .aggregate import AggregationContext, derive_metrics, top_cooccurrences

ALL_SCOPES = frozenset(
    {"conversation", "window", "enrollment", "participant", "flow", "account"}
)
AGGREGATE_SCOPES = ALL_SCOPES - {"conversation"}


@dataclass(frozen=True)
class ComponentDef:
    key: str
    label: str
    scopes: FrozenSet[str]
    builder: Callable[[AggregationContext], Optional[Dict[str, Any]]]
    # Builders may return None to indicate "nothing to show" — the engine
    # omits the section rather than rendering an empty shell.


# --- builders -----------------------------------------------------------------

def _descriptive_stats(ctx):
    return {
        "conversations": ctx.derived["conversations"],
        "total_messages": ctx.derived["total_messages"],
        "user_messages": ctx.derived["user_messages"],
        "assistant_messages": ctx.derived["assistant_messages"],
        "avg_messages_per_conversation": ctx.derived["avg_messages_per_conversation"],
        "avg_user_words_per_message": ctx.derived["avg_user_words_per_message"],
        "avg_assistant_words_per_message": ctx.derived["avg_assistant_words_per_message"],
        "active_days": ctx.derived["active_days"],
        "first_message_at": ctx.derived["first_message_at"],
        "last_message_at": ctx.derived["last_message_at"],
        "median_user_messages": ctx.derived["median_user_messages"],
        "median_duration_seconds": ctx.derived["median_duration_seconds"],
        "messages_by_day": ctx.stats["messages_by_day"],
    }


def _sentiment_analysis(ctx):
    if not ctx.stats["sentiment"]["count"]:
        return None
    return {
        "mean": ctx.derived["sentiment_mean"],
        "stddev": ctx.derived["sentiment_stddev"],
        "median": ctx.derived["median_sentiment"],
        "distribution": ctx.stats["sentiment"]["buckets"],
        "percentages": ctx.derived["sentiment_percentages"],
        "analyzed_messages": ctx.stats["sentiment"]["count"],
    }


def _voice_analysis(ctx):
    voice = ctx.stats["voice"]
    if not (voice["active"] + voice["passive"]):
        return None  # spacy model unavailable at extraction, or no user text
    return {
        "active_count": voice["active"],
        "passive_count": voice["passive"],
        "active_ratio": ctx.derived["voice_active_ratio"],
        "passive_ratio": ctx.derived["voice_passive_ratio"],
    }


def _keyword_analysis(ctx):
    keywords = ctx.stats["keywords"]
    if not keywords["analyzed_texts"]:
        return None
    return {
        "emotional_keywords": keywords["categories"],
        "question_count": keywords["question_count"],
        "questions_per_user_message": ctx.derived["questions_per_user_message"],
        "analyzed_texts": keywords["analyzed_texts"],
    }


def _cooccurrence(ctx):
    return top_cooccurrences(ctx.stats)


def _ai_summary(ctx):
    """Leaf only: the conversation's own extraction-time summary."""
    if not ctx.leaf_summaries:
        return None
    _, summary = ctx.leaf_summaries[0]
    return {"summary": summary}


def _hierarchical_summary(ctx):
    """Summaries of summaries — never raw transcripts (bounded LLM context).

    With groups: synthesize each group from its members' leaf summaries, then
    synthesize the whole from the group syntheses. Without groups (window):
    synthesize directly from leaf summaries."""
    if ctx.synthesize is None or not ctx.leaf_summaries:
        return None

    if ctx.groups and len(ctx.groups) > 1:
        group_sections = []
        for group in ctx.groups:
            member_summaries = [s for _, s in ctx.group_summaries.get(group.key, []) if s]
            if not member_summaries:
                continue
            synthesis = ctx.synthesize(member_summaries, group.label)
            if synthesis:
                group_sections.append({"key": group.key, "label": group.label,
                                       "summary": synthesis})
        if not group_sections:
            return None
        overall = ctx.synthesize(
            [section["summary"] for section in group_sections], ctx.title
        )
        return {"summary": overall, "groups": group_sections}

    leaf = [s for _, s in ctx.leaf_summaries if s]
    if not leaf:
        return None
    return {"summary": ctx.synthesize(leaf, ctx.title), "groups": []}


def _series(groups, metric):
    return [{"key": g.key, "label": g.label, "order": g.order, "value": metric(g)}
            for g in groups]


def _trend_analysis(ctx):
    """Time series over the scope's natural groups (phases/flows/participants)."""
    if len(ctx.groups) < 2:
        return None  # a trend needs at least two points
    group_derived = [(g, derive_metrics(g.stats)) for g in ctx.groups]
    return {
        "group_kind": ctx.groups[0].key.split(":")[0],
        "sentiment": [
            {"key": g.key, "label": g.label, "value": d["sentiment_mean"]}
            for g, d in group_derived
        ],
        "message_volume": [
            {"key": g.key, "label": g.label, "value": d["total_messages"]}
            for g, d in group_derived
        ],
        "engagement": [
            {"key": g.key, "label": g.label,
             "value": d["avg_messages_per_conversation"]}
            for g, d in group_derived
        ],
        "user_words_per_message": [
            {"key": g.key, "label": g.label,
             "value": d["avg_user_words_per_message"]}
            for g, d in group_derived
        ],
    }


def _phase_comparison(ctx):
    """Side-by-side table of each group's headline stats."""
    if len(ctx.groups) < 2:
        return None
    rows = []
    for group in ctx.groups:
        derived = derive_metrics(group.stats)
        rows.append({
            "key": group.key,
            "label": group.label,
            "conversations": derived["conversations"],
            "user_messages": derived["user_messages"],
            "avg_messages_per_conversation": derived["avg_messages_per_conversation"],
            "sentiment_mean": derived["sentiment_mean"],
            "questions_per_user_message": derived["questions_per_user_message"],
            "active_days": derived["active_days"],
        })
    return {"rows": rows}


def _completion_analysis(ctx):
    """Enrollment vs participation (flow/account scopes; resolver meta)."""
    meta = ctx.meta
    if ctx.scope == "flow":
        enrolled = meta.get("enrollment_count", 0)
        started = meta.get("started_count", 0)
        return {
            "enrolled": enrolled,
            "started": started,
            "started_pct": (started / enrolled * 100) if enrolled else 0,
            "phase_participation": meta.get("phase_participation", {}),
            # participants enrolled but with zero conversations anywhere
            "inactive": [g.label for g in ctx.groups
                         if not g.stats["conversations"]],
        }
    if ctx.scope == "account":
        flows = meta.get("flows", [])
        if not flows:
            return None
        enrolled = sum(f["enrollment_count"] for f in flows)
        started = sum(f["started_count"] for f in flows)
        return {
            "enrolled": enrolled,
            "started": started,
            "started_pct": (started / enrolled * 100) if enrolled else 0,
            "by_flow": flows,
        }
    return None


def _engagement_overview(ctx):
    """Account scope: one headline row per flow (plus standalone bucket)."""
    if not ctx.groups:
        return None
    rows = []
    for group in ctx.groups:
        derived = derive_metrics(group.stats)
        rows.append({
            "key": group.key,
            "label": group.label,
            "conversations": derived["conversations"],
            "total_messages": derived["total_messages"],
            "active_days": derived["active_days"],
            "sentiment_mean": derived["sentiment_mean"],
            "last_message_at": derived["last_message_at"],
        })
    return {"rows": rows, "patient_count": ctx.meta.get("patient_count")}


# --- registry -----------------------------------------------------------------

COMPONENTS: Dict[str, ComponentDef] = {
    definition.key: definition for definition in [
        ComponentDef("descriptive_stats", "Descriptive statistics",
                     ALL_SCOPES, _descriptive_stats),
        ComponentDef("sentiment_analysis", "Sentiment analysis",
                     ALL_SCOPES, _sentiment_analysis),
        ComponentDef("voice_analysis", "Voice analysis",
                     ALL_SCOPES, _voice_analysis),
        ComponentDef("keyword_analysis", "Keyword analysis",
                     ALL_SCOPES, _keyword_analysis),
        ComponentDef("cooccurrence", "Word co-occurrence",
                     ALL_SCOPES - {"account"}, _cooccurrence),
        ComponentDef("ai_summary", "AI summary",
                     frozenset({"conversation"}), _ai_summary),
        ComponentDef("hierarchical_summary", "AI summary",
                     AGGREGATE_SCOPES, _hierarchical_summary),
        ComponentDef("trend_analysis", "Trends over time",
                     frozenset({"enrollment", "participant", "flow", "account"}),
                     _trend_analysis),
        ComponentDef("phase_comparison", "Phase comparison",
                     frozenset({"enrollment", "participant"}), _phase_comparison),
        ComponentDef("completion_analysis", "Completion analysis",
                     frozenset({"flow", "account"}), _completion_analysis),
        ComponentDef("engagement_overview", "Engagement overview",
                     frozenset({"account"}), _engagement_overview),
    ]
}


def components_for_scope(scope: str):
    """Registry order, filtered to the scope."""
    return [c for c in COMPONENTS.values() if scope in c.scopes]
