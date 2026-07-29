"""Worked ENV=dev/prod client-selection example for a consuming project to
copy into its own repo. This is a template — mock-gmail-api does not import
it, and it is not exercised against real Google credentials by this repo's
own tests.

Dev branch (ENV=dev): plain `requests` against this mock's HTTP API,
mirroring real Gmail REST paths under `/gmail/v1/users/me/...`.

Prod branch (ENV=prod): a real `googleapiclient.discovery.build("gmail",
"v1", ...)` service, authenticated via `google-auth-oauthlib`. A consuming
project would declare `google-api-python-client`/`google-auth-oauthlib`/
`google-auth-httplib2` as dependencies — this shows the intended usage once
Gmail OAuth is wired up on the prod server. That credential/token-refresh
plumbing stays entirely in the consuming project's own repo per the
dev/prod trust boundary; this function only shows where the branch point is.

Both branches expose the same three operations
(`search_messages`/`get_thread`/`create_draft`) so calling code written
against the mock runs unmodified against real Gmail.
"""

from __future__ import annotations

import os
from typing import Any, Protocol


class GmailClient(Protocol):
    def search_messages(self, query: str, max_results: int = 20) -> dict[str, Any]: ...

    def get_thread(self, thread_id: str) -> dict[str, Any]: ...

    def create_draft(
        self, to: list[str], subject: str, body_text: str, thread_id: str | None = None
    ) -> dict[str, Any]: ...


class MockGmailClient:
    """Dev-branch client: talks to mock-gmail-api over plain HTTP."""

    def __init__(self, base_url: str, token: str) -> None:
        import requests

        self._requests = requests
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def search_messages(self, query: str, max_results: int = 20) -> dict[str, Any]:
        resp = self._session.get(
            f"{self._base_url}/gmail/v1/users/me/messages",
            params={"q": query, "maxResults": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        resp = self._session.get(
            f"{self._base_url}/gmail/v1/users/me/threads/{thread_id}", timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def create_draft(
        self, to: list[str], subject: str, body_text: str, thread_id: str | None = None
    ) -> dict[str, Any]:
        resp = self._session.post(
            f"{self._base_url}/gmail/v1/users/me/drafts",
            json={"to": to, "subject": subject, "body_text": body_text, "thread_id": thread_id},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


class RealGmailClient:
    """Prod-branch client: wraps the real Gmail API via
    `googleapiclient.discovery.build`. Never used by this repo's tests —
    the consuming project supplies real OAuth credentials on the prod
    server only.
    """

    def __init__(self, credentials: object) -> None:
        from googleapiclient.discovery import build  # pyright: ignore[reportMissingImports]

        # `credentials` is a google.oauth2.credentials.Credentials instance
        # the consuming project obtains via its own OAuth flow
        # (google-auth-oauthlib) on the prod server — never constructed or
        # refreshed by this repo.
        self._service = build("gmail", "v1", credentials=credentials)

    def search_messages(self, query: str, max_results: int = 20) -> dict[str, Any]:
        return (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        return self._service.users().threads().get(userId="me", id=thread_id).execute()

    def create_draft(
        self, to: list[str], subject: str, body_text: str, thread_id: str | None = None
    ) -> dict[str, Any]:
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body_text)
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        body: dict[str, Any] = {"message": {"raw": raw}}
        if thread_id is not None:
            body["message"]["threadId"] = thread_id
        return self._service.users().drafts().create(userId="me", body=body).execute()


def _load_prod_credentials() -> object:
    """Placeholder for the consuming project's real OAuth token loading
    (refresh-token file, secrets manager, etc.). Not implemented here —
    this repo never runs the prod branch."""
    raise NotImplementedError(
        "prod credential loading is the consuming project's responsibility; "
        "this repo never runs the prod branch"
    )


def get_gmail_client(env: str) -> GmailClient:
    """The branch point calling code should build around: construct
    a `GmailClient` for `ENV=dev` (mock) or `ENV=prod` (real Gmail),
    identically shaped either way.
    """
    if env == "dev":
        base_url = os.environ.get("MOCK_GMAIL_BASE_URL", "http://localhost:8000")
        token = os.environ.get("MOCK_GMAIL_DEV_TOKEN", "dev-secret-token")
        return MockGmailClient(base_url, token)
    if env == "prod":
        credentials = _load_prod_credentials()
        return RealGmailClient(credentials)
    raise ValueError(f"unknown ENV: {env!r} (expected 'dev' or 'prod')")


def main() -> None:
    env = os.environ.get("ENV", "dev")
    client = get_gmail_client(env)

    results = client.search_messages("to:pitches@acme.example newer_than:1d")
    print(f"found {results.get('resultSizeEstimate', 0)} matching message(s)")

    for item in results.get("messages", []):
        thread = client.get_thread(item["threadId"])
        print(f"thread {thread['id']}: {len(thread['messages'])} message(s)")

    draft = client.create_draft(
        to=["harry@acme.example"],
        subject="Weekly tear-sheet (draft)",
        body_text="Summary of this week's pitch inbound goes here.",
    )
    print(f"created draft {draft['id']}")


if __name__ == "__main__":
    main()
