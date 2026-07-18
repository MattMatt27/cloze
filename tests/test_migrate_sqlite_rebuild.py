"""The sqlite reports-table rebuild in migrate_schema.py.

Legacy sqlite databases carry NOT NULL on reports.window_id/patient_id/
provider_id, which multi-scope v2 reports violate (a flow or account report
has no window). Postgres relaxes via ALTER; sqlite needs rebuild+copy+swap.
This bit the seeded dev DB for 5 of 6 scopes before the fix — and would bite
any self-hosted sqlite deployment on upgrade."""
import sqlite3

from migrate_schema import _sqlite_rebuild_reports, _sqlite_reports_needs_rebuild


def _legacy_reports_db():
    """An in-memory DB shaped like a pre-v2 install AFTER column additions
    (the rebuild runs after ADD COLUMNs in the same migration)."""
    db = sqlite3.connect(":memory:")
    db.execute("""
        CREATE TABLE reports (
            id INTEGER PRIMARY KEY,
            window_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            report_type VARCHAR(50),
            report_data TEXT,
            generated_at FLOAT,
            file_path VARCHAR(255),
            scope VARCHAR(20),
            conversation_id INTEGER,
            flow_enrollment_id INTEGER,
            flow_id INTEGER,
            analyzer_version VARCHAR(20),
            template_id INTEGER
        )""")
    db.execute(
        "INSERT INTO reports (window_id, patient_id, provider_id, report_type,"
        " report_data, generated_at, scope) VALUES (1, 2, 3, 'summary', '{}',"
        " 1234.5, 'window')")
    return db


def test_detects_legacy_not_nulls():
    db = _legacy_reports_db()
    assert _sqlite_reports_needs_rebuild(db.cursor()) is True


def test_rebuild_relaxes_and_preserves_rows():
    db = _legacy_reports_db()
    cursor = db.cursor()
    _sqlite_rebuild_reports(cursor)
    db.commit()

    assert _sqlite_reports_needs_rebuild(cursor) is False
    # legacy row intact
    row = cursor.execute(
        "SELECT window_id, patient_id, provider_id, report_type, scope,"
        " generated_at FROM reports").fetchone()
    assert row == (1, 2, 3, "summary", "window", 1234.5)
    # the previously-impossible insert now works: account-scope report
    cursor.execute(
        "INSERT INTO reports (provider_id, report_type, scope, report_data)"
        " VALUES (9, 'v2', 'account', '{}')")
    assert cursor.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 2


def test_rebuild_is_idempotent_check():
    db = _legacy_reports_db()
    cursor = db.cursor()
    _sqlite_rebuild_reports(cursor)
    # a second migration run must detect nothing to do
    assert _sqlite_reports_needs_rebuild(cursor) is False