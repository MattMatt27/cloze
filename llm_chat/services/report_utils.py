import time
from typing import List

from ..extensions import db
from ..models import ChatWindow, Report
from report.generator import UnifiedReportGenerator


def generate_report_for_window(window_id: int, report_type: str = None):
    """Generate and persist both summary and detailed reports for a window.

    Always generates both report types. Returns the summary report for
    backward compatibility.
    """
    window = ChatWindow.query.get(window_id)
    if not window:
        raise ValueError(f"Chat window {window_id} not found")

    # Generate summary report if missing
    summary = Report.query.filter_by(window_id=window.id, report_type='summary').first()
    if not summary:
        summary = UnifiedReportGenerator.save_report(window_id, report_type='summary')

    # Generate detailed report if missing
    detailed = Report.query.filter_by(window_id=window.id, report_type='detailed').first()
    if not detailed:
        UnifiedReportGenerator.save_report(window_id, report_type='detailed')

    window.status = 'report_ready'
    db.session.commit()

    return summary


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
            try:
                if not Report.query.filter_by(window_id=window.id, report_type='summary').first():
                    UnifiedReportGenerator.save_report(window.id, report_type='summary')
                if not Report.query.filter_by(window_id=window.id, report_type='detailed').first():
                    UnifiedReportGenerator.save_report(window.id, report_type='detailed')
                window.status = 'report_ready'
                processed.append(window.id)
                changed = True
            except Exception:
                db.session.rollback()
                raise

    if changed:
        db.session.commit()

    return processed
