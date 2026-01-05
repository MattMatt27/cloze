import os
import time
import json
import requests
from typing import List, Dict, Optional, Tuple

# Ollama host configuration (default: localhost for local development)
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')

# Provider clients (optional imports)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class LLMInterface:
    """Unified interface for different LLM providers"""
    _provider_clients: Dict[str, object] = {}

    @classmethod
    def initialize_clients(cls):
        """Initialize provider clients based on available API keys"""
        # OpenAI
        openai_key = os.environ.get('OPENAI_API_KEY')
        if OpenAI and openai_key and openai_key.strip() and openai_key != 'your_openai_key_here':
            try:
                cls._provider_clients['openai'] = OpenAI(api_key=openai_key)
                print("✓ OpenAI client initialized successfully")
            except Exception as e:
                print(f"✗ Could not initialize OpenAI client: {e}")
        else:
            reasons = []
            if not OpenAI:
                reasons.append("OpenAI library not installed")
            if not openai_key:
                reasons.append("No API key found")
            elif not openai_key.strip():
                reasons.append("API key is empty")
            elif openai_key == 'your_openai_key_here':
                reasons.append("Using placeholder value")
            print(f"✗ OpenAI API key not configured or invalid: {', '.join(reasons)}")

        # Anthropic
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if Anthropic and anthropic_key and anthropic_key.strip() and anthropic_key != 'your_anthropic_key_here':
            try:
                cls._provider_clients['anthropic'] = Anthropic(api_key=anthropic_key)
                print("✓ Anthropic client initialized successfully")
            except Exception as e:
                print(f"✗ Could not initialize Anthropic client: {e}")
        else:
            reasons = []
            if not Anthropic:
                reasons.append("Anthropic library not installed")
            if not anthropic_key:
                reasons.append("No API key found")
            elif not anthropic_key.strip():
                reasons.append("API key is empty")
            elif anthropic_key == 'your_anthropic_key_here':
                reasons.append("Using placeholder value")
            print(f"✗ Anthropic API key not configured or invalid: {', '.join(reasons)}")

        # Google
        google_key = os.environ.get('GOOGLE_API_KEY')
        if genai and google_key and google_key.strip() and google_key != 'your_google_api_key_here':
            try:
                genai.configure(api_key=google_key)
                cls._provider_clients['google'] = genai
                print("✓ Google client initialized successfully")
            except Exception as e:
                print(f"✗ Could not initialize Google client: {e}")
        else:
            print("✗ Google API key not configured or invalid")

        # Local Ollama
        try:
            ollama_url = f"{OLLAMA_HOST}/api/tags"
            response = requests.get(ollama_url, timeout=2)
            if response.status_code == 200:
                cls._provider_clients['local'] = True
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                print(f"✓ Ollama server detected at {OLLAMA_HOST} with models: {model_names}")
            else:
                print(f"✗ Ollama server at {OLLAMA_HOST} responded but with an error")
        except requests.exceptions.RequestException:
            print(f"✗ Ollama server not available at {OLLAMA_HOST}")

        print("\n=== LLM Client Status ===")
        print(f"Initialized providers: {list(cls._provider_clients.keys())}")
        for provider in ['openai', 'anthropic', 'google', 'local']:
            status = "✓ AVAILABLE" if provider in cls._provider_clients else "✗ NOT AVAILABLE"
            print(f"{provider}: {status}")
        print("========================\n")

    @classmethod
    def call_llm(cls, model, messages: List[Dict], system_prompt: Optional[str] = None, config_override: Optional[Dict] = None) -> Tuple[str, float]:
        """Call LLM with messages and return (response_text, response_time_sec)

        Args:
            model: Model object to use
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            config_override: Optional config overrides (e.g., {'timeout': 180})
        """
        start_time = time.time()

        # Format messages with system prompt
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({'role': 'system', 'content': system_prompt})
        formatted_messages.extend(messages)

        config = json.loads(model.config or '{}')
        # Apply config overrides if provided
        if config_override:
            config.update(config_override)

        try:
            if model.provider == 'openai':
                client = cls._provider_clients.get('openai')
                if not client:
                    raise RuntimeError("OpenAI client not available")

                response = client.chat.completions.create(
                    model=model.model_identifier,
                    messages=formatted_messages,
                    temperature=config.get('temperature', 0.7),
                    max_tokens=config.get('max_tokens', 1000),
                )
                result = response.choices[0].message.content

            elif model.provider == 'anthropic':
                client = cls._provider_clients.get('anthropic')
                if not client:
                    raise RuntimeError("Anthropic client not available")

                # Extract system message
                system_msg = None
                anthropic_messages = []
                for msg in formatted_messages:
                    if msg['role'] == 'system':
                        system_msg = msg['content']
                    else:
                        anthropic_messages.append(msg)

                # Build request kwargs
                request_kwargs = {
                    'model': model.model_identifier,
                    'max_tokens': config.get('max_tokens', 1000),
                    'temperature': config.get('temperature', 0.7),
                    'messages': anthropic_messages,
                }

                # Newer Claude models (4.5+) require system as a list of content blocks
                if system_msg:
                    request_kwargs['system'] = [{"type": "text", "text": system_msg}]

                response = client.messages.create(**request_kwargs)
                # anthropic SDK returns list of content blocks
                result = response.content[0].text

            elif model.provider == 'google':
                client = cls._provider_clients.get('google')
                if not client:
                    raise RuntimeError("Google client not available")

                # Extract system prompt
                system_instruction = None
                gemini_messages = []
                for msg in formatted_messages:
                    if msg['role'] == 'system':
                        system_instruction = msg['content']
                    else:
                        role = 'model' if msg['role'] == 'assistant' else 'user'
                        gemini_messages.append({'role': role, 'parts': [{'text': msg['content']}]})

                # Create model with system instruction if available
                if system_instruction:
                    model_obj = genai.GenerativeModel(
                        model_name=model.model_identifier,
                        system_instruction=system_instruction
                    )
                else:
                    model_obj = genai.GenerativeModel(model.model_identifier)

                response = model_obj.generate_content(
                    contents=gemini_messages,
                    generation_config={
                        'temperature': config.get('temperature', 0.7),
                        'max_output_tokens': config.get('max_tokens', 1000),
                    },
                )
                result = response.text

            elif model.provider == 'local':
                response = requests.post(
                    model.api_endpoint,
                    json={
                        'model': model.model_identifier,  # Required by Ollama
                        'messages': formatted_messages,
                        'temperature': config.get('temperature', 0.7),
                        'max_tokens': config.get('max_tokens', 1000),
                        'stream': False  # Disable streaming for simpler response handling
                    },
                    timeout=config.get('timeout', 250),  # Use custom timeout if provided (250s for CPU inference)
                )
                response.raise_for_status()
                result = response.json()['choices'][0]['message']['content']

            else:
                raise ValueError(f"Unknown provider: {model.provider}")

        except Exception as e:
            result = f"Error calling {model.provider}: {str(e)}"

        response_time = time.time() - start_time
        return result, response_time
