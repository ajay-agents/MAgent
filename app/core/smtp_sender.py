import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


def _header(value: str) -> str:
    # Collapse whitespace so model output can never inject extra headers via CR/LF
    return " ".join(value.split())


def new_message_id(from_address: str) -> str:
    return make_msgid(domain=from_address.rsplit("@", 1)[-1])


def build_message(from_address: str, to_email: str, subject: str, body: str,
                  message_id: str | None = None, in_reply_to: str | None = None,
                  extra_headers: dict[str, str] | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_address
    msg["To"] = _header(to_email)
    msg["Subject"] = _header(subject)
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = message_id or new_message_id(from_address)
    if in_reply_to:  # threads the follow-up under the original in the recipient's inbox
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    for name, value in (extra_headers or {}).items():
        msg[name] = _header(value)
    msg.set_content(body)
    return msg


def send_email(
    gmail_address: str,
    app_password: str,
    to_email: str,
    subject: str,
    body: str,
    message_id: str | None = None,
    in_reply_to: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> None:
    msg = build_message(gmail_address, to_email, subject, body, message_id, in_reply_to, extra_headers)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(gmail_address, app_password)
        server.send_message(msg)


def verify_login(gmail_address: str, app_password: str) -> None:
    """Raises smtplib.SMTPAuthenticationError (or a connection error) if the credentials don't work."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(gmail_address, app_password)
