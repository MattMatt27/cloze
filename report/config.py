"""
Report Configuration

Handles config normalization, migration from v1 (flat booleans) to v2
(hierarchical features), and provides defaults.

v1 format (legacy):
    {"ai_summary": true, "nlp_analysis": true, ...}

v2 format (current):
    {"version": 2, "report_type": "summary", "features": {"ai_summary": true, ...}}
"""

from typing import Any, Dict

from report.registry import get_registry

# v1 component key -> list of v2 feature keys it maps to
V1_TO_V2_MAPPING = {
    "ai_summary": ["ai_summary"],
    "saved_messages": ["saved_messages"],
    "descriptive_stats": ["descriptive_stats"],
    "nlp_analysis": ["sentiment_analysis", "voice_analysis", "keyword_analysis"],
    "cooccurrence_analysis": ["cooccurrence_analysis"],
}


def get_default_config() -> Dict[str, Any]:
    """Return the default config in v2 format with all available features enabled."""
    registry = get_registry()
    features = {key: True for key in registry.get_available_feature_keys()}
    return {
        "version": 2,
        "report_type": "summary",
        "features": features,
    }


def normalize_config(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize any config format (v1 flat or v2 hierarchical) to v2.

    Called every time a config is read from the database. Old v1 configs are
    never rewritten — they are translated on the fly.
    """
    if not raw_config:
        return get_default_config()

    # Already v2 format
    if raw_config.get("version") == 2:
        return raw_config

    # v1 flat format — migrate on the fly
    features = {}
    for v1_key, v2_keys in V1_TO_V2_MAPPING.items():
        enabled = raw_config.get(v1_key, True)  # default to True for missing keys
        for v2_key in v2_keys:
            features[v2_key] = enabled

    return {
        "version": 2,
        "report_type": "summary",
        "features": features,
    }


def is_feature_enabled(config: Dict[str, Any], feature_key: str) -> bool:
    """Check if a specific feature is enabled in a (possibly unnormalized) config."""
    normalized = normalize_config(config)
    return normalized.get("features", {}).get(feature_key, False)


def get_enabled_component_keys(config: Dict[str, Any]) -> set:
    """
    Get the set of component_keys that need to be instantiated.

    Multiple features may map to the same component (e.g., sentiment_analysis,
    voice_analysis, keyword_analysis all map to the nlp_analysis component).
    A component runs if ANY of its features are enabled.
    """
    normalized = normalize_config(config)
    features = normalized.get("features", {})
    registry = get_registry()

    component_keys = set()
    for feature_key, enabled in features.items():
        if enabled:
            meta = registry.get_feature(feature_key)
            if meta and meta.status == "available":
                component_keys.add(meta.component_key)

    return component_keys


def config_to_v1(config: Dict[str, Any]) -> Dict[str, bool]:
    """
    Convert a v2 config back to v1 flat format.

    A v1 key is enabled if ANY of its sub-features are enabled.
    Used for backward compatibility when passing config to existing components.
    """
    normalized = normalize_config(config)
    features = normalized.get("features", {})

    v1 = {}
    for v1_key, v2_keys in V1_TO_V2_MAPPING.items():
        v1[v1_key] = any(features.get(k, False) for k in v2_keys)

    return v1
