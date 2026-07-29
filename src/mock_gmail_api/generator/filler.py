"""Generic noise-email template — volume/filler around the pitch-inbound
scenario so search/pagination behave like a real, mixed inbox rather than
an artificially clean one. "Internal" mail is drawn from a small pool of
synthetic team personas, standing in for mock-superhuman-mcp's
multi-mailbox internal senders now that this repo is single-inbox.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from faker import Faker

from mock_gmail_api.generator import new_id
from mock_gmail_api.models import Message, Thread

_TEMPLATES = ["newsletter", "internal", "calendar", "promo"]

_INTERNAL_TEAM = [
    "harry@acme.example",
    "priya@acme.example",
    "leo@acme.example",
    "sofia@acme.example",
]


def _epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _newsletter(fake: Faker) -> tuple[str, str, str, list[str]]:
    sender_domain = fake.random_element(["substack.com", "mailchimp-relay.com", "beehiiv.com"])
    from_addr = f"newsletter@{fake.word()}.{sender_domain}"
    subject = fake.catch_phrase()
    body = fake.paragraph(nb_sentences=5)
    return from_addr, subject, body, ["INBOX", "CATEGORY_PROMOTIONS"]


def _internal(fake: Faker) -> tuple[str, str, str, list[str]]:
    from_addr = fake.random_element(_INTERNAL_TEAM)
    subject = fake.sentence(nb_words=6)
    body = fake.paragraph(nb_sentences=3)
    return from_addr, subject, body, ["INBOX"]


def _calendar(fake: Faker) -> tuple[str, str, str, list[str]]:
    from_addr = "calendar-notification@google.com"
    subject = f"Invitation: {fake.bs()}"
    body = f"{fake.name()} has invited you to an event.\n\n{fake.paragraph(nb_sentences=2)}"
    return from_addr, subject, body, ["INBOX", "CATEGORY_UPDATES"]


def _promo(fake: Faker) -> tuple[str, str, str, list[str]]:
    from_addr = f"deals@{fake.company().lower().replace(' ', '')}.com"
    subject = fake.catch_phrase()
    body = fake.paragraph(nb_sentences=4)
    return from_addr, subject, body, ["INBOX", "CATEGORY_PROMOTIONS", "UNREAD"]


def make_filler_thread(
    fake: Faker, to_addr: str, reference_time: datetime
) -> tuple[Thread, list[Message]]:
    template = fake.random_element(_TEMPLATES)
    if template == "newsletter":
        from_addr, subject, body, labels = _newsletter(fake)
    elif template == "internal":
        from_addr, subject, body, labels = _internal(fake)
    elif template == "calendar":
        from_addr, subject, body, labels = _calendar(fake)
    else:
        from_addr, subject, body, labels = _promo(fake)

    thread_id = new_id(fake, "thr")
    msg_id = new_id(fake, "msg")
    when = reference_time - timedelta(days=fake.random_int(min=0, max=90))

    message = Message(
        id=msg_id,
        thread_id=thread_id,
        from_addr=from_addr,
        to_addrs=[to_addr],
        subject=subject,
        body_text=body,
        body_html=None,
        headers={
            "From": from_addr,
            "To": to_addr,
            "Subject": subject,
            "Message-ID": f"<{msg_id}@{from_addr.split('@')[-1]}>",
        },
        internal_date=_epoch_ms(when),
        label_ids=labels,
    )
    thread = Thread(id=thread_id, subject=subject, label_ids=labels)
    return thread, [message]
