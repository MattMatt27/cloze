import time
from typing import List

from ..extensions import db
from ..models import ChatWindow, Report
from report.generator import UnifiedReportGenerator


def generate_report_for_window(window_id: int, report_type: str = None):
    """Generate and persist a unified report for a specific window."""
    window = ChatWindow.query.get(window_id)
    if not window:
        raise ValueError(f"Chat window {window_id} not found")

    report = Report.query.filter_by(window_id=window.id).first()
    if not report:
        report = UnifiedReportGenerator.save_report(window_id, report_type=report_type)

    window.status = 'report_ready'
    db.session.commit()

    return report


def finalize_expired_windows() -> List[int]:
    """
    Sync chat window statuses (scheduled → active → generating_report → report_ready)
    and generate reports for windows that reached the generating_report state.
    Returns list of window IDs whose reports were generated/confirmed.
    """
    now = time.time()

    windows = ChatWindow.query.all()
    processed: List[int] = []
    changed = False

    for window in windows:
        previous_status = window.status
        current_status = window.sync_status(now)

        if previous_status != current_status:
            changed = True

        if current_status == 'generating_report':
            existing_report = Report.query.filter_by(window_id=window.id).first()
            try:
                if not existing_report:
                    UnifiedReportGenerator.save_report(window.id)
                window.status = 'report_ready'
                processed.append(window.id)
                changed = True
            except Exception:
                db.session.rollback()
                raise

    if changed:
        db.session.commit()

    return processed
