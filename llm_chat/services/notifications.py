"""CLOZE-Guard v0 — email notifications via AWS SES.

Sends a dashboard-pointer email when a participant message is flagged.
Deliberately contains NO message content (PHI stays in-app); the email only
identifies the participant and matched term(s) and points staff to the
dashboard.

Authenticated by the EC2 instance IAM role in production. When boto3 or AWS
credentials/sender config are absent (e.g. local dev), this degrades to a
logged no-op rather than raising.
"""

import os

from flask import current_app


def send_guard_email(recipients, patient, hits, conversation):
    """Send a flagged-message alert to configured research staff.

    Args:
        recipients: comma-separated recipient address string.
        patient:    the participant User who sent the message.
        hits:       list of matched keyword strings.
        conversation: the Conversation the message belongs to.
    """
    sender = os.environ.get("CLOZE_GUARD_SENDER")
    region = os.environ.get("AWS_SES_REGION", "us-east-1")

    to_addresses = [e.strip() for e in (recipients or "").split(",") if e.strip()]
    if not sender or not to_addresses:
        current_app.logger.warning(
            "CLOZE-Guard email skipped (sender=%r, recipients=%r)", sender, to_addresses
        )
        return

    try:
        import boto3
    except ImportError:
        current_app.logger.warning("CLOZE-Guard email skipped: boto3 not installed")
        return

    subject = f"[CLOZE-Guard] Flagged message — {patient.username}"
    body = (
        f"Participant {patient.username} (ID {patient.id}) sent a message "
        f"matching flagged term(s): {', '.join(hits)}.\n\n"
        f"Conversation #{conversation.id}. Review the chat log in the provider "
        f"dashboard. (This email intentionally contains no message content.)"
    )

    try:
        ses = boto3.client("ses", region_name=region)
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": to_addresses},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
        current_app.logger.info(
            "CLOZE-Guard alert emailed to %d recipient(s) for patient %s",
            len(to_addresses), patient.id,
        )
    except Exception:
        current_app.logger.exception("CLOZE-Guard SES send failed")
