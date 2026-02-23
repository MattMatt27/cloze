"""
Co-occurrence Analysis Component

Provides word co-occurrence network analysis for conversation messages.
"""

from typing import Dict, Any

from report.base import ReportComponent
from report.analyzers.cooccurrence import CooccurrenceAnalyzer


class CooccurrenceAnalysisComponent(ReportComponent):
    """Component for word co-occurrence network analysis."""

    def generate(self) -> Dict[str, Any]:
        """
        Generate co-occurrence analysis for user messages.

        Returns:
            Dict containing:
                - cooccurrence_matrix: Word pair frequencies
                - top_words: Most frequent words with counts
                - total_unique_words: Count of unique words
                - total_sentences: Number of sentences analyzed
                - graph_image: Base64-encoded network graph (if available)
                - has_visualization: Whether visualization was generated
                - message_count: Number of messages analyzed
        """
        user_messages = [m for m in self.messages if m.role == 'user']

        if not user_messages:
            return self._empty_analysis()

        # Extract message texts
        message_texts = [msg.content for msg in user_messages]

        # Get configuration parameters
        min_cooccurrence = self.config.get('cooccurrence_min_count', 2)
        top_n_words = self.config.get('cooccurrence_top_n', 20)
        graph_style = 'academic' if self.config.get('report_type') == 'detailed' else 'product'

        # Run analyzer
        try:
            analyzer = CooccurrenceAnalyzer(
                min_cooccurrence=min_cooccurrence,
                top_n_words=top_n_words,
                graph_style=graph_style
            )
            results = analyzer.analyze(message_texts)

            # Add message count
            results['message_count'] = len(user_messages)

            return results

        except Exception as e:
            print(f"Error in co-occurrence analysis: {e}")
            return {
                **self._empty_analysis(),
                'error': str(e)
            }

    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "cooccurrence_matrix": {},
            "top_words": [],
            "total_unique_words": 0,
            "total_sentences": 0,
            "graph_image": None,
            "has_visualization": False,
            "message_count": 0
        }
