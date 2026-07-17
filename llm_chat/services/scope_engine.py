"""The aggregation engine: scope → report_data dict.

Pipeline (design doc §Idea 1):
    resolve scope → ensure artifacts (extract missing leaves) → fold merged
    stats (whole scope + per group) → run scope-enabled components → sections.

Persistence (Report rows) and the job-kind wiring land with the next
milestone; this module returns the data structure.
"""

import json
import time

from report.aggregate import AggregationContext, GroupAggregate, derive_metrics
from report.merge import empty_stats, merge_all
from report.registry_v2 import components_for_scope

from ..models import AnalysisArtifact
from .artifacts import ANALYZER_VERSION, extract_artifact
from .scopes import resolve_scope
from .summaries import synthesize_summaries

REPORT_DATA_SCHEMA = 1


def generate_report_data(scope, scope_id, components=None, progress_cb=None):
    """Build the full report_data dict for a scope.

    components: optional iterable of component keys to restrict to (still
    intersected with the scope's supported set).
    progress_cb: optional fn(current, total) — the job handler wires this to
    heartbeats; extraction of missing artifacts dominates runtime.
    """
    selection = resolve_scope(scope, scope_id)
    conversation_ids = selection.conversation_ids

    # 1. Ensure leaves exist (idempotent; skips ready artifacts).
    total = len(conversation_ids)
    for index, conversation_id in enumerate(conversation_ids, start=1):
        extract_artifact(conversation_id)
        if progress_cb is not None:
            progress_cb(index, total)

    # 2. Load artifacts once.
    artifacts = {}
    if conversation_ids:
        rows = AnalysisArtifact.query.filter(
            AnalysisArtifact.conversation_id.in_(conversation_ids),
            AnalysisArtifact.analyzer_version == ANALYZER_VERSION,
            AnalysisArtifact.status == "ready",
        ).all()
        artifacts = {
            row.conversation_id: (json.loads(row.artifact_data), row.ai_summary)
            for row in rows
        }

    def stats_for(ids):
        return merge_all(artifacts[i][0] for i in ids if i in artifacts)

    # 3. Fold: whole scope + per group.
    overall = stats_for(conversation_ids) if conversation_ids else empty_stats()
    groups = [
        GroupAggregate(key=g.key, label=g.label, order=g.order,
                       stats=stats_for(g.conversation_ids))
        for g in selection.groups
    ]
    leaf_summaries = [
        (i, artifacts[i][1]) for i in conversation_ids if i in artifacts
    ]
    group_summaries = {
        g.key: [(i, artifacts[i][1]) for i in g.conversation_ids if i in artifacts]
        for g in selection.groups
    }

    ctx = AggregationContext(
        scope=scope,
        scope_id=scope_id,
        title=selection.title,
        stats=overall,
        derived=derive_metrics(overall),
        groups=groups,
        leaf_summaries=leaf_summaries,
        group_summaries=group_summaries,
        meta=selection.meta,
        synthesize=synthesize_summaries,
    )

    # 4. Components: registry order, scope-filtered, optionally restricted.
    requested = set(components) if components is not None else None
    sections = {}
    for definition in components_for_scope(scope):
        if requested is not None and definition.key not in requested:
            continue
        result = definition.builder(ctx)
        if result is not None:
            sections[definition.key] = result

    return {
        "report_data_schema": REPORT_DATA_SCHEMA,
        "scope": scope,
        "scope_id": scope_id,
        "title": selection.title,
        "provider_id": selection.provider_id,
        "patient_id": selection.patient_id,
        "conversation_count": len(conversation_ids),
        "analyzer_version": ANALYZER_VERSION,
        "generated_at": time.time(),
        "groups": [
            {"key": g.key, "label": g.label, "order": g.order,
             "conversations": len(g.conversation_ids)}
            for g in selection.groups
        ],
        "sections": sections,
    }
