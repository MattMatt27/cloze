"""Tests for the layered prompt composer — the core of Cloze's
configurable-but-safe prompt architecture.

The universal safety floor must always be present; study/provider/per-conversation
layers must appear only under their documented conditions.
"""
import pytest

from prompts.composer import compose_system_prompt
from prompts.registry import PromptRegistry


@pytest.fixture
def registry():
    PromptRegistry.reset()
    reg = PromptRegistry.instance()
    yield reg
    PromptRegistry.reset()


SAMPLE_SAFETY_PLAN = {
    "warning_signs": [{"sign": "racing thoughts", "severity": 4}],
    "coping_strategies": [{"strategy": "box breathing", "effectiveness": 4}],
    "anti_patterns": [
        {"pattern": "use exposure-based techniques", "reason": "prior trauma"}
    ],
}


def test_universal_layers_always_present(registry):
    """Every universal prompt appears regardless of configuration."""
    out = compose_system_prompt(is_clinical_use=False)
    universal = registry.get_universal_prompts()
    assert universal, "expected universal prompts to be loaded from disk"
    for prompt in universal:
        assert prompt.content in out


def test_clinical_layer_toggles_with_is_clinical_use(registry):
    clinical = registry.get_study_context_prompt("clinical_safety").content
    assert clinical in compose_system_prompt(is_clinical_use=True)
    assert clinical not in compose_system_prompt(is_clinical_use=False)


def test_pii_layer_loads_only_without_safety_plan(registry):
    pii = registry.get_study_context_prompt("pii_protection").content
    # No safety plan -> PII protection loaded
    assert pii in compose_system_prompt(is_clinical_use=True)
    # Safety plan active -> PII protection withheld (plan needs personal context)
    assert pii not in compose_system_prompt(
        is_clinical_use=True, safety_plan=SAMPLE_SAFETY_PLAN
    )


def test_persona_override_replaces_default(registry):
    default_persona = registry.get_default_prompt("default_persona").content
    out = compose_system_prompt(persona_override="You are a terse coach.")
    assert "You are a terse coach." in out
    assert default_persona not in out


def test_persona_disabled_sentinel_removes_layer(registry):
    default_persona = registry.get_default_prompt("default_persona").content
    out = compose_system_prompt(persona_override="__disabled__")
    assert default_persona not in out
    assert "__disabled__" not in out


def test_domain_layer_included_when_requested(registry):
    domain = registry.get_domain_prompt("anxiety").content
    out = compose_system_prompt(domain_id="anxiety")
    assert "## Clinical Focus" in out
    assert domain in out


def test_custom_instructions_appended(registry):
    out = compose_system_prompt(custom_instructions="Follow protocol X step by step.")
    assert "## Additional Instructions" in out
    assert "Follow protocol X step by step." in out


def test_safety_plan_only_rendered_for_clinical_use(registry):
    clinical_out = compose_system_prompt(
        is_clinical_use=True, safety_plan=SAMPLE_SAFETY_PLAN
    )
    assert "## Patient Safety Plan" in clinical_out

    nonclinical_out = compose_system_prompt(
        is_clinical_use=False, safety_plan=SAMPLE_SAFETY_PLAN
    )
    assert "## Patient Safety Plan" not in nonclinical_out


def test_anti_patterns_render_as_hard_constraints(registry):
    out = compose_system_prompt(is_clinical_use=True, safety_plan=SAMPLE_SAFETY_PLAN)
    assert "Hard Constraints" in out
    assert "Do NOT use exposure-based techniques" in out


def test_layers_joined_with_separator(registry):
    """Composed sections are delimited so layers stay distinct."""
    out = compose_system_prompt(is_clinical_use=True)
    assert "\n\n---\n\n" in out
