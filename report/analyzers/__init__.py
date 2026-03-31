"""
Text Analyzers Package

Pure utility functions for analyzing text. These are reusable algorithms
that can be used by any component.

Imports are lazy to avoid loading heavy NLP dependencies (textblob, spacy,
sklearn) at application startup.
"""


def __getattr__(name):
    if name == 'SentimentAnalyzer':
        from .sentiment import SentimentAnalyzer
        return SentimentAnalyzer
    if name == 'VoiceAnalyzer':
        from .voice_analysis import VoiceAnalyzer
        return VoiceAnalyzer
    if name == 'KeywordAnalyzer':
        from .keyword_extraction import KeywordAnalyzer
        return KeywordAnalyzer
    if name == 'CooccurrenceAnalyzer':
        from .cooccurrence import CooccurrenceAnalyzer
        return CooccurrenceAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'SentimentAnalyzer',
    'VoiceAnalyzer',
    'KeywordAnalyzer',
    'CooccurrenceAnalyzer',
]
