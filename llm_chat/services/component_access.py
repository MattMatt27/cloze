"""Tiered component access — the analysis-library governance model.

Every component is *visible* to every researcher (discoverability first: this
is meant to grow into an extensible analysis library). Usage is tiered by the
registry's ``cost``:

- ``standard`` — freely usable by any team
- ``intensive`` — compute-heavy (LLM summaries today); requires a per-team
  admin **grant**. Researchers request; admins grant/revoke from the provider
  drill-down.

Grant state lives on ``ProviderFeatureFlags.report_component_grants`` as JSON
``{component_key: "requested" | "granted"}``. Enforcement happens both at
template save and at generation time (defense in depth).
"""

import json

from report.registry_v2 import COMPONENTS

from ..extensions import db
from ..models import ProviderFeatureFlags


def _flags_for(provider_id, create=False):
    flags = ProviderFeatureFlags.query.filter_by(provider_id=provider_id).first()
    if flags is None and create:
        flags = ProviderFeatureFlags(provider_id=provider_id)
        db.session.add(flags)
    return flags


def _grants(provider_id):
    flags = _flags_for(provider_id)
    if flags is None or not flags.report_component_grants:
        return {}
    try:
        grants = json.loads(flags.report_component_grants)
    except ValueError:
        return {}
    return grants if isinstance(grants, dict) else {}


def component_access(provider_id):
    """{component_key: "available" | "requestable" | "requested" | "granted"}

    "available"  — standard cost, always usable
    "granted"    — intensive, admin-granted (usable)
    "requested"  — intensive, request pending (not usable)
    "requestable"— intensive, no request yet (not usable)
    """
    grants = _grants(provider_id)
    access = {}
    for key, definition in COMPONENTS.items():
        if definition.cost == "standard":
            access[key] = "available"
        else:
            access[key] = grants.get(key) if grants.get(key) in (
                "requested", "granted") else "requestable"
    return access


def usable_components(provider_id):
    """The set of component keys this provider may actually run."""
    return {key for key, state in component_access(provider_id).items()
            if state in ("available", "granted")}


def request_component(provider_id, component_key):
    """Provider asks for an intensive component. Idempotent; granted stays
    granted. Raises ValueError for unknown/standard components."""
    definition = COMPONENTS.get(component_key)
    if definition is None:
        raise ValueError(f"unknown component {component_key!r}")
    if definition.cost != "intensive":
        raise ValueError(f"component {component_key!r} does not require a grant")
    flags = _flags_for(provider_id, create=True)
    grants = _grants(provider_id)
    if grants.get(component_key) != "granted":
        grants[component_key] = "requested"
    flags.report_component_grants = json.dumps(grants)
    db.session.commit()
    return grants[component_key]


def set_grant(provider_id, component_key, granted):
    """Admin grants or revokes an intensive component for a team."""
    definition = COMPONENTS.get(component_key)
    if definition is None:
        raise ValueError(f"unknown component {component_key!r}")
    if definition.cost != "intensive":
        raise ValueError(f"component {component_key!r} does not require a grant")
    flags = _flags_for(provider_id, create=True)
    grants = _grants(provider_id)
    if granted:
        grants[component_key] = "granted"
    else:
        grants.pop(component_key, None)  # revoke clears request state too
    flags.report_component_grants = json.dumps(grants) if grants else None
    db.session.commit()
    return grants.get(component_key)


def pending_requests():
    """[(provider_id, component_key)] across all teams — the admin queue."""
    rows = ProviderFeatureFlags.query.filter(
        ProviderFeatureFlags.report_component_grants.isnot(None)).all()
    pending = []
    for flags in rows:
        try:
            grants = json.loads(flags.report_component_grants)
        except ValueError:
            continue
        for key, state in grants.items():
            if state == "requested":
                pending.append((flags.provider_id, key))
    return pending
