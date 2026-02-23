"""
Feature Registry

Central registry of all analysis features with metadata for UI generation,
config validation, and feature discovery.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import OrderedDict


@dataclass
class FeatureGroup:
    """A logical grouping of analysis features."""
    key: str
    name: str
    description: str
    order: int
    icon: str = ""


@dataclass
class FeatureMetadata:
    """Metadata for a single analysis feature."""
    key: str
    name: str
    description: str
    group: str                          # group key
    component_key: str                  # maps to COMPONENT_REGISTRY key
    dependencies: List[str] = field(default_factory=list)
    citation: str = ""
    status: str = "available"           # "available" | "coming_soon" | "licensed"
    report_modes: List[str] = field(default_factory=lambda: ["summary", "detailed"])
    order: int = 0


class FeatureRegistry:
    """Singleton registry for all analysis features."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._groups = OrderedDict()
            cls._instance._features = OrderedDict()
            cls._instance._initialized = False
        return cls._instance

    def register_group(self, group: FeatureGroup):
        self._groups[group.key] = group

    def register_feature(self, feature: FeatureMetadata):
        self._features[feature.key] = feature

    def get_feature(self, key: str) -> Optional[FeatureMetadata]:
        return self._features.get(key)

    def get_group(self, key: str) -> Optional[FeatureGroup]:
        return self._groups.get(key)

    def get_all_features(self) -> Dict[str, FeatureMetadata]:
        return dict(self._features)

    def get_all_groups(self) -> Dict[str, FeatureGroup]:
        return dict(self._groups)

    def get_features_by_group(self) -> Dict[str, List[FeatureMetadata]]:
        """Return features organized by group, sorted by order."""
        grouped = {key: [] for key in self._groups}

        for feature in self._features.values():
            if feature.group in grouped:
                grouped[feature.group].append(feature)

        for group_key in grouped:
            grouped[group_key].sort(key=lambda f: f.order)

        return grouped

    def get_available_feature_keys(self) -> List[str]:
        """Return keys of features with status 'available'."""
        return [k for k, f in self._features.items() if f.status == "available"]

    def get_all_feature_keys(self) -> List[str]:
        """Return all feature keys including coming_soon."""
        return list(self._features.keys())

    def validate_config(self, features: dict) -> dict:
        """Validate and normalize a features dict. Returns only valid available keys."""
        available = set(self.get_available_feature_keys())
        return {k: bool(v) for k, v in features.items() if k in available}

    def to_ui_schema(self) -> List[Dict]:
        """Generate UI-ready schema for the template."""
        result = []
        grouped = self.get_features_by_group()

        for group_key, group in sorted(self._groups.items(), key=lambda x: x[1].order):
            features = grouped.get(group_key, [])
            group_data = {
                "key": group.key,
                "name": group.name,
                "description": group.description,
                "icon": group.icon,
                "features": [
                    {
                        "key": f.key,
                        "name": f.name,
                        "description": f.description,
                        "status": f.status,
                        "citation": f.citation,
                        "report_modes": f.report_modes,
                    }
                    for f in features
                ],
            }
            result.append(group_data)

        return result


def _init_registry() -> FeatureRegistry:
    """Initialize the registry with all known features."""
    registry = FeatureRegistry()
    if registry._initialized:
        return registry

    # -- Groups --
    groups = [
        FeatureGroup("clinical_overview", "Clinical Overview",
                     "AI-generated summaries and clinical notes", 1, "clipboard"),
        FeatureGroup("conversation_data", "Conversation Data",
                     "Raw data from sessions", 2, "messages"),
        FeatureGroup("conversation_metrics", "Conversation Metrics",
                     "Quantitative statistics about sessions", 3, "chart"),
        FeatureGroup("emotion_analysis", "Emotion Analysis",
                     "Sentiment and emotional pattern detection", 4, "heart"),
        FeatureGroup("linguistic_analysis", "Linguistic Analysis",
                     "Language patterns and communication style", 5, "brain"),
        FeatureGroup("conversation_dynamics", "Conversation Dynamics",
                     "Patterns in how conversations unfold", 6, "network"),
        FeatureGroup("psycholinguistic_measures", "Psycholinguistic Measures",
                     "Validated psychological language measures", 7, "psychology"),
    ]
    for g in groups:
        registry.register_group(g)

    # -- Available features (map to existing components) --
    features = [
        FeatureMetadata(
            key="ai_summary",
            name="AI Summary",
            description="Intelligent analysis of conversation themes and progress",
            group="clinical_overview",
            component_key="ai_summary",
            dependencies=["llama"],
            citation="Local LLM (Llama)",
            status="available",
            order=1,
        ),
        FeatureMetadata(
            key="saved_messages",
            name="Saved Messages",
            description="Important messages flagged during sessions",
            group="conversation_data",
            component_key="saved_messages",
            dependencies=[],
            status="available",
            order=1,
        ),
        FeatureMetadata(
            key="descriptive_stats",
            name="Descriptive Statistics",
            description="Message counts, word counts, session duration",
            group="conversation_metrics",
            component_key="descriptive_stats",
            dependencies=[],
            status="available",
            order=1,
        ),
        FeatureMetadata(
            key="sentiment_analysis",
            name="Sentiment Analysis",
            description="Polarity analysis of user messages (positive/neutral/negative)",
            group="emotion_analysis",
            component_key="nlp_analysis",
            dependencies=["textblob"],
            citation="TextBlob (Loria, 2018)",
            status="available",
            order=1,
        ),
        FeatureMetadata(
            key="keyword_analysis",
            name="Emotional Keywords",
            description="Detection of emotional language patterns",
            group="emotion_analysis",
            component_key="nlp_analysis",
            dependencies=[],
            citation="Custom keyword lexicon",
            status="available",
            order=2,
        ),
        FeatureMetadata(
            key="voice_analysis",
            name="Voice Analysis",
            description="Active vs passive voice usage patterns",
            group="linguistic_analysis",
            component_key="nlp_analysis",
            dependencies=["spacy"],
            citation="spaCy (Honnibal & Montani, 2017)",
            status="available",
            order=1,
        ),
        FeatureMetadata(
            key="cooccurrence_analysis",
            name="Word Co-occurrence Network",
            description="Word relationship network showing conversation themes",
            group="conversation_dynamics",
            component_key="cooccurrence_analysis",
            dependencies=["nltk", "networkx", "matplotlib"],
            citation="NLTK + NetworkX",
            status="available",
            order=1,
        ),

        # -- Coming soon (Phase 2 placeholders) --
        FeatureMetadata(
            key="liwc_analysis",
            name="LIWC Analysis",
            description="Validated psycholinguistic word categories (requires license)",
            group="psycholinguistic_measures",
            component_key="liwc_analysis",
            dependencies=["liwc"],
            citation="Pennebaker et al. (2015)",
            status="coming_soon",
            order=1,
        ),
        FeatureMetadata(
            key="readability_metrics",
            name="Readability Metrics",
            description="Flesch-Kincaid, Gunning Fog, and other readability scores",
            group="linguistic_analysis",
            component_key="readability_metrics",
            dependencies=["textstat"],
            citation="Kincaid et al. (1975)",
            status="coming_soon",
            order=2,
        ),
        FeatureMetadata(
            key="lexical_diversity",
            name="Lexical Diversity",
            description="Vocabulary richness measures (MATTR, MTLD)",
            group="linguistic_analysis",
            component_key="lexical_diversity",
            dependencies=["lexicalrichness"],
            citation="McCarthy (2005); Covington & McFall (2010)",
            status="coming_soon",
            order=3,
        ),
        FeatureMetadata(
            key="turn_taking_patterns",
            name="Turn-Taking Patterns",
            description="Analysis of conversational turn structure and response patterns",
            group="conversation_dynamics",
            component_key="turn_taking_patterns",
            dependencies=[],
            status="coming_soon",
            order=2,
        ),
    ]
    for f in features:
        registry.register_feature(f)

    registry._initialized = True
    return registry


def get_registry() -> FeatureRegistry:
    """Get the initialized feature registry."""
    return _init_registry()
