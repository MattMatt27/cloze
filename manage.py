import json
import os
import time
from flask import Flask
from llm_chat import create_app
from llm_chat.extensions import db
from llm_chat.models import (
    User, ProviderPatient, ProviderSettings, SystemPrompt,
    Model, Conversation, Message, ChatWindow, ChatTemplate, SafetyPlan
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
                Model(name='GPT-3.5 Turbo', provider='openai', model_identifier='gpt-3.5-turbo',
                      config=json.dumps({'temperature': 0.7, 'max_tokens': 1000})),
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

        # Default system prompts — seed from prompt registry
        from prompts.registry import PromptRegistry
        registry = PromptRegistry.instance()
        if not SystemPrompt.query.first():
            for domain in registry.list_domain_prompts():
                db.session.add(SystemPrompt(
                    name=domain.name,
                    content=domain.description,
                    domain_prompt_id=domain.id,
                ))
            print("Created domain-linked system prompts")
        else:
            # Back-fill domain_prompt_id on existing rows that lack it
            for domain in registry.list_domain_prompts():
                if not SystemPrompt.query.filter_by(domain_prompt_id=domain.id).first():
                    db.session.add(SystemPrompt(
                        name=domain.name,
                        content=domain.description,
                        domain_prompt_id=domain.id,
                    ))
                    print(f"Added domain prompt: {domain.name}")

        # Flush to ensure IDs are assigned for models, prompts, users
        db.session.flush()

        # Demo chat windows with conversations for user1
        provider = User.query.filter_by(username='provider1').first()
        patient1 = User.query.filter_by(username='user1').first()
        model1 = Model.query.first()
        prompt1 = SystemPrompt.query.first()

        if provider and patient1 and model1 and not ChatWindow.query.filter_by(patient_id=patient1.id).first():
            now = time.time()

            # Window 1: completed, 1 conversation (report_ready)
            w1 = ChatWindow(
                patient_id=patient1.id,
                provider_id=provider.id,
                title='Week 1 — Getting Started',
                description='Initial check-in conversation to establish rapport.',
                start_date=now - 14 * 86400,  # 2 weeks ago
                end_date=now - 7 * 86400,      # 1 week ago
                status='report_ready',
            )
            db.session.add(w1)
            db.session.flush()

            t1 = ChatTemplate(
                window_id=w1.id,
                title='Check-In',
                purpose='General check-in to see how things are going',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                order_index=0,
            )
            db.session.add(t1)
            db.session.flush()

            c1 = Conversation(
                user_id=patient1.id,
                title='Check-In',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                window_id=w1.id,
                template_id=t1.id,
                consent_provided=True,
                created_at=now - 13 * 86400,
                updated_at=now - 13 * 86400,
            )
            db.session.add(c1)
            db.session.flush()

            c1_messages = [
                ('user', "Hi, I'm not sure what to talk about. My provider suggested I try this.", now - 13 * 86400),
                ('assistant', "That's completely okay — there's no pressure to have a specific topic. A lot of people start here just to get a feel for what this is like. How has your week been so far?", now - 13 * 86400 + 30),
                ('user', "It's been okay I guess. Work has been stressful and I haven't been sleeping well.", now - 13 * 86400 + 120),
                ('assistant', "I'm sorry to hear that. Stress at work and poor sleep often go hand in hand — when one gets worse, the other tends to follow. What's been going on at work that's been weighing on you?", now - 13 * 86400 + 150),
                ('user', "There's a big deadline coming up and I feel like I can't keep up. I've been staying late but it doesn't seem to help.", now - 13 * 86400 + 300),
                ('assistant', "That sounds really frustrating — putting in the extra effort and still feeling behind. It makes sense that would affect your sleep too, with all that on your mind. Have you been able to do anything to unwind after those long days, even something small?", now - 13 * 86400 + 330),
                ('user', "Not really. I usually just scroll on my phone until I fall asleep. I know that's not great.", now - 13 * 86400 + 500),
                ('assistant', "No judgement at all — that's a really common way people wind down, especially when they're exhausted. It sounds like you're aware it might not be helping with the sleep though. Is sleep something you'd like to work on, or is the work stress feeling more pressing right now?", now - 13 * 86400 + 530),
            ]
            for role, content, ts in c1_messages:
                db.session.add(Message(conversation_id=c1.id, role=role, content=content, timestamp=ts))
            print("Created demo window 1 (completed, 1 conversation)")

            # Window 2: completed, 2 conversations (report_ready)
            w2 = ChatWindow(
                patient_id=patient1.id,
                provider_id=provider.id,
                title='Week 2 — Coping Strategies',
                description='Exploring coping mechanisms and building a toolkit.',
                start_date=now - 7 * 86400,   # 1 week ago
                end_date=now - 1 * 86400,      # yesterday
                status='report_ready',
            )
            db.session.add(w2)
            db.session.flush()

            t2a = ChatTemplate(
                window_id=w2.id,
                title='Stress Management',
                purpose='Discuss strategies for managing work stress',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                order_index=0,
            )
            t2b = ChatTemplate(
                window_id=w2.id,
                title='Sleep Hygiene',
                purpose='Work on improving sleep habits',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                order_index=1,
            )
            db.session.add(t2a)
            db.session.add(t2b)
            db.session.flush()

            # Conversation 2a: Stress management
            c2a = Conversation(
                user_id=patient1.id,
                title='Stress Management',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                window_id=w2.id,
                template_id=t2a.id,
                consent_provided=True,
                created_at=now - 6 * 86400,
                updated_at=now - 6 * 86400,
            )
            db.session.add(c2a)
            db.session.flush()

            c2a_messages = [
                ('user', "I wanted to talk about what's been going on at work. The deadline passed but now there's another one.", now - 6 * 86400),
                ('assistant', "It sounds like the cycle is continuing. How did you feel after the first deadline passed — was there any relief, or did the next one take over right away?", now - 6 * 86400 + 30),
                ('user', "There was maybe a day where I felt okay, then the next project started and it was right back to feeling overwhelmed.", now - 6 * 86400 + 180),
                ('assistant', "One day of relief before the pressure builds again — that's a tough pattern. It sounds like the stress isn't just about one deadline but more about the pace itself. Have you noticed anything that helps you feel even a little more grounded during these intense stretches?", now - 6 * 86400 + 210),
                ('user', "Honestly, going for walks helps. When I actually do it. But when I'm stressed I just skip it.", now - 6 * 86400 + 400),
                ('assistant', "That's really insightful — you know what works for you, but stress makes it harder to do the very thing that helps. That's such a common pattern. What if the walk didn't have to be a big thing? Even five minutes around the block during a work break?", now - 6 * 86400 + 430),
                ('user', "Yeah, I could probably do that. I think I build it up in my head like it has to be this whole thing.", now - 6 * 86400 + 600),
                ('assistant', "That makes a lot of sense. Sometimes lowering the bar is the most helpful thing — 'getting some air' for five minutes counts just as much as a long walk. Would you want to try that this week and see how it goes?", now - 6 * 86400 + 630),
                ('user', "I'll try. It does help when I actually do it.", now - 6 * 86400 + 750),
                ('assistant', "That's a great plan. And if you miss a day, that's fine too — no need to be perfect about it. The goal is just to give yourself a small reset when things feel heavy.", now - 6 * 86400 + 780),
            ]
            for role, content, ts in c2a_messages:
                db.session.add(Message(conversation_id=c2a.id, role=role, content=content, timestamp=ts))

            # Conversation 2b: Sleep hygiene
            c2b = Conversation(
                user_id=patient1.id,
                title='Sleep Hygiene',
                model_id=model1.id,
                system_prompt_id=prompt1.id if prompt1 else None,
                window_id=w2.id,
                template_id=t2b.id,
                consent_provided=True,
                created_at=now - 4 * 86400,
                updated_at=now - 4 * 86400,
            )
            db.session.add(c2b)
            db.session.flush()

            c2b_messages = [
                ('user', "I've been thinking about the sleep thing. I'm still scrolling on my phone every night and it takes me forever to fall asleep.", now - 4 * 86400),
                ('assistant', "I'm glad you're thinking about it. The phone-before-bed habit is really hard to break because it feels like the easiest way to zone out. What does your evening usually look like after you get home from work?", now - 4 * 86400 + 30),
                ('user', "I eat dinner, watch some TV, then get in bed with my phone. Sometimes I'm on it for an hour or two before I actually sleep.", now - 4 * 86400 + 200),
                ('assistant', "That's a pretty common routine. The tricky part is that the phone light and the endless scrolling keep your brain in 'awake mode' even though your body is tired. Would you be open to experimenting with putting the phone down a bit earlier — even just 20 minutes before you want to sleep?", now - 4 * 86400 + 230),
                ('user', "I could try. What would I do instead though? I feel like I need something to wind down.", now - 4 * 86400 + 400),
                ('assistant', "That's a great question — it's not about just removing the phone, it's about replacing it with something that actually helps you relax. Some people read, some people journal, some people just listen to music. You mentioned journaling helps you sometimes — writing it out, right? That could work well as a wind-down routine.", now - 4 * 86400 + 430),
                ('user', "Yeah, I do like writing things down. It helps get the thoughts out of my head. Maybe I'll try that.", now - 4 * 86400 + 600),
                ('assistant', "That sounds like a solid plan. Even a few minutes of writing before bed could help quiet things down. And if some nights you end up back on the phone, that's okay — it's about building the habit gradually, not flipping a switch overnight.", now - 4 * 86400 + 630),
            ]
            for role, content, ts in c2b_messages:
                db.session.add(Message(conversation_id=c2b.id, role=role, content=content, timestamp=ts))
            print("Created demo window 2 (completed, 2 conversations)")

        # Demo safety plans for test users
        provider = User.query.filter_by(username='provider1').first()
        if provider:
            for username in ['user1']:
                patient = User.query.filter_by(username=username).first()
                if patient and not SafetyPlan.query.filter_by(patient_id=patient.id).first():
                    plan = SafetyPlan(
                        patient_id=patient.id,
                        status='active',
                        version=1,
                        approved_at=time.time(),
                        approved_by=provider.id,
                    )
                    plan.set_warning_signs([
                        {'sign': 'Withdrawing from friends', 'severity': 4, 'context': 'Usually happens after stressful work weeks'},
                        {'sign': 'Difficulty sleeping', 'severity': 3, 'context': 'Precedes low mood episodes'},
                        {'sign': 'Losing interest in hobbies', 'severity': 3, 'context': 'Sign of deepening withdrawal'},
                    ])
                    plan.set_coping_strategies([
                        {'strategy': 'Going for a walk outside', 'effectiveness': 4, 'context': 'Works best in daylight', 'patient_language': 'getting some air'},
                        {'strategy': 'Calling a friend', 'effectiveness': 3, 'context': 'Harder when feeling very low', 'patient_language': 'checking in with someone'},
                        {'strategy': 'Journaling', 'effectiveness': 4, 'context': 'Helps process difficult thoughts', 'patient_language': 'writing it out'},
                    ])
                    plan.set_support_network([
                        {'person': 'Sarah', 'relationship': 'Sister', 'contact_preference': 'Text first, then call', 'comfort_level': 5},
                        {'person': 'James', 'relationship': 'Close friend', 'contact_preference': 'Call anytime', 'comfort_level': 4},
                    ])
                    plan.set_reasons_for_living([
                        {'reason': 'My sister and her kids', 'context': 'Family is very important'},
                        {'reason': 'I want to finish my degree', 'context': 'Long-term goal'},
                        {'reason': 'My dog, Charlie', 'context': 'Daily companionship'},
                    ])
                    plan.set_anti_patterns([
                        {'pattern': 'ask directly about a suicidal plan', 'reason': 'feels interrogative and triggering', 'severity': 3, 'source': 'provider', 'visible_to_patient': True},
                        {'pattern': 'suggest calling crisis hotlines without context', 'reason': 'negative past experiences with crisis lines', 'severity': 2, 'source': 'provider', 'visible_to_patient': True},
                        {'pattern': 'use the phrase "just think positive"', 'reason': 'dismissive of their experience', 'severity': 2, 'source': 'patient', 'visible_to_patient': True},
                        {'pattern': 'bring up family conflicts unprompted', 'reason': 'complex family dynamics — let patient lead', 'severity': 2, 'source': 'provider', 'visible_to_patient': False},
                    ])
                    plan.set_care_team([
                        {'name': provider.username, 'role': 'provider', 'contact_protocol': 'Contact through Cloze platform', 'after_hours': 'Call clinic emergency line'},
                    ])
                    plan.set_emergency_plan({
                        'activation_conditions': 'Expression of active suicidal ideation with means or plan',
                        'preferred_facility': 'City General Hospital — Psychiatric Emergency',
                        'contraindications': 'Avoid restraint if possible — history of trauma response',
                    })
                    plan.provider_notes = 'Patient has history of major depressive episodes. Currently stable on medication. Family dynamics are complex — father is estranged. Sister is primary support.'
                    db.session.add(plan)
                    print(f"Created demo safety plan for {username}")

            # user2 gets a draft plan (provider created, patient not yet filled in)
            patient2 = User.query.filter_by(username='user2').first()
            if patient2 and not SafetyPlan.query.filter_by(patient_id=patient2.id).first():
                plan2 = SafetyPlan(
                    patient_id=patient2.id,
                    status='draft',
                    version=1,
                )
                plan2.set_anti_patterns([
                    {'pattern': 'use CBT reframing techniques', 'reason': 'patient is resistant to CBT framing', 'severity': 2, 'source': 'provider', 'visible_to_patient': True},
                ])
                plan2.set_care_team([
                    {'name': provider.username, 'role': 'provider', 'contact_protocol': 'Contact through Cloze platform', 'after_hours': ''},
                ])
                plan2.set_emergency_plan({
                    'activation_conditions': 'Active suicidal ideation',
                    'preferred_facility': '',
                    'contraindications': '',
                })
                plan2.provider_notes = 'New patient. Intake completed. Awaiting patient safety plan input.'
                db.session.add(plan2)
                print(f"Created draft safety plan for user2")

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