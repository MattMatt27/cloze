"""Participant conversations must always carry the universal safety layers.

Only the chat-window path composes the system prompt (universal layers
included), so a participant must never be able to talk to a model through a
conversation that didn't come from a chat window. See advisory
GHSA-cwx7-2jrr-h54g.
"""
import time

import pytest

from llm_chat.extensions import db as _db
from llm_chat.models import ProviderFeatureFlags
from llm_chat.models.chat import Conversation, Message, Model
from llm_chat.models.chat_window import ChatWindow, ChatTemplate
from llm_chat.models.core import ProviderPatient
from llm_chat.services.llm_interface import LLMInterface
from prompts.registry import PromptRegistry

DAY = 86400
JSON_HEADERS = {"Content-Type": "application/json"}


@pytest.fixture
def model(app):
    m = Model(name="test-model", provider="local", model_identifier="test")
    _db.session.add(m)
    _db.session.commit()
    return m


@pytest.fixture
def provider(make_user):
    p = make_user("prov", role="provider")
    # Skip the safety-plan gate so the window route can start a conversation.
    _db.session.add(ProviderFeatureFlags(provider_id=p.id, require_safety_plan=False))
    _db.session.commit()
    return p


@pytest.fixture
def patient(make_user, provider):
    p = make_user("pt", role="user")
    _db.session.add(ProviderPatient(provider_id=provider.id, patient_id=p.id))
    _db.session.commit()
    return p


@pytest.fixture
def no_llm(monkeypatch):
    """Any model call in these tests is a failure, not a network request."""
    def _fail(*args, **kwargs):
        raise AssertionError("the model was called")
    monkeypatch.setattr(LLMInterface, "call_llm", staticmethod(_fail))


def test_window_conversation_stores_universal_layers(app, login_as, provider, patient, model):
    now = time.time()
    window = ChatWindow(patient_id=patient.id, provider_id=provider.id, title="Week 1",
                        start_date=now - DAY, end_date=now + DAY)
    _db.session.add(window)
    _db.session.flush()
    template = ChatTemplate(window_id=window.id, title="Module 1", model_id=model.id,
                            custom_system_prompt="Study protocol text.")
    _db.session.add(template)
    _db.session.commit()

    resp = login_as(patient).post("/api/windows/start_conversation",
                                  json={"template_id": template.id}, headers=JSON_HEADERS)
    assert resp.status_code == 200, resp.get_json()

    stored = _db.session.get(Conversation, resp.get_json()["id"]).system_prompt_content
    universal = PromptRegistry.instance().get_universal_prompts()
    assert universal, "no universal prompts loaded"
    for prompt in universal:
        assert prompt.content in stored, f"universal layer {prompt.id!r} missing"


def test_participant_cannot_message_windowless_conversation(app, login_as, patient, model, no_llm):
    # However it got there, a conversation outside a chat window has no
    # composed prompt behind it.
    conv = Conversation(user_id=patient.id, model_id=model.id, system_prompt_content=None)
    _db.session.add(conv)
    _db.session.commit()

    resp = login_as(patient).post(f"/api/conversation/{conv.id}/message",
                                  json={"message": "hello"}, headers=JSON_HEADERS)
    assert resp.status_code == 403
    assert Message.query.filter_by(conversation_id=conv.id).count() == 0
