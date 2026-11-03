"""Opt-in SMTP notification for newly created critical Mack risk alerts."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_critical_alerts(alerts: list[dict], *, run_id: int) -> int:
    """Send one summary only if SMTP environment variables are configured.

    No credentials or recipient addresses are stored in the database.
    """
    critical = [a for a in alerts if a["status"] == "red"]
    if not critical:
        return 0
    host = os.environ.get("ACTUARIALAI_SMTP_HOST", "")
    recipient = os.environ.get("ACTUARIALAI_ALERT_TO", "")
    sender = os.environ.get("ACTUARIALAI_ALERT_FROM", "")
    if not (host and recipient and sender):
        return 0
    port = int(os.environ.get("ACTUARIALAI_SMTP_PORT", "465"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid SMTP port")
    message = EmailMessage()
    message["Subject"] = f"ActuarialAI critical risk alerts - run {run_id}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Critical Mack risk monitoring alerts (user-defined thresholds):\n\n"
        + "\n".join(
            f"{a['scope']}/{a['name']}: {a['previous_status']} -> {a['status']}"
            for a in critical
        )
        + "\n\nReview in ActuarialAI. This is not regulatory capital."
    )
    with smtplib.SMTP_SSL(
        host, port, timeout=15, context=ssl.create_default_context(),
    ) as server:
        username = os.environ.get("ACTUARIALAI_SMTP_USER", "")
        password = os.environ.get("ACTUARIALAI_SMTP_PASSWORD", "")
        if username and password:
            server.login(username, password)
        server.send_message(message)
    return len(critical)
