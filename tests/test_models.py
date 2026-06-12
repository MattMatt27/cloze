"""Unit tests for core models: auth helpers, lockout, access control,
and the database-enforced one-provider-per-patient constraint."""
import time

import pytest
from sqlalchemy.exc import IntegrityError

from llm_chat.models.core import ProviderPatient


def test_password_hash_roundtrip(make_user):
    user = make_user("alice", password="correct horse")
    assert user.password_hash != "correct horse"  # never stored in cleartext
    assert user.check_password("correct horse")
    assert not user.check_password("wrong")


def test_role_helpers(make_user):
    assert make_user("a", role="admin").is_admin()
    assert make_user("p", role="provider").is_provider()
    assert make_user("u", role="user").is_patient()


def test_is_active_mirrors_visible(make_user):
    user = make_user("u")
    assert user.is_active is True
    user.is_active = False
    assert user.visible is False


def test_lockout_after_five_failures_then_reset(make_user):
    user = make_user("u")
    for _ in range(4):
        user.record_failed_login()
    assert not user.is_locked  # 4 failures: still open
    user.record_failed_login()  # 5th
    assert user.is_locked
    assert user.locked_until > time.time()

    user.record_successful_login()
    assert not user.is_locked
    assert user.failed_login_attempts == 0


def test_can_access_patient_rules(make_user):
    admin = make_user("admin", role="admin")
    provider = make_user("prov", role="provider")
    patient = make_user("pt", role="user")
    other_patient = make_user("pt2", role="user")

    ProviderPatient.query.session.add(
        ProviderPatient(provider_id=provider.id, patient_id=patient.id)
    )
    ProviderPatient.query.session.commit()

    # Admin: everyone
    assert admin.can_access_patient(patient.id)
    assert admin.can_access_patient(other_patient.id)

    # Provider: only assigned patient
    assert provider.can_access_patient(patient.id)
    assert not provider.can_access_patient(other_patient.id)

    # Patient: only themselves
    assert patient.can_access_patient(patient.id)
    assert not patient.can_access_patient(other_patient.id)


def test_one_provider_per_patient_enforced(make_user, db):
    """A patient assigned to one provider cannot be assigned to a second —
    this prevents cross-study data leakage and is enforced at the DB level."""
    provider1 = make_user("prov1", role="provider")
    provider2 = make_user("prov2", role="provider")
    patient = make_user("pt", role="user")

    db.session.add(ProviderPatient(provider_id=provider1.id, patient_id=patient.id))
    db.session.commit()

    db.session.add(ProviderPatient(provider_id=provider2.id, patient_id=patient.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_duplicate_provider_patient_pair_rejected(make_user, db):
    provider = make_user("prov", role="provider")
    patient = make_user("pt", role="user")

    db.session.add(ProviderPatient(provider_id=provider.id, patient_id=patient.id))
    db.session.commit()

    db.session.add(ProviderPatient(provider_id=provider.id, patient_id=patient.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
