"""Shared pytest fixtures for Cloze.

Sets environment defaults *before* importing the application so that
`create_app()` builds an isolated, in-memory test instance.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest

from llm_chat import create_app
from llm_chat.extensions import db as _db
from llm_chat.models.core import User


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """The active SQLAlchemy session/handle, inside the app context."""
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    """Clear the module-global IP rate-limit state between tests so login
    tests don't leak attempt counts into one another."""
    from llm_chat.routes import auth as auth_module
    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


@pytest.fixture
def make_user(app):
    """Factory: create and persist a User with a known password."""
    def _make(username, role="user", password="pw-12345", **kwargs):
        user = User(
            username=username,
            email=kwargs.pop("email", f"{username}@example.test"),
            role=role,
            **kwargs,
        )
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user
    return _make


@pytest.fixture
def make_conversation(app, make_user):
    """Factory: a conversation with the given (role, content, timestamp) messages."""
    from llm_chat.models import Conversation, Message, Model

    model = Model(name="test-model", provider="local")
    _db.session.add(model)
    _db.session.commit()

    def _make(messages, user=None):
        user = user or make_user(f"patient{Conversation.query.count()}")
        conversation = Conversation(user_id=user.id, model_id=model.id)
        _db.session.add(conversation)
        _db.session.commit()
        for role, content, ts in messages:
            _db.session.add(Message(
                conversation_id=conversation.id, role=role, content=content, timestamp=ts,
            ))
        _db.session.commit()
        return conversation

    return _make


DAY = 86400.0
T0 = 1780000000.0   # seeded-study start
WEEK2 = T0 + 7 * DAY


@pytest.fixture
def study(app, make_user):
    """Two-provider study hierarchy for scope/report tests.

    provider1: flow1 "Mindfulness" (Week 1, Week 2)
      alice: w1 (Week 1, FK-linked, 2 convs), w2 (Week 2, LEGACY name-linked,
             1 conv), w4 standalone (1 conv), plus one window-less free conv
      bob:   w3 (Week 1, FK-linked, 1 conv) — never started Week 2
    provider2: flow2 "Other Study", carol, w5 (1 conv) — isolation control.
    """
    from llm_chat.models import (
        ChatWindow, Conversation, FlowEnrollment, FlowPhase, Message, Model,
        ProviderPatient, StudyFlow,
    )

    model = Model(name="test-model", provider="local")
    _db.session.add(model)
    _db.session.commit()

    provider1 = make_user("prov1", role="provider")
    provider2 = make_user("prov2", role="provider")
    alice = make_user("alice")
    bob = make_user("bob")
    carol = make_user("carol")
    for provider, patient in [(provider1, alice), (provider1, bob), (provider2, carol)]:
        _db.session.add(ProviderPatient(provider_id=provider.id, patient_id=patient.id))

    flow1 = StudyFlow(provider_id=provider1.id, name="Mindfulness",
                      flow_type="phased", created_at=T0)
    flow2 = StudyFlow(provider_id=provider2.id, name="Other Study",
                      flow_type="phased", created_at=T0)
    _db.session.add_all([flow1, flow2])
    _db.session.commit()
    _db.session.add_all([
        FlowPhase(flow_id=flow1.id, name="Week 1", order_index=0, start_day=0),
        FlowPhase(flow_id=flow1.id, name="Week 2", order_index=1, start_day=7),
    ])

    enr_alice = FlowEnrollment(flow_id=flow1.id, patient_id=alice.id, enrolled_at=T0)
    enr_bob = FlowEnrollment(flow_id=flow1.id, patient_id=bob.id, enrolled_at=T0 + 1)
    enr_carol = FlowEnrollment(flow_id=flow2.id, patient_id=carol.id, enrolled_at=T0)
    _db.session.add_all([enr_alice, enr_bob, enr_carol])
    _db.session.commit()

    def window(patient, title, start, *, flow_id=None, flow_name=None, phase=None,
               provider=provider1):
        w = ChatWindow(patient_id=patient.id, provider_id=provider.id, title=title,
                       start_date=start, end_date=start + 7 * DAY,
                       flow_id=flow_id, flow_name=flow_name, phase_label=phase)
        _db.session.add(w)
        _db.session.commit()
        return w

    def conversation(patient, window, texts, t):
        c = Conversation(user_id=patient.id, model_id=model.id,
                         window_id=window.id if window else None, created_at=t)
        _db.session.add(c)
        _db.session.commit()
        for offset, (role, content) in enumerate(texts):
            _db.session.add(Message(conversation_id=c.id, role=role,
                                    content=content, timestamp=t + offset * 60))
        _db.session.commit()
        return c

    w1 = window(alice, "Week 1", T0, flow_id=flow1.id, flow_name="Mindfulness",
                phase="Week 1")
    # LEGACY linkage: no FK, name only — must still resolve into the enrollment
    w2 = window(alice, "Week 2", WEEK2, flow_name="Mindfulness", phase="Week 2")
    w3 = window(bob, "Week 1", T0 + DAY, flow_id=flow1.id, flow_name="Mindfulness",
                phase="Week 1")
    w4 = window(alice, "Extra check-in", T0 + 3 * DAY)  # standalone, no flow
    w5 = window(carol, "Other W1", T0, flow_id=flow2.id, flow_name="Other Study",
                phase="Week 1", provider=provider2)

    convs = {
        "a_w1_1": conversation(alice, w1, [("user", "I feel happy and grateful today."),
                                           ("assistant", "That is lovely to hear.")], T0),
        "a_w1_2": conversation(alice, w1, [("user", "Still feeling good. Maybe tired?")],
                               T0 + DAY),
        "a_w2_1": conversation(alice, w2, [("user", "This week was sad and frustrating."),
                                           ("assistant", "I hear you.")], WEEK2),
        "b_w3_1": conversation(bob, w3, [("user", "Trying the exercises. Feeling anxious.")],
                               T0 + DAY),
        "a_w4_1": conversation(alice, w4, [("user", "Quick extra chat here.")],
                               T0 + 3 * DAY),
        "a_free": conversation(alice, None, [("user", "Old free-form conversation.")],
                               T0 - 30 * DAY),
        "c_w5_1": conversation(carol, w5, [("user", "Different study entirely.")], T0),
    }

    class NS:
        pass

    ns = NS()
    ns.provider1, ns.provider2 = provider1, provider2
    ns.alice, ns.bob, ns.carol = alice, bob, carol
    ns.flow1, ns.flow2 = flow1, flow2
    ns.enr_alice, ns.enr_bob, ns.enr_carol = enr_alice, enr_bob, enr_carol
    ns.w1, ns.w2, ns.w3, ns.w4, ns.w5 = w1, w2, w3, w4, w5
    ns.convs = convs
    return ns


@pytest.fixture
def login_as(app):
    """Return a fresh test client already authenticated as `user`, by seeding
    the Flask-Login session cookie directly (see flask_login_test_pattern).

    A new client per call avoids cross-identity session bleed that occurs when
    one client's session cookie is rewritten between requests.
    """
    def _login(user):
        # Tests run inside a single app context, and Flask-Login caches the
        # resolved user on `g`. Clear it so switching identity mid-test takes
        # effect instead of returning the previously cached user.
        from flask import g
        g.pop("_login_user", None)

        c = app.test_client()
        with c.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True
        return c
    return _login
