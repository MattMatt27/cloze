"""
Prompt Composer

Assembles the final system prompt from layers:

1. Universal (always) — forbidden content, AI honesty, crisis protocols,
   platform context, persona guardrails
2. Clinical safety (when is_clinical_use = true) — non-editable clinical
   restrictions
3. Monitoring disclosure (team-written freeform text)
4. Persona (default, overridable per provider)
5. Interaction context (default, overridable per provider)
6. Domain (anxiety, depression, etc.)
7. Safety plan (when is_clinical_use = true AND plan exists)
"""

from typing import Optional

from .registry import PromptRegistry


def compose_system_prompt(
    *,
    is_clinical_use: bool = True,
    monitoring_disclosure: Optional[str] = None,
    persona_override: Optional[str] = None,
    interaction_context_override: Optional[str] = None,
    domain_id: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    safety_plan: Optional[dict] = None,
) -> str:
    """
    Assemble full system prompt from layers.

    Args:
        is_clinical_use: Whether clinical safety prompt is loaded
        monitoring_disclosure: Team-written monitoring disclosure text
        persona_override: Replaces the default persona prompt
        interaction_context_override: Replaces the default interaction context
        domain_id: Domain prompt to include (e.g. "anxiety")
        custom_instructions: Provider's custom instructions text
        safety_plan: Patient's active safety plan dict

    Returns:
        The fully composed system prompt string.
    """
    registry = PromptRegistry.instance()
    sections = []

    # Layer 1: Universal (always loaded, not editable)
    for prompt in registry.get_universal_prompts():
        sections.append(prompt.content)

    # Layer 2: Study context (conditional prompts from study_context/)
    if is_clinical_use:
        clinical = registry.get_study_context_prompt('clinical_safety')
        if clinical:
            sections.append(clinical.content)

    # PII protection — loaded when no safety plan is active (safety plans
    # are inherently personal, so PII restrictions conflict with them)
    if not safety_plan:
        pii = registry.get_study_context_prompt('pii_protection')
        if pii:
            sections.append(pii.content)

    # Layer 3: Monitoring disclosure (team-written)
    if monitoring_disclosure and monitoring_disclosure.strip():
        sections.append(
            f"## Conversation Monitoring\n\n{monitoring_disclosure.strip()}"
        )

    # Layer 4: Persona (overridable, '__disabled__' = skip entirely)
    if persona_override == '__disabled__':
        pass  # Provider explicitly disabled this layer
    elif persona_override and persona_override.strip():
        sections.append(persona_override.strip())
    else:
        default_persona = registry.get_default_prompt('default_persona')
        if default_persona:
            sections.append(default_persona.content)

    # Layer 5: Interaction context (overridable, '__disabled__' = skip entirely)
    if interaction_context_override == '__disabled__':
        pass  # Provider explicitly disabled this layer
    elif interaction_context_override and interaction_context_override.strip():
        sections.append(interaction_context_override.strip())
    else:
        default_context = registry.get_default_prompt('default_interaction_context')
        if default_context:
            sections.append(default_context.content)

    # Layer 6: Domain prompt
    if domain_id:
        domain = registry.get_domain_prompt(domain_id)
        if domain:
            sections.append(f"## Clinical Focus\n\n{domain.content}")

    # Layer 7: Custom instructions (provider-written per conversation)
    if custom_instructions and custom_instructions.strip():
        sections.append(
            f"## Additional Instructions\n\n{custom_instructions.strip()}"
        )

    # Layer 8: Safety plan (when clinical + plan exists)
    if is_clinical_use and safety_plan:
        sections.append(_format_safety_plan(safety_plan))

    return "\n\n---\n\n".join(sections)


# ── Safety plan prompt formatting ──────────────────────────────
# Adapted from Beyond Boilerplate's PromptBuilder + ConstraintFormatter
# + EscalationFrameworkBuilder for Cloze's UI-driven workflow.

_SEVERITY_LABELS = {1: 'mild', 2: 'mild-moderate', 3: 'moderate', 4: 'moderate-severe', 5: 'severe'}
_EFFECTIVENESS_LABELS = {1: 'minimal', 2: 'low', 3: 'moderate', 4: 'high', 5: 'very high'}
_COMFORT_LABELS = {1: 'very low', 2: 'low', 3: 'moderate', 4: 'high', 5: 'very high'}


def _format_safety_plan(safety_plan: dict) -> str:
    """Format a structured safety plan dict into prompt text.

    Expects the output of SafetyPlan.to_prompt_dict() with keys:
        warning_signs, coping_strategies, support_network, care_team,
        emergency_plan, reasons_for_living, anti_patterns, conflicts.
    """
    parts = []

    # Integration guidance
    parts.append(_build_integration_guidance())

    # Header
    parts.append("## Patient Safety Plan")

    # Warning signs
    warning_signs = safety_plan.get('warning_signs', [])
    if warning_signs:
        lines = ["### Warning Signs"]
        for ws in warning_signs:
            severity = _SEVERITY_LABELS.get(ws.get('severity', 3), 'moderate')
            line = f'- "{ws.get("sign", "")}" (severity: {severity}'
            if ws.get('context'):
                line += f', context: {ws["context"]}'
            line += ')'
            lines.append(line)
        parts.append('\n'.join(lines))

    # Coping strategies
    strategies = safety_plan.get('coping_strategies', [])
    if strategies:
        lines = ["### Coping Strategies"]
        for cs in strategies:
            effectiveness = _EFFECTIVENESS_LABELS.get(cs.get('effectiveness', 3), 'moderate')
            line = f'- {cs.get("strategy", "")}'
            if cs.get('context'):
                line += f' ({cs["context"]})'
            lines.append(line)
            if cs.get('patient_language'):
                lines.append(f'  They call this: "{cs["patient_language"]}"')
            lines.append(f'  Effectiveness: {effectiveness}')
        parts.append('\n'.join(lines))

    # Support network
    network = safety_plan.get('support_network', [])
    if network:
        lines = ["### Support Network"]
        for sc in network:
            comfort = _COMFORT_LABELS.get(sc.get('comfort_level', 3), 'moderate')
            line = f'- {sc.get("person", "")} ({sc.get("relationship", "")})'
            line += f' — prefers: {sc.get("contact_preference", "")}'
            line += f', comfort: {comfort}'
            lines.append(line)
        parts.append('\n'.join(lines))

    # Care team
    care_team = safety_plan.get('care_team', [])
    if care_team:
        lines = ["### Care Team"]
        for cp in care_team:
            line = f'- {cp.get("name", "")} ({cp.get("role", "")})'
            line += f' — {cp.get("contact_protocol", "")}'
            lines.append(line)
            if cp.get('after_hours'):
                lines.append(f'  After hours: {cp["after_hours"]}')
        parts.append('\n'.join(lines))

    # Emergency plan
    emergency = safety_plan.get('emergency_plan', {})
    if emergency:
        lines = ["### Emergency Plan"]
        if emergency.get('activation_conditions'):
            lines.append(f'Activate when: {emergency["activation_conditions"]}')
        if emergency.get('preferred_facility'):
            lines.append(f'Preferred facility: {emergency["preferred_facility"]}')
        if emergency.get('contraindications'):
            lines.append(f'Avoid: {emergency["contraindications"]}')
        parts.append('\n'.join(lines))

    # Reasons for living
    reasons = safety_plan.get('reasons_for_living', [])
    if reasons:
        lines = ["### Reasons for Living"]
        for rfl in reasons:
            line = f'- "{rfl.get("reason", "")}"'
            if rfl.get('context'):
                line += f' ({rfl["context"]})'
            lines.append(line)
        parts.append('\n'.join(lines))

    # Hard constraints (anti-patterns) — imperative format
    anti_patterns = safety_plan.get('anti_patterns', [])
    if anti_patterns:
        parts.append(_format_constraints(anti_patterns))

    # Conflict framing
    conflicts = safety_plan.get('conflicts', [])
    if conflicts:
        parts.append(_format_conflicts(anti_patterns, conflicts))

    return '\n\n'.join(parts)


def _build_integration_guidance() -> str:
    """Instructions for how to use the safety plan in conversation."""
    return (
        "## How to Use This Safety Plan\n\n"
        "You have access to a personalized safety plan built with this person "
        "and their provider. This plan should INFORM your approach, not be recited.\n\n"
        "CRITICAL RULES:\n"
        "1. DO NOT reference information the person has not shared in THIS "
        "conversation. Wait for them to bring up a topic, then use what you "
        "know to engage more deeply.\n"
        "2. If you need to reference the safety plan directly, explain how you "
        'know: "When you worked on safety planning with your provider, you '
        'mentioned..." Do not drop prior knowledge without attribution.\n'
        "3. Use the plan to AVOID harm. The anti-patterns section tells you "
        "what NOT to do. This is the most important part of the plan.\n"
        "4. Use the plan to guide your questions. If you know their coping "
        "strategies, you can ask about those strategies when relevant "
        "— but frame it as a question, not a statement of fact.\n"
        "5. The plan is a guide, not a script. The person in front of you "
        "right now may be different from who they were during safety planning."
    )


def _format_constraints(anti_patterns: list[dict]) -> str:
    """Format anti-patterns as imperative hard constraints."""
    header = (
        "### Hard Constraints\n\n"
        "The following have been identified as harmful for this person. "
        "Do NOT use them:"
    )
    items = []
    for ap in anti_patterns:
        reason_part = f' ({ap["reason"]})' if ap.get('reason') else ''
        items.append(f'- Do NOT {ap.get("pattern", "")}{reason_part}')
    return header + '\n' + '\n'.join(items)


def _format_conflicts(all_anti_patterns: list[dict], conflicts: list[dict]) -> str:
    """Format conflicting anti-patterns with framing text."""
    lines = [
        "### Anti-Pattern Conflicts\n",
        "The following anti-patterns have been flagged as potentially conflicting. "
        "Both remain in effect. Use your judgement to navigate the tension between them:"
    ]

    for conflict_ap in conflicts:
        other_idx = conflict_ap.get('conflicts_with')
        if other_idx is not None and other_idx < len(all_anti_patterns):
            other = all_anti_patterns[other_idx]
            lines.append(f'\n- Constraint A: Do NOT {conflict_ap.get("pattern", "")}')
            lines.append(f'  Constraint B: Do NOT {other.get("pattern", "")}')
            if conflict_ap.get('conflict_rationale'):
                lines.append(f'  Provider note: {conflict_ap["conflict_rationale"]}')

    return '\n'.join(lines)
