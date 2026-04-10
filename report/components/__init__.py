"""
Report Components Package

Components are self-contained features that generate data for reports.
Each component loads data, performs analysis, and returns structured results.

NLP-heavy components are imported lazily to keep startup fast.
"""

from typing import Dict
from .ai_summary import AISummaryComponent
from .saved_messages import SavedMessagesComponent
from .descriptive_stats import DescriptiveStatsComponent

__all__ = [
    'AISummaryComponent',
    'SavedMessagesComponent',
    'DescriptiveStatsComponent',
    'NLPAnalysisComponent',
    'CooccurrenceAnalysisComponent',
    'get_all_components',
]


def _get_component_registry():
    """Build registry with lazy imports for NLP-heavy components."""
    from .nlp_analysis import NLPAnalysisComponent
    from .cooccurrence_analysis import CooccurrenceAnalysisComponent
    return {
        'ai_summary': AISummaryComponent,
        'saved_messages': SavedMessagesComponent,
        'descriptive_stats': DescriptiveStatsComponent,
        'nlp_analysis': NLPAnalysisComponent,
        'cooccurrence_analysis': CooccurrenceAnalysisComponent,
    }


def get_all_components(window, config: Dict = None):
    """
    Instantiate all registered components for a given window.

    Args:
        window: ChatWindow object or window_id
        config: Optional configuration dict

    Returns:
        Dict mapping component names to component instances
    """
    # Handle both ChatWindow objects and window IDs
    if hasattr(window, 'id'):
        window_id = window.id
        if config is None:
            config = window.get_report_config()
    else:
        window_id = window

    config = config or {}

    # Instantiate all components
    registry = _get_component_registry()
    components = {}
    for name, component_class in registry.items():
        components[name] = component_class(window_id, config)

    return components
