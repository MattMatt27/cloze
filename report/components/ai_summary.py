"""
AI Summary Component

Generates AI-powered summaries of conversations using Llama models.
Extracts key themes and clinical progress notes from chat transcripts.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from report.base import ReportComponent
from llm_chat.models import Model
from llm_chat.services.llm_interface import LLMInterface


class AISummaryComponent(ReportComponent):
    """AI-powered conversation summary component using Llama models."""

    def generate(self) -> Optional[Dict[str, Any]]:
        """
        Generate AI summary using the smallest available Llama model.

        Returns:
            Dict containing:
                - summary: 2-3 paragraph overview
                - themes: List of key themes identified
                - progress_notes: Clinical notes
                - generated_with: Model name used
                - error: Error message if generation failed
            Or None if no Llama models are available.
        """
        if not self.messages:
            return {
                "summary": "No messages to summarize.",
                "themes": [],
                "progress_notes": "",
                "generated_with": "No model"
            }

        try:
            model = self._select_llama_model()
            if model is None:
                # No Llama models available, skip AI summary
                return None

            conversation_text = self._prepare_conversation_text()
            prompt = self._build_prompt(conversation_text)

            # Use LLMInterface to call the model with extended timeout for reports
            messages = [{"role": "user", "content": prompt}]
            config_override = {"timeout": 180}  # 3 minutes for report generation
            response_text, _ = LLMInterface.call_llm(model, messages, config_override=config_override)

            return self._parse_ai_response(response_text, model.name)

        except Exception as e:
            error_msg = str(e)

            # Provide user-friendly error messages
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                summary_text = "The AI model took too long to generate a summary (timeout after 3 minutes). This can happen with longer conversations or slower models. The conversation data is still available in other sections of this report."
            elif "connection" in error_msg.lower():
                summary_text = "Unable to connect to the AI model service. Please ensure the model service is running."
            else:
                summary_text = f"Error generating AI summary: {error_msg}"

            return {
                "summary": summary_text,
                "themes": [],
                "progress_notes": "",
                "error": error_msg,
                "generated_with": model.name if 'model' in locals() else "Unknown"
            }

    def _select_llama_model(self) -> Optional[Model]:
        """
        Select the smallest available Llama model.

        Returns:
            Model object if a Llama model is available, None otherwise.
        """
        # Query for available Llama models from local provider
        available_models = Model.query.filter(
            Model.provider == 'local',
            Model.name.ilike('%llama%'),
            Model.is_active == True
        ).all()

        if not available_models:
            print("No Llama models available for AI summary generation")
            return None

        # Check actual availability
        available_models = [m for m in available_models if m.check_availability()]

        if not available_models:
            print("No Llama models currently available for AI summary generation")
            return None

        # Prioritize smaller models (ordered from smallest to largest)
        # Common patterns: llama3.2, llama3.1, llama2, llama3
        priority_patterns = [
            'llama3.2:1b',      # Smallest
            'llama3.2:3b',
            'llama3.2',
            'llama2:7b',
            'llama3.1:8b',
            'llama3:8b',
            'llama2',
            'llama3.1',
            'llama3',
        ]

        # Try to find models matching priority patterns
        for pattern in priority_patterns:
            for model in available_models:
                if pattern.lower() in model.name.lower():
                    print(f"Selected Llama model for AI summary: {model.name}")
                    return model

        # Fallback to first available Llama model
        print(f"Selected Llama model for AI summary: {available_models[0].name}")
        return available_models[0]

    def _prepare_conversation_text(self) -> str:
        """Prepare conversation text for AI analysis."""
        text_parts = []
        for conv in self.conversations:
            conv_messages = [m for m in self.messages if m.conversation_id == conv.id]
            if conv_messages:
                text_parts.append(f"\n--- Conversation: {conv.title} ---")
                for msg in sorted(conv_messages, key=lambda x: x.timestamp):
                    timestamp = datetime.fromtimestamp(msg.timestamp).strftime('%Y-%m-%d %H:%M')
                    text_parts.append(f"[{timestamp}] {msg.role}: {msg.content}")
        return "\n".join(text_parts)

    def _build_prompt(self, conversation_text: str) -> str:
        """Build the prompt for AI summary generation."""
        return f"""
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

    def _parse_ai_response(self, response_text: str, model_name: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        import re

        summary = ""
        themes = []
        progress_notes = ""

        # Remove markdown bold markers (**text**)
        response_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', response_text)

        current_section = None
        summary_lines = []
        progress_lines = []

        for line in response_text.split('\n'):
            line_upper = line.upper()
            stripped = line.strip()

            # Check for section headers
            if 'SUMMARY:' in line_upper or 'SUMMARY' == stripped.upper() or stripped.upper().startswith('SUMMARY'):
                current_section = 'summary'
                continue
            elif 'THEMES:' in line_upper or 'THEMES' == stripped.upper() or 'KEY THEMES' in line_upper or stripped.upper().startswith('THEMES'):
                current_section = 'themes'
                continue
            elif 'PROGRESS NOTES:' in line_upper or 'PROGRESS NOTES' == stripped.upper() or 'PROGRESS' in line_upper:
                current_section = 'progress'
                continue

            # Collect content for each section
            if current_section == 'summary' and stripped:
                summary_lines.append(stripped)
            elif current_section == 'themes' and stripped:
                # Handle both bulleted and non-bulleted themes
                cleaned = stripped
                if cleaned.startswith('-') or cleaned.startswith('*') or cleaned.startswith('•'):
                    cleaned = cleaned[1:].strip()
                if cleaned and len(cleaned) > 2:  # Skip very short lines
                    themes.append(cleaned)
            elif current_section == 'progress' and stripped:
                progress_lines.append(stripped)

        # Join summary lines with paragraph breaks (double line breaks create new paragraphs)
        if summary_lines:
            summary = ' '.join(summary_lines)

        # Join progress notes and clean up bullet markers
        if progress_lines:
            # Remove leading asterisks/bullets that might be in the text
            cleaned_progress = []
            for line in progress_lines:
                # Remove bullet markers at start of lines
                cleaned = re.sub(r'^[\*\-\•]\s*', '', line)
                cleaned_progress.append(cleaned)
            progress_notes = ' '.join(cleaned_progress)

        # Fallback: if parsing failed, use the whole response as summary with basic formatting
        if not summary.strip() and not themes and not progress_notes.strip():
            # Try to break up the text into paragraphs
            summary = response_text.strip()

        return {
            "summary": summary.strip() if summary.strip() else "AI generated summary is not available in expected format.",
            "themes": themes,
            "progress_notes": progress_notes.strip(),
            "generated_with": model_name
        }
