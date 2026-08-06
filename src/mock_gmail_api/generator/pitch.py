"""VC pitch-inbound email template: the primary realistic scenario this
generator exists for — a founder emails a deck (sometimes via a forwarded
warm intro, sometimes with a follow-up), carrying structured fields
(sector/ask/stage/company) that mirror a downstream Airtable/vault
frontmatter convention.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from faker import Faker

from mock_gmail_api.docgen import CAP_TABLE, ONE_PAGER, PITCH_DECK, DocumentCache
from mock_gmail_api.generator import new_id, slugify_company_name
from mock_gmail_api.models import Attachment, Message, PitchMeta, Thread

SECTORS = [
    "Fintech",
    "SaaS",
    "Healthtech",
    "Climate",
    "AI/ML",
    "Marketplace",
    "Devtools",
    "Consumer",
    "Biotech",
    "Cybersecurity",
]

STAGES = ["Pre-seed", "Seed", "Series A", "Series B"]

_STAGE_ASKS = {
    "Pre-seed": ["£250k", "£400k", "£500k"],
    "Seed": ["£750k", "£1.2m", "£1.5m", "£2m"],
    "Series A": ["£3m", "£5m", "£8m"],
    "Series B": ["£12m", "£18m", "£25m"],
}

PITCH_LABEL = "PITCH-INBOUND"


def _epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _pitch_body(fake: Faker, company_name: str, sector: str, stage: str, ask: str) -> str:
    return (
        f"Hi,\n\n"
        f"I'm the founder of {company_name}, a {sector.lower()} company. "
        f"We're raising a {stage.lower()} round of {ask} and wanted to share our deck.\n\n"
        f"{fake.paragraph(nb_sentences=3)}\n\n"
        f"{fake.paragraph(nb_sentences=2)}\n\n"
        f"Would love to find 20 minutes to talk this week if it's of interest.\n\n"
        f"Best,\n{fake.name()}"
    )


def _make_attachments(
    fake: Faker,
    message_id: str,
    company_slug: str,
    pitch_meta: PitchMeta,
    docgen_cache: DocumentCache,
) -> list[Attachment]:
    content_ref, data = docgen_cache.get_or_generate(PITCH_DECK, pitch_meta)
    attachments = [
        Attachment(
            id=new_id(fake, "att"),
            message_id=message_id,
            filename=f"{company_slug}_Pitch_Deck.pdf",
            mimetype=PITCH_DECK.mimetype,
            size_bytes=len(data),
            page_count=None,
            content_ref=content_ref,
        )
    ]
    if fake.random.random() < 0.3:
        content_ref, data = docgen_cache.get_or_generate(CAP_TABLE, pitch_meta)
        attachments.append(
            Attachment(
                id=new_id(fake, "att"),
                message_id=message_id,
                filename=f"{company_slug}_Cap_Table.xlsx",
                mimetype=CAP_TABLE.mimetype,
                size_bytes=len(data),
                page_count=None,
                content_ref=content_ref,
            )
        )
    if fake.random.random() < 0.3:
        content_ref, data = docgen_cache.get_or_generate(ONE_PAGER, pitch_meta)
        attachments.append(
            Attachment(
                id=new_id(fake, "att"),
                message_id=message_id,
                filename=f"{company_slug}_One_Pager.docx",
                mimetype=ONE_PAGER.mimetype,
                size_bytes=len(data),
                page_count=None,
                content_ref=content_ref,
            )
        )
    return attachments


def make_pitch_thread(
    fake: Faker, to_addr: str, reference_time: datetime, docgen_cache: DocumentCache
) -> tuple[Thread, list[Message], list[Attachment]]:
    company_name = fake.company()
    sector = fake.random_element(SECTORS)
    stage = fake.random_element(STAGES)
    ask = fake.random_element(_STAGE_ASKS[stage])
    founder = fake.name()
    company_slug = slugify_company_name(company_name)
    company_domain = f"{company_slug.lower()}.com"
    founder_email = f"{founder.split()[0].lower()}@{company_domain}"

    pitch_meta = PitchMeta(company_name=company_name, sector=sector, ask=ask, stage=stage)

    thread_id = new_id(fake, "thr")
    base_time = reference_time - timedelta(days=fake.random_int(min=0, max=90))

    messages: list[Message] = []
    attachments: list[Attachment] = []

    is_multi_message = fake.random.random() < 0.4

    if is_multi_message:
        intro_subject = f"Intro: {company_name}"
        connector = fake.name()
        connector_email = fake.company_email()
        intro_msg_id = new_id(fake, "msg")
        intro_body = (
            f"Hi Harry,\n\nLooping you in with {founder} at {company_name} — "
            f"thought this could be relevant given the {sector.lower()} space. "
            f"Adding {founder} here to share more.\n\nBest,\n{connector}"
        )
        messages.append(
            Message(
                id=intro_msg_id,
                thread_id=thread_id,
                from_addr=connector_email,
                to_addrs=[to_addr, founder_email],
                subject=intro_subject,
                body_text=intro_body,
                body_html=None,
                headers={
                    "From": connector_email,
                    "To": f"{to_addr}, {founder_email}",
                    "Subject": intro_subject,
                    "Message-ID": f"<{intro_msg_id}@mail.example>",
                },
                internal_date=_epoch_ms(base_time),
                label_ids=["INBOX", "UNREAD"],
            )
        )

        followup_time = base_time + timedelta(hours=fake.random_int(min=1, max=48))
        followup_subject = f"Re: {intro_subject}"
        followup_id = new_id(fake, "msg")
        followup_body = _pitch_body(fake, company_name, sector, stage, ask)
        messages.append(
            Message(
                id=followup_id,
                thread_id=thread_id,
                from_addr=founder_email,
                to_addrs=[to_addr],
                subject=followup_subject,
                body_text=followup_body,
                body_html=f"<p>{followup_body.replace(chr(10), '<br>')}</p>",
                headers={
                    "From": founder_email,
                    "To": to_addr,
                    "Subject": followup_subject,
                    "Message-ID": f"<{followup_id}@{company_domain}>",
                    "In-Reply-To": f"<{intro_msg_id}@mail.example>",
                },
                internal_date=_epoch_ms(followup_time),
                label_ids=["INBOX", "UNREAD", PITCH_LABEL],
                pitch_meta=pitch_meta,
            )
        )
        attachments.extend(
            _make_attachments(fake, followup_id, company_slug, pitch_meta, docgen_cache)
        )
        thread_subject = intro_subject
    else:
        subject = f"{company_name} — {stage} pitch ({sector})"
        msg_id = new_id(fake, "msg")
        body = _pitch_body(fake, company_name, sector, stage, ask)
        messages.append(
            Message(
                id=msg_id,
                thread_id=thread_id,
                from_addr=founder_email,
                to_addrs=[to_addr],
                subject=subject,
                body_text=body,
                body_html=f"<p>{body.replace(chr(10), '<br>')}</p>",
                headers={
                    "From": founder_email,
                    "To": to_addr,
                    "Subject": subject,
                    "Message-ID": f"<{msg_id}@{company_domain}>",
                },
                internal_date=_epoch_ms(base_time),
                label_ids=["INBOX", "UNREAD", PITCH_LABEL],
                pitch_meta=pitch_meta,
            )
        )
        attachments.extend(_make_attachments(fake, msg_id, company_slug, pitch_meta, docgen_cache))
        thread_subject = subject

    thread = Thread(
        id=thread_id,
        subject=thread_subject,
        label_ids=["INBOX", "UNREAD", PITCH_LABEL],
    )
    return thread, messages, attachments
