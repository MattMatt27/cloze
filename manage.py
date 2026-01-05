import json
import os
import time
from flask import Flask
from llm_chat import create_app
from llm_chat.extensions import db
from llm_chat.models import (
    User, ProviderPatient, ProviderSettings, SystemPrompt,
    Model, Conversation, ChatWindow, ChatTemplate
)
from llm_chat.services.llm_interface import LLMInterface

app: Flask = create_app()

def initialize_database():
    """Initialize database with default data (idempotent)."""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created/verified")

        # Initialize LLM clients
        LLMInterface.initialize_clients()

        # Create default admin (only if doesn't exist)
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("Created default admin user")

        # Demo provider (only if doesn't exist)
        if not User.query.filter_by(username='provider1').first():
            provider = User(username='provider1', email='provider1@example.com', role='provider')
            provider.set_password('provider123')
            db.session.add(provider)
            print("Created demo provider")

        # Demo users (patients) - only create if they don't exist
        demo_users = ['user1', 'user2', 'user3']
        for username in demo_users:
            if not User.query.filter_by(username=username).first():
                u = User(username=username, email=f'{username}@example.com', role='user')
                u.set_password('user123')
                db.session.add(u)
                print(f"Created demo user: {username}")

        # Assign provider to demo users (only if assignments don't exist)
        provider = User.query.filter_by(username='provider1').first()
        admin = User.query.filter_by(role='admin').first()
        if provider and admin:
            for username in demo_users:
                patient = User.query.filter_by(username=username).first()
                if patient and not ProviderPatient.query.filter_by(provider_id=provider.id, patient_id=patient.id).first():
                    db.session.add(ProviderPatient(
                        provider_id=provider.id,
                        patient_id=patient.id,
                        assigned_by=admin.id
                    ))
                    print(f"Created provider assignment for {username}")

        # Default models (only if none exist)
        if not Model.query.first():
            models = [
                Model(name='GPT-4o', provider='openai', model_identifier='gpt-4o',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
                Model(name='GPT-4o Mini', provider='openai', model_identifier='gpt-4o-mini',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
                Model(name='Claude Opus 4.5', provider='anthropic', model_identifier='claude-opus-4-5-20251101',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
                Model(name='Claude Sonnet 4.5', provider='anthropic', model_identifier='claude-sonnet-4-5-20250514',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
                Model(name='Gemini 2.0 Flash', provider='google', model_identifier='gemini-2.0-flash',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
                Model(name='Llama 3.2 1B (Fast)', provider='local',
                      api_endpoint=f"{os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}/v1/chat/completions",
                      model_identifier='llama3.2:1b',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 2000})),
                Model(name='Llama 3.2 3B (Balanced)', provider='local',
                      api_endpoint=f"{os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}/v1/chat/completions",
                      model_identifier='llama3.2:3b',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 2000})),
                Model(name='Llama 3.1 8B (Quality)', provider='local',
                      api_endpoint=f"{os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}/v1/chat/completions",
                      model_identifier='llama3.1:8b',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 2000})),
            ]
            for m in models:
                db.session.add(m)
            print("Created default models")

        # Default system prompts (only if none exist)
        if not SystemPrompt.query.first():
            prompts = [
                SystemPrompt(name='Default Assistant', content='You are a helpful AI assistant. Respond in appropriate chat format.'),
                SystemPrompt(name='Mental Health Support', content='You are a supportive mental health companion. Provide empathetic responses and coping strategies. Always remind users to seek professional help for serious concerns.'),
                SystemPrompt(name='Anxiety Management', content='You are specialized in anxiety management. Help users identify triggers, practice breathing techniques, and develop coping strategies. Be calm and reassuring.'),
                SystemPrompt(name='Work & Career Support', content='You help with work-related stress, career decisions, and professional development. Be practical and encouraging.'),
                SystemPrompt(name='General Therapy Support', content='You provide general therapeutic support. Listen actively, ask clarifying questions, and help users process their thoughts and feelings.')
            ]
            for p in prompts:
                db.session.add(p)
            print("Created default system prompts")

        # Commit all changes at once
        try:
            db.session.commit()
            print("Database initialization complete.")
        except Exception as e:
            db.session.rollback()
            print(f"Database initialization completed with some existing data: {e}")

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True, host="0.0.0.0", port=5051)