"""
Unified Report Generator System
================================
A scalable, component-based report generation system that supports:
- Multiple output formats (HTML, PDF, JSON)
- Configurable report components
- Easy extension for new NLP features
- Consistent styling across all report types
"""

import json
import time
import tempfile
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
import google.generativeai as genai
from textblob import TextBlob
import spacy

# PDF generation - optional dependency
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    # Handle both import errors and system dependency errors
    WEASYPRINT_AVAILABLE = False
    print(f"Warning: WeasyPrint not available for PDF generation: {e}")

from llm_chat.models import (
    ChatWindow, Conversation, Message, SavedSelection,
    Report, User, Model
)
from llm_chat.extensions import db


class ReportComponent(ABC):
    """Abstract base class for report components"""

    def __init__(self, window_id: int, config: Dict[str, Any] = None):
        self.window_id = window_id
        self.config = config or {}
        self.window = None
        self.conversations = []
        self.messages = []
        self._load_data()

    def _load_data(self):
        """Load common data needed by most components"""
        self.window = ChatWindow.query.get(self.window_id)
        if not self.window:
            raise ValueError(f"ChatWindow with id {self.window_id} not found")

        self.conversations = Conversation.query.filter_by(window_id=self.window_id).all()

        # Get all messages for all conversations
        for conv in self.conversations:
            self.messages.extend(Message.query.filter_by(conversation_id=conv.id).all())

    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        """Generate component data"""
        pass

    @abstractmethod
    def render_html(self, data: Dict[str, Any]) -> str:
        """Render component as HTML"""
        pass

    @abstractmethod
    def render_pdf(self, data: Dict[str, Any]) -> str:
        """Render component for PDF (returns HTML optimized for print)"""
        pass


class AISummaryComponent(ReportComponent):
    """AI-powered conversation summary component"""

    def generate(self) -> Dict[str, Any]:
        """Generate AI summary using Gemini"""
        if not self.messages:
            return {
                "summary": "No messages to summarize.",
                "themes": [],
                "progress_notes": "",
                "generated_with": "No model"
            }

        try:
            # Select appropriate model
            model = self._select_gemini_model()

            # Prepare conversation text
            conversation_text = self._prepare_conversation_text()

            # Generate summary prompt
            prompt = f"""
            Please analyze this series of chat conversations from a therapy/support window and provide:
            1. A comprehensive summary (2-3 paragraphs)
            2. Key themes identified (list up to 5)
            3. Brief progress notes suitable for clinical documentation

            Conversations:
            {conversation_text}

            Format your response as:
            SUMMARY:
            [Your summary here]

            THEMES:
            - Theme 1
            - Theme 2
            [etc]

            PROGRESS NOTES:
            [Your clinical notes here]
            """

            response = model.generate_content(prompt)
            return self._parse_ai_response(response.text, model.name)

        except Exception as e:
            return {
                "summary": f"Error generating AI summary: {str(e)}",
                "themes": [],
                "progress_notes": "",
                "error": str(e)
            }

    def _select_gemini_model(self):
        """Select the best available Gemini model"""
        # Get API key from environment
        import os
        google_key = os.getenv('GOOGLE_API_KEY')
        if not google_key or google_key.strip() == '' or google_key == 'your_google_api_key_here':
            raise ValueError("Google API key not configured")

        # Configure genai with API key
        genai.configure(api_key=google_key)

        # Check available models in database
        available_models = Model.query.filter(
            Model.name.like('gemini%'),
            Model.visible == True
        ).all()

        # Prioritize models
        priority_order = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']

        for model_name in priority_order:
            model = next((m for m in available_models if m.name == model_name), None)
            if model:
                return genai.GenerativeModel(model_name)

        # Fallback to any available Gemini model
        if available_models:
            model = available_models[0]
            return genai.GenerativeModel(model.name)

        raise ValueError("No Gemini models available")

    def _prepare_conversation_text(self) -> str:
        """Prepare conversation text for AI analysis"""
        text_parts = []
        for conv in self.conversations:
            conv_messages = [m for m in self.messages if m.conversation_id == conv.id]
            if conv_messages:
                text_parts.append(f"\n--- Conversation: {conv.title} ---")
                for msg in sorted(conv_messages, key=lambda x: x.timestamp):
                    timestamp = datetime.fromtimestamp(msg.timestamp).strftime('%Y-%m-%d %H:%M')
                    text_parts.append(f"[{timestamp}] {msg.role}: {msg.content}")
        return "\n".join(text_parts)

    def _parse_ai_response(self, response_text: str, model_name: str) -> Dict[str, Any]:
        """Parse the AI response into structured data"""
        parts = response_text.split('\n\n')
        summary = ""
        themes = []
        progress_notes = ""

        current_section = None
        for line in response_text.split('\n'):
            if 'SUMMARY:' in line:
                current_section = 'summary'
            elif 'THEMES:' in line:
                current_section = 'themes'
            elif 'PROGRESS NOTES:' in line:
                current_section = 'progress'
            elif current_section == 'summary' and line.strip():
                summary += line.strip() + " "
            elif current_section == 'themes' and line.strip().startswith('-'):
                themes.append(line.strip()[1:].strip())
            elif current_section == 'progress' and line.strip():
                progress_notes += line.strip() + " "

        return {
            "summary": summary.strip(),
            "themes": themes,
            "progress_notes": progress_notes.strip(),
            "generated_with": model_name
        }

    def render_html(self, data: Dict[str, Any]) -> str:
        """Render AI summary as HTML"""
        html = f"""
        <div class="report-component ai-summary">
            <div class="component-header">
                <span class="component-icon">🤖</span>
                <h3 class="component-title">AI Summary</h3>
            </div>
            <div class="summary-content">
                <p class="summary-text">{data.get('summary', 'No summary available')}</p>
        """

        if data.get('themes'):
            html += """
                <div class="themes-section">
                    <h4>Key Themes Identified:</h4>
                    <ul class="themes-list">
            """
            for theme in data['themes']:
                html += f"<li>{theme}</li>"
            html += "</ul></div>"

        if data.get('progress_notes'):
            html += f"""
                <div class="progress-notes">
                    <h4>Progress Notes:</h4>
                    <p>{data['progress_notes']}</p>
                </div>
            """

        html += f"""
                <p class="generated-by">Generated with {data.get('generated_with', 'AI')}</p>
            </div>
        </div>
        """
        return html

    def render_pdf(self, data: Dict[str, Any]) -> str:
        """Render for PDF - simpler formatting"""
        return self.render_html(data)  # Can customize for print later


class SavedMessagesComponent(ReportComponent):
    """Saved message selections component"""

    def generate(self) -> Dict[str, Any]:
        """Get saved message selections"""
        conv_ids = [c.id for c in self.conversations]

        if not conv_ids:
            return {"selections": [], "total_count": 0}

        selections = SavedSelection.query.filter(
            SavedSelection.conversation_id.in_(conv_ids)
        ).order_by(SavedSelection.created_at.desc()).all()

        selections_data = []
        for selection in selections:
            selections_data.append({
                "id": selection.id,
                "text": selection.selection_text,
                "note": selection.note,
                "conversation_id": selection.conversation_id,
                "created_at": selection.created_at,
                "created_at_formatted": datetime.fromtimestamp(selection.created_at).strftime('%Y-%m-%d %H:%M')
            })

        return {
            "selections": selections_data,
            "total_count": len(selections_data)
        }

    def render_html(self, data: Dict[str, Any]) -> str:
        """Render saved messages as HTML"""
        html = f"""
        <div class="report-component saved-messages">
            <div class="component-header">
                <span class="component-icon">💾</span>
                <h3 class="component-title">Saved Messages ({data['total_count']})</h3>
            </div>
            <div class="messages-content">
        """

        if data['selections']:
            for selection in data['selections']:
                html += f"""
                <div class="saved-message">
                    <p class="message-text">"{selection['text']}"</p>
                    {f'<p class="message-note">Note: {selection["note"]}</p>' if selection.get('note') else ''}
                    <p class="message-date">{selection['created_at_formatted']}</p>
                </div>
                """
        else:
            html += "<p class='no-data'>No saved messages</p>"

        html += """
            </div>
        </div>
        """
        return html

    def render_pdf(self, data: Dict[str, Any]) -> str:
        """Render for PDF"""
        return self.render_html(data)


class DescriptiveStatsComponent(ReportComponent):
    """Descriptive statistics component"""

    def generate(self) -> Dict[str, Any]:
        """Generate descriptive statistics"""
        if not self.messages:
            return self._empty_stats()

        user_messages = [m for m in self.messages if m.role == 'user']
        assistant_messages = [m for m in self.messages if m.role == 'assistant']

        # Word counts
        user_words = [len(m.content.split()) for m in user_messages]
        assistant_words = [len(m.content.split()) for m in assistant_messages]

        # Time analysis
        if self.messages:
            first_message = min(self.messages, key=lambda m: m.timestamp)
            last_message = max(self.messages, key=lambda m: m.timestamp)
            duration_hours = (last_message.timestamp - first_message.timestamp) / 3600
        else:
            duration_hours = 0

        # Messages by day
        messages_by_day = {}
        for msg in self.messages:
            day = datetime.fromtimestamp(msg.timestamp).strftime('%Y-%m-%d')
            if day not in messages_by_day:
                messages_by_day[day] = {"user": 0, "assistant": 0}
            messages_by_day[day][msg.role] += 1

        return {
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_messages": len(self.messages),
            "avg_words_per_user_message": sum(user_words) / len(user_words) if user_words else 0,
            "avg_words_per_assistant_message": sum(assistant_words) / len(assistant_words) if assistant_words else 0,
            "total_words": sum(user_words) + sum(assistant_words),
            "session_duration_hours": round(duration_hours, 2),
            "messages_by_day": messages_by_day,
            "longest_user_message": max(user_words) if user_words else 0,
            "shortest_user_message": min(user_words) if user_words else 0,
            "conversations_count": len(self.conversations),
            "average_messages_per_chat": len(self.messages) / len(self.conversations) if self.conversations else 0
        }

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            "user_messages": 0,
            "assistant_messages": 0,
            "total_messages": 0,
            "avg_words_per_user_message": 0,
            "avg_words_per_assistant_message": 0,
            "total_words": 0,
            "session_duration_hours": 0,
            "messages_by_day": {},
            "longest_user_message": 0,
            "shortest_user_message": 0,
            "conversations_count": 0,
            "average_messages_per_chat": 0
        }

    def render_html(self, data: Dict[str, Any]) -> str:
        """Render statistics as HTML"""
        html = f"""
        <div class="report-component descriptive-stats">
            <div class="component-header">
                <span class="component-icon">📊</span>
                <h3 class="component-title">Conversation Statistics</h3>
            </div>
            <div class="stats-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-value">{data['total_messages']}</span>
                        <span class="stat-label">Total Messages</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">{data['user_messages']}</span>
                        <span class="stat-label">User Messages</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">{data['assistant_messages']}</span>
                        <span class="stat-label">AI Responses</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">{data['session_duration_hours']}h</span>
                        <span class="stat-label">Session Duration</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">{round(data['avg_words_per_user_message'])}</span>
                        <span class="stat-label">Avg Words/User Msg</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">{data['total_words']:,}</span>
                        <span class="stat-label">Total Words</span>
                    </div>
                </div>
            </div>
        </div>
        """
        return html

    def render_pdf(self, data: Dict[str, Any]) -> str:
        """Render for PDF"""
        return self.render_html(data)


class NLPAnalysisComponent(ReportComponent):
    """NLP analysis component for sentiment and linguistic features"""

    def __init__(self, window_id: int, config: Dict[str, Any] = None):
        super().__init__(window_id, config)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            self.nlp = None

    def generate(self) -> Dict[str, Any]:
        """Generate NLP analysis"""
        user_messages = [m for m in self.messages if m.role == 'user']

        if not user_messages:
            return self._empty_analysis()

        # Sentiment analysis
        sentiments = []
        for msg in user_messages:
            blob = TextBlob(msg.content)
            sentiments.append(blob.sentiment.polarity)

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        positive_msgs = sum(1 for s in sentiments if s > 0.1)
        negative_msgs = sum(1 for s in sentiments if s < -0.1)
        neutral_msgs = len(sentiments) - positive_msgs - negative_msgs

        # Voice analysis (active vs passive)
        active_count = 0
        passive_count = 0

        if self.nlp:
            for msg in user_messages:
                doc = self.nlp(msg.content)
                for token in doc:
                    if token.dep_ == "auxpass":
                        passive_count += 1
                    elif token.pos_ == "VERB":
                        active_count += 1

        total_voice = active_count + passive_count
        active_ratio = (active_count / total_voice * 100) if total_voice > 0 else 0
        passive_ratio = (passive_count / total_voice * 100) if total_voice > 0 else 0

        # Question frequency
        question_count = sum(1 for msg in user_messages if '?' in msg.content)
        question_ratio = (question_count / len(user_messages) * 100) if user_messages else 0

        # Emotional keywords (simple detection)
        emotional_keywords = {
            'positive': ['happy', 'great', 'good', 'wonderful', 'excited', 'love', 'thank'],
            'negative': ['sad', 'angry', 'frustrated', 'worried', 'anxious', 'hate', 'bad'],
            'uncertainty': ['maybe', 'perhaps', 'might', 'could', 'possibly', 'unsure', "don't know"]
        }

        keyword_counts = {category: 0 for category in emotional_keywords}
        for msg in user_messages:
            msg_lower = msg.content.lower()
            for category, keywords in emotional_keywords.items():
                keyword_counts[category] += sum(1 for keyword in keywords if keyword in msg_lower)

        return {
            "average_sentiment": avg_sentiment,
            "sentiment_distribution": {
                "positive": positive_msgs,
                "neutral": neutral_msgs,
                "negative": negative_msgs
            },
            "sentiment_percentages": {
                "positive": (positive_msgs / len(sentiments) * 100) if sentiments else 0,
                "neutral": (neutral_msgs / len(sentiments) * 100) if sentiments else 0,
                "negative": (negative_msgs / len(sentiments) * 100) if sentiments else 0
            },
            "voice_analysis": {
                "active_ratio": active_ratio,
                "passive_ratio": passive_ratio,
                "total_verbs": total_voice
            },
            "question_frequency": question_ratio,
            "emotional_keywords": keyword_counts,
            "message_count": len(user_messages)
        }

    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            "average_sentiment": 0,
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "sentiment_percentages": {"positive": 0, "neutral": 0, "negative": 0},
            "voice_analysis": {"active_ratio": 0, "passive_ratio": 0, "total_verbs": 0},
            "question_frequency": 0,
            "emotional_keywords": {"positive": 0, "negative": 0, "uncertainty": 0},
            "message_count": 0
        }

    def render_html(self, data: Dict[str, Any]) -> str:
        """Render NLP analysis as HTML"""
        html = f"""
        <div class="report-component nlp-analysis">
            <div class="component-header">
                <span class="component-icon">🧠</span>
                <h3 class="component-title">Language Analysis</h3>
            </div>
            <div class="nlp-content">
                <div class="nlp-grid">
                    <div class="nlp-card">
                        <h4 class="nlp-title">Sentiment Analysis</h4>
                        <div class="sentiment-score">
                            Overall: {data['average_sentiment']:.2f}
                            ({self._get_sentiment_label(data['average_sentiment'])})
                        </div>
                        <div class="progress-bars">
                            <div class="progress-item">
                                <span>Positive ({data['sentiment_percentages']['positive']:.0f}%)</span>
                                <div class="progress-bar">
                                    <div class="progress-fill progress-positive" style="width: {data['sentiment_percentages']['positive']:.0f}%"></div>
                                </div>
                            </div>
                            <div class="progress-item">
                                <span>Neutral ({data['sentiment_percentages']['neutral']:.0f}%)</span>
                                <div class="progress-bar">
                                    <div class="progress-fill progress-neutral" style="width: {data['sentiment_percentages']['neutral']:.0f}%"></div>
                                </div>
                            </div>
                            <div class="progress-item">
                                <span>Negative ({data['sentiment_percentages']['negative']:.0f}%)</span>
                                <div class="progress-bar">
                                    <div class="progress-fill progress-negative" style="width: {data['sentiment_percentages']['negative']:.0f}%"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="nlp-card">
                        <h4 class="nlp-title">Voice Analysis</h4>
                        <div class="progress-bars">
                            <div class="progress-item">
                                <span>Active Voice ({data['voice_analysis']['active_ratio']:.0f}%)</span>
                                <div class="progress-bar">
                                    <div class="progress-fill progress-active" style="width: {data['voice_analysis']['active_ratio']:.0f}%"></div>
                                </div>
                            </div>
                            <div class="progress-item">
                                <span>Passive Voice ({data['voice_analysis']['passive_ratio']:.0f}%)</span>
                                <div class="progress-bar">
                                    <div class="progress-fill progress-passive" style="width: {data['voice_analysis']['passive_ratio']:.0f}%"></div>
                                </div>
                            </div>
                        </div>
                        <p class="nlp-note">Questions: {data['question_frequency']:.0f}% of messages</p>
                    </div>
                </div>
            </div>
        </div>
        """
        return html

    def _get_sentiment_label(self, score: float) -> str:
        """Get sentiment label from score"""
        if score > 0.3:
            return "Positive"
        elif score < -0.3:
            return "Negative"
        else:
            return "Neutral"

    def render_pdf(self, data: Dict[str, Any]) -> str:
        """Render for PDF"""
        return self.render_html(data)


class UnifiedReportGenerator:
    """Main unified report generator that orchestrates all components"""

    # Available components registry
    COMPONENTS = {
        'ai_summary': AISummaryComponent,
        'saved_messages': SavedMessagesComponent,
        'descriptive_stats': DescriptiveStatsComponent,
        'nlp_analysis': NLPAnalysisComponent
    }

    def __init__(self, window_id: int):
        self.window_id = window_id
        self.window = ChatWindow.query.get(window_id)
        if not self.window:
            raise ValueError(f"ChatWindow with id {window_id} not found")

        self.config = self.window.get_report_config()
        self.components_data = {}

    def generate(self) -> Dict[str, Any]:
        """Generate all configured report components"""
        report_data = {
            'window_id': self.window_id,
            'window_title': self.window.title,
            'window_description': self.window.description,
            'patient_id': self.window.patient_id,
            'provider_id': self.window.provider_id,
            'start_date': self.window.start_date,
            'end_date': self.window.end_date,
            'generated_at': time.time(),
            'components': {}
        }

        # Generate each configured component
        for component_name, component_class in self.COMPONENTS.items():
            if self.config.get(component_name, False):
                try:
                    component = component_class(self.window_id, self.config)
                    component_data = component.generate()
                    report_data['components'][component_name] = component_data
                    self.components_data[component_name] = (component, component_data)
                except Exception as e:
                    print(f"Error generating {component_name}: {e}")
                    report_data['components'][component_name] = {'error': str(e)}

        # Add summary statistics for backward compatibility
        if 'descriptive_stats' in report_data['components']:
            stats = report_data['components']['descriptive_stats']
            report_data['summary'] = {
                'total_conversations': stats.get('conversations_count', 0),
                'total_user_messages': stats.get('user_messages', 0),
                'total_model_messages': stats.get('assistant_messages', 0),
                'average_messages_per_chat': stats.get('average_messages_per_chat', 0)
            }
        else:
            # Provide default summary if stats not generated
            report_data['summary'] = {
                'total_conversations': 0,
                'total_user_messages': 0,
                'total_model_messages': 0,
                'average_messages_per_chat': 0
            }

        return report_data

    def render_html(self, report_data: Dict[str, Any] = None, standalone: bool = False) -> str:
        """Render report as HTML"""
        if not report_data:
            report_data = self.generate()

        css = self._get_css(standalone)
        html_parts = []

        # Add wrapper div
        html_parts.append('<div class="unified-report">')

        # Add header
        html_parts.append(self._render_header(report_data))

        # Add components
        html_parts.append('<div class="report-content">')

        # If we have stored report data, render components from that data
        if 'components' in report_data:
            for component_name, component_data in report_data['components'].items():
                if component_name in self.COMPONENTS:
                    component_class = self.COMPONENTS[component_name]
                    component = component_class(self.window_id, self.config)
                    html_parts.append(f'<div class="report-section" data-component="{component_name}">')
                    html_parts.append(component.render_html(component_data))
                    html_parts.append('</div>')
        else:
            # Fallback to self.components_data for freshly generated reports
            for component_name, (component, data) in self.components_data.items():
                html_parts.append(f'<div class="report-section" data-component="{component_name}">')
                html_parts.append(component.render_html(data))
                html_parts.append('</div>')

        html_parts.append('</div>')

        html_parts.append('</div>')

        if standalone:
            # For PDF or download, include full HTML document
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Report - {report_data.get('window_title', 'Chat Session')}</title>
                <style>{css}</style>
            </head>
            <body>
                {''.join(html_parts)}
            </body>
            </html>
            """
        else:
            # For modal display, just return the styled content
            return f"<style>{css}</style>{''.join(html_parts)}"

    def render_pdf(self, report_data: Dict[str, Any] = None) -> str:
        """Render report optimized for PDF generation"""
        if not report_data:
            report_data = self.generate()

        css = self._get_pdf_css()
        html_parts = []

        # Similar to HTML but with print-optimized styling
        html_parts.append('<div class="unified-report print-mode">')
        html_parts.append(self._render_header(report_data, for_print=True))

        html_parts.append('<div class="report-content">')
        for component_name, (component, data) in self.components_data.items():
            html_parts.append(f'<div class="report-section print-section" data-component="{component_name}">')
            html_parts.append(component.render_pdf(data))
            html_parts.append('</div>')
        html_parts.append('</div>')

        html_parts.append('</div>')

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Report - {report_data.get('window_title', 'Chat Session')}</title>
            <style>{css}</style>
        </head>
        <body>
            {''.join(html_parts)}
        </body>
        </html>
        """

    def _get_models_used(self) -> Dict[str, Dict[str, Any]]:
        """Get information about models used in conversations"""
        models_used = {}
        conversations = Conversation.query.filter_by(window_id=self.window_id).all()

        for conv in conversations:
            if conv.model:
                model_name = conv.model.name
                model_provider = conv.model.provider if conv.model.provider else "Unknown"

                if model_name not in models_used:
                    models_used[model_name] = {
                        "provider": model_provider,
                        "conversation_count": 0
                    }

                models_used[model_name]["conversation_count"] += 1

        return models_used

    def _render_header(self, report_data: Dict[str, Any], for_print: bool = False) -> str:
        """Render report header"""
        generated_date = datetime.fromtimestamp(report_data.get('generated_at', 0)).strftime('%B %d, %Y')

        # Get summary stats
        summary = report_data.get('summary', {})

        # Get models used from conversations
        models_used = self._get_models_used()

        header_class = "report-header print-header" if for_print else "report-header"

        # Build models display
        models_html = ""
        if models_used:
            model_list = ", ".join([f"{name} ({info['provider']})" for name, info in models_used.items()])
            models_html = f"""
                <div class="meta-item meta-item-full">
                    <div class="meta-label">Models Used</div>
                    <div class="meta-value meta-value-models">{model_list}</div>
                </div>
            """

        return f"""
        <div class="{header_class}">
            <h2>{report_data.get('window_title', 'Chat Session Report')}</h2>
            {f'<p class="window-description">{report_data.get("window_description")}</p>' if report_data.get('window_description') else ''}
            <div class="report-meta">
                <div class="meta-item">
                    <div class="meta-label">Generated</div>
                    <div class="meta-value">{generated_date}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Conversations</div>
                    <div class="meta-value">{summary.get('total_conversations', 0)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Total Messages</div>
                    <div class="meta-value">{summary.get('total_user_messages', 0) + summary.get('total_model_messages', 0)}</div>
                </div>
                {models_html}
            </div>
        </div>
        """

    def _get_css(self, standalone: bool = False) -> str:
        """Get CSS for HTML rendering"""
        # Scope all CSS within .unified-report to prevent conflicts
        return """
        .unified-report {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .unified-report .report-header {
            background: linear-gradient(135deg, #0066cc 0%, #4a90e2 100%);
            color: #ffffff;
            padding: 2rem;
            text-align: center;
        }

        .unified-report .report-header h2 {
            margin: 0 0 1rem 0;
            font-size: 2rem;
            font-weight: 300;
            color: #ffffff;
        }

        .unified-report .window-description {
            color: rgba(255,255,255,0.9);
            margin-bottom: 1.5rem;
        }

        .unified-report .report-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .unified-report .meta-item {
            background: rgba(255,255,255,0.1);
            padding: 0.75rem;
            border-radius: 8px;
            text-align: center;
        }

        .unified-report .meta-item-full {
            grid-column: 1 / -1;
        }

        .unified-report .meta-value-models {
            font-size: 0.95rem;
            word-wrap: break-word;
        }

        .unified-report .meta-label {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.9);
            margin-bottom: 0.25rem;
        }

        .unified-report .meta-value {
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
        }

        .unified-report .report-content {
            padding: 0;
        }

        .unified-report .report-section {
            border-bottom: 1px solid #f0f0f0;
            padding: 2rem;
        }

        .unified-report .report-section:last-child {
            border-bottom: none;
        }

        .unified-report .component-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid #e6f3ff;
        }

        .unified-report .component-icon {
            font-size: 1.5rem;
            margin-right: 0.75rem;
        }

        .unified-report .component-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #003d7a;
            margin: 0;
        }

        .unified-report .summary-content {
            background: #f0f8ff;
            border-radius: 12px;
            padding: 1.5rem;
            border-left: 4px solid #0066cc;
        }

        .unified-report .summary-text {
            font-size: 1.05rem;
            line-height: 1.6;
            color: #1a1a1a;
            margin-bottom: 1rem;
        }

        .unified-report .themes-list {
            list-style: none;
            padding: 0;
            margin: 1rem 0;
        }

        .unified-report .themes-list li {
            background: #e6f3ff;
            margin: 0.5rem 0;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border-left: 3px solid #0066cc;
            color: #1a1a1a;
        }

        .unified-report .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }

        .unified-report .stat-card {
            background: linear-gradient(135deg, #0066cc 0%, #4a90e2 100%);
            color: #ffffff;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
        }

        .unified-report .stat-value {
            display: block;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #ffffff;
        }

        .unified-report .stat-label {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.95);
        }

        .unified-report .nlp-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }

        .unified-report .nlp-card {
            background: #ffffff;
            border: 2px solid #e6f3ff;
            border-radius: 12px;
            padding: 1.5rem;
        }

        .unified-report .nlp-title {
            font-weight: 600;
            color: #003d7a;
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }

        .unified-report .progress-bar {
            background: #e6f3ff;
            border-radius: 10px;
            height: 12px;
            margin: 0.5rem 0;
            overflow: hidden;
        }

        .unified-report .progress-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }

        .unified-report .progress-positive { background: linear-gradient(90deg, #00a86b, #4fd1c7); }
        .unified-report .progress-neutral { background: linear-gradient(90deg, #808080, #b0b0b0); }
        .unified-report .progress-negative { background: linear-gradient(90deg, #ff6b6b, #ffa8a8); }
        .unified-report .progress-active { background: linear-gradient(90deg, #0066cc, #66b3ff); }
        .unified-report .progress-passive { background: linear-gradient(90deg, #9370db, #b19cd9); }

        .unified-report .saved-message {
            background: #f0f8ff;
            border-left: 4px solid #0066cc;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }

        .unified-report .message-text {
            font-style: italic;
            color: #003d7a;
            margin-bottom: 0.5rem;
            font-size: 1.05rem;
        }

        .unified-report .message-note {
            color: #0066cc;
            font-size: 0.9rem;
            margin-bottom: 0.25rem;
        }

        .unified-report .message-date {
            color: #999;
            font-size: 0.85rem;
            margin: 0;
        }

        .unified-report .generated-by {
            text-align: right;
            font-size: 0.85rem;
            color: #666;
            margin-top: 1rem;
            font-style: italic;
        }

        .unified-report .no-data {
            color: #666;
            font-style: italic;
            text-align: center;
            padding: 2rem;
        }

        .unified-report .progress-item {
            margin-bottom: 1rem;
        }

        .unified-report .progress-item span {
            display: block;
            margin-bottom: 0.25rem;
            font-size: 0.9rem;
            color: #333;
        }

        .unified-report .nlp-note {
            margin-top: 1rem;
            font-size: 0.9rem;
            color: #666;
        }

        .unified-report .sentiment-score {
            font-size: 1.2rem;
            font-weight: 600;
            color: #003d7a;
            margin-bottom: 1rem;
        }
        """

    def _get_pdf_css(self) -> str:
        """Get CSS optimized for PDF printing"""
        base_css = self._get_css()
        pdf_additions = """
        @page {
            size: A4;
            margin: 1cm;
        }

        .unified-report.print-mode {
            box-shadow: none;
            border-radius: 0;
        }

        .unified-report .report-section {
            page-break-inside: avoid;
        }

        .unified-report .report-header.print-header {
            page-break-after: avoid;
        }

        .unified-report .stats-grid,
        .unified-report .nlp-grid {
            grid-template-columns: repeat(2, 1fr);
        }

        @media print {
            .unified-report {
                max-width: 100%;
            }
        }
        """
        return base_css + pdf_additions

    @classmethod
    def save_report(cls, window_id: int) -> Report:
        """Generate and save report to database"""
        generator = cls(window_id)
        report_data = generator.generate()

        # Save to database
        report = Report(
            window_id=window_id,
            patient_id=report_data['patient_id'],
            provider_id=report_data['provider_id'],
            report_type='unified',
            report_data=json.dumps(report_data),
            generated_at=report_data['generated_at']
        )

        db.session.add(report)
        db.session.commit()

        return report

    @classmethod
    def export_html(cls, window_id: int, filename: str = None) -> str:
        """Export report as standalone HTML file"""
        generator = cls(window_id)
        report_data = generator.generate()
        html_content = generator.render_html(report_data, standalone=True)

        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return filename

        return html_content

    @classmethod
    def export_pdf(cls, window_id: int, filename: str = None) -> bytes:
        """Export report as PDF using weasyprint"""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("weasyprint is required for PDF generation. Install with: pip install weasyprint")

        generator = cls(window_id)
        report_data = generator.generate()
        html_content = generator.render_pdf(report_data)

        # Generate PDF using weasyprint
        html_doc = weasyprint.HTML(string=html_content)

        if filename:
            # Save to specified file
            html_doc.write_pdf(filename)
            with open(filename, 'rb') as f:
                return f.read()
        else:
            # Return PDF bytes
            return html_doc.write_pdf()
