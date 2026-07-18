"""Scope resolution — scope → conversation set + natural grouping.

The one DB-aware step at the front of report generation. Everything after it
(merging, derived metrics, components) is pure and operates on what this
module returns.

Scope lattice (design doc):
    conversation → window (phase) → enrollment → flow (cohort) → account
    participant (cross-flow): all of a patient's windows, grouped by flow

Groups are the scope's *natural children*, time-ordered — they drive the
trend, phase-comparison, and hierarchical-summary components:
    conversation → (none — leaf)
    window       → (none — folds its conversations directly)
    enrollment   → windows/phases, by start_date
    participant  → flows (+ "Unstructured" bucket for flow-less windows and
                   window-less conversations)
    flow         → enrolled participants, by enrollment date
    account      → flows (+ standalone-windows bucket)

Flow↔window linkage: ``ChatWindow.flow_id`` (FK, set at generation since
report-v2) with a ``flow_name`` match fallback for legacy rows.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_

from ..models import (
    ChatWindow,
    Conversation,
    FlowEnrollment,
    ProviderPatient,
    StudyFlow,
    User,
)

SCOPES = ("conversation", "window", "enrollment", "participant", "flow", "account")


@dataclass
class Group:
    key: str                      # stable identifier, e.g. "window:12", "flow:3"
    label: str                    # display label (window title, flow name, username)
    order: float                  # sort key (start_date / enrolled_at / created_at)
    conversation_ids: List[int] = field(default_factory=list)


@dataclass
class ScopeSelection:
    scope: str
    scope_id: int
    title: str
    provider_id: Optional[int]    # owning provider — access-control anchor
    patient_id: Optional[int]     # set for patient-rooted scopes
    conversation_ids: List[int] = field(default_factory=list)
    groups: List[Group] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class UnknownScopeError(ValueError):
    pass


class ScopeNotFoundError(LookupError):
    pass


def resolve_scope(scope, scope_id) -> ScopeSelection:
    try:
        resolver = _RESOLVERS[scope]
    except KeyError:
        raise UnknownScopeError(
            f"unknown scope {scope!r}; expected one of {SCOPES}"
        ) from None
    return resolver(scope_id)


# --- helpers ------------------------------------------------------------------

def _get_or_raise(model, entity_id, label):
    from ..extensions import db
    entity = db.session.get(model, entity_id)
    if entity is None:
        raise ScopeNotFoundError(f"{label} {entity_id} not found")
    return entity


def _conversation_ids_for_window(window_id) -> List[int]:
    rows = (Conversation.query.filter_by(window_id=window_id)
            .order_by(Conversation.created_at).with_entities(Conversation.id).all())
    return [r[0] for r in rows]


def _windows_for_enrollment(enrollment) -> List[ChatWindow]:
    """FK linkage preferred; flow_name match covers pre-FK legacy rows."""
    flow = enrollment.flow
    return (ChatWindow.query.filter(
        ChatWindow.patient_id == enrollment.patient_id,
        or_(
            ChatWindow.flow_id == enrollment.flow_id,
            and_(ChatWindow.flow_id.is_(None), ChatWindow.flow_name == flow.name),
        ),
    ).order_by(ChatWindow.start_date).all())


def _window_group(window) -> Group:
    label = window.title
    if window.phase_label and window.phase_label not in label:
        label = f"{label} ({window.phase_label})"
    return Group(
        key=f"window:{window.id}",
        label=label,
        order=window.start_date,
        conversation_ids=_conversation_ids_for_window(window.id),
    )


def _flatten(groups: List[Group]) -> List[int]:
    seen, ordered = set(), []
    for group in groups:
        for conversation_id in group.conversation_ids:
            if conversation_id not in seen:
                seen.add(conversation_id)
                ordered.append(conversation_id)
    return ordered


# --- resolvers ----------------------------------------------------------------

def _resolve_conversation(conversation_id):
    conversation = _get_or_raise(Conversation, conversation_id, "conversation")
    window = conversation.chat_window
    provider_id = window.provider_id if window else None
    if provider_id is None:  # window-less legacy chat: owning provider via link
        link = ProviderPatient.query.filter_by(patient_id=conversation.user_id).first()
        provider_id = link.provider_id if link else None
    return ScopeSelection(
        scope="conversation",
        scope_id=conversation_id,
        title=conversation.title or f"Conversation {conversation_id}",
        provider_id=provider_id,
        patient_id=conversation.user_id,
        conversation_ids=[conversation_id],
        groups=[],
    )


def _resolve_window(window_id):
    window = _get_or_raise(ChatWindow, window_id, "window")
    return ScopeSelection(
        scope="window",
        scope_id=window_id,
        title=window.title,
        provider_id=window.provider_id,
        patient_id=window.patient_id,
        conversation_ids=_conversation_ids_for_window(window_id),
        groups=[],
        meta={"phase_label": window.phase_label, "flow_name": window.flow_name},
    )


def _resolve_enrollment(enrollment_id):
    enrollment = _get_or_raise(FlowEnrollment, enrollment_id, "enrollment")
    flow = enrollment.flow
    groups = [_window_group(w) for w in _windows_for_enrollment(enrollment)]
    return ScopeSelection(
        scope="enrollment",
        scope_id=enrollment_id,
        title=f"{flow.name} — {enrollment.patient.username}",
        provider_id=flow.provider_id,
        patient_id=enrollment.patient_id,
        conversation_ids=_flatten(groups),
        groups=groups,
        meta={"flow_id": flow.id, "flow_name": flow.name,
              "enrolled_at": enrollment.enrolled_at},
    )


def _resolve_participant(patient_id):
    patient = _get_or_raise(User, patient_id, "participant")
    link = ProviderPatient.query.filter_by(patient_id=patient_id).first()
    provider_id = link.provider_id if link else None

    windows = (ChatWindow.query.filter_by(patient_id=patient_id)
               .order_by(ChatWindow.start_date).all())

    # Group windows by flow; flow-less windows form an "Unstructured" bucket.
    flow_groups: Dict[str, Group] = {}
    from ..extensions import db
    for window in windows:
        window_conversations = _conversation_ids_for_window(window.id)
        flow = None
        if window.flow_id is not None:
            flow = db.session.get(StudyFlow, window.flow_id)
        elif window.flow_name:  # legacy rows: name match
            flow = StudyFlow.query.filter_by(name=window.flow_name).first()

        key = f"flow:{flow.id}" if flow else "unaffiliated"
        label = flow.name if flow else "Unstructured windows"
        group = flow_groups.get(key)
        if group is None:
            group = flow_groups[key] = Group(
                key=key, label=label, order=window.start_date
            )
        group.conversation_ids.extend(window_conversations)

    # Window-less conversations (legacy free chat) get their own bucket.
    rows = (Conversation.query.filter_by(user_id=patient_id)
            .filter(Conversation.window_id.is_(None))
            .order_by(Conversation.created_at)
            .with_entities(Conversation.id, Conversation.created_at).all())
    if rows:
        flow_groups["free"] = Group(
            key="free",
            label="Free conversations",
            order=rows[0][1] or 0.0,
            conversation_ids=[r[0] for r in rows],
        )

    groups = sorted(flow_groups.values(), key=lambda g: g.order)
    return ScopeSelection(
        scope="participant",
        scope_id=patient_id,
        title=f"Participant {patient.username}",
        provider_id=provider_id,
        patient_id=patient_id,
        conversation_ids=_flatten(groups),
        groups=groups,
    )


def _resolve_flow(flow_id):
    flow = _get_or_raise(StudyFlow, flow_id, "flow")
    enrollments = (FlowEnrollment.query.filter_by(flow_id=flow_id)
                   .order_by(FlowEnrollment.enrolled_at).all())
    groups = []
    phase_participation: Dict[str, int] = {}
    for enrollment in enrollments:
        windows = _windows_for_enrollment(enrollment)
        conversation_ids = []
        for window in windows:
            window_conversations = _conversation_ids_for_window(window.id)
            conversation_ids.extend(window_conversations)
            if window_conversations:
                phase = window.phase_label or window.title
                phase_participation[phase] = phase_participation.get(phase, 0) + 1
        groups.append(Group(
            key=f"enrollment:{enrollment.id}",
            label=enrollment.patient.username,
            order=enrollment.enrolled_at,
            conversation_ids=conversation_ids,
        ))
    return ScopeSelection(
        scope="flow",
        scope_id=flow_id,
        title=flow.name,
        provider_id=flow.provider_id,
        patient_id=None,
        conversation_ids=_flatten(groups),
        groups=groups,
        meta={
            "enrollment_count": len(enrollments),
            "started_count": sum(1 for g in groups if g.conversation_ids),
            # per-phase count of participants with ≥1 conversation there
            "phase_participation": phase_participation,
        },
    )


def _resolve_account(provider_id):
    provider = _get_or_raise(User, provider_id, "provider")
    flows = (StudyFlow.query.filter_by(provider_id=provider_id)
             .order_by(StudyFlow.created_at).all())
    groups = []
    flow_meta = []
    for flow in flows:
        flow_selection = _resolve_flow(flow.id)
        groups.append(Group(
            key=f"flow:{flow.id}",
            label=flow.name,
            order=flow.created_at or 0.0,
            conversation_ids=flow_selection.conversation_ids,
        ))
        flow_meta.append({
            "flow_id": flow.id,
            "name": flow.name,
            "enrollment_count": flow_selection.meta["enrollment_count"],
            "started_count": flow_selection.meta["started_count"],
        })

    # Standalone windows: created directly by the provider, outside any flow.
    covered = {cid for g in groups for cid in g.conversation_ids}
    standalone_windows = (ChatWindow.query.filter_by(provider_id=provider_id)
                          .filter(ChatWindow.flow_id.is_(None),
                                  ChatWindow.flow_name.is_(None))
                          .order_by(ChatWindow.start_date).all())
    standalone_ids = []
    for window in standalone_windows:
        standalone_ids.extend(
            cid for cid in _conversation_ids_for_window(window.id) if cid not in covered
        )
    if standalone_ids:
        groups.append(Group(
            key="standalone",
            label="Standalone windows",
            order=standalone_windows[0].start_date,
            conversation_ids=standalone_ids,
        ))

    return ScopeSelection(
        scope="account",
        scope_id=provider_id,
        title=f"Study account — {provider.username}",
        provider_id=provider_id,
        patient_id=None,
        conversation_ids=_flatten(groups),
        groups=groups,
        meta={
            "flow_count": len(flows),
            "flows": flow_meta,
            "patient_count": ProviderPatient.query.filter_by(
                provider_id=provider_id).count(),
        },
    )


_RESOLVERS = {
    "conversation": _resolve_conversation,
    "window": _resolve_window,
    "enrollment": _resolve_enrollment,
    "participant": _resolve_participant,
    "flow": _resolve_flow,
    "account": _resolve_account,
}


# --- lightweight ownership (access control) -----------------------------------

def scope_owner(scope, scope_id):
    """(provider_id, patient_id) for a scope target WITHOUT resolving its
    conversation set — cheap enough for per-request access checks.

    Raises ScopeNotFoundError / UnknownScopeError like resolve_scope."""
    if scope == "conversation":
        conversation = _get_or_raise(Conversation, scope_id, "conversation")
        window = conversation.chat_window
        provider_id = window.provider_id if window else None
        if provider_id is None:
            link = ProviderPatient.query.filter_by(
                patient_id=conversation.user_id).first()
            provider_id = link.provider_id if link else None
        return provider_id, conversation.user_id
    if scope == "window":
        window = _get_or_raise(ChatWindow, scope_id, "window")
        return window.provider_id, window.patient_id
    if scope == "enrollment":
        enrollment = _get_or_raise(FlowEnrollment, scope_id, "enrollment")
        return enrollment.flow.provider_id, enrollment.patient_id
    if scope == "participant":
        _get_or_raise(User, scope_id, "participant")
        link = ProviderPatient.query.filter_by(patient_id=scope_id).first()
        return (link.provider_id if link else None), scope_id
    if scope == "flow":
        flow = _get_or_raise(StudyFlow, scope_id, "flow")
        return flow.provider_id, None
    if scope == "account":
        _get_or_raise(User, scope_id, "provider")
        return scope_id, None
    raise UnknownScopeError(f"unknown scope {scope!r}; expected one of {SCOPES}")
