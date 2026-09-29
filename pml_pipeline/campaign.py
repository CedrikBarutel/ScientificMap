from __future__ import annotations

import csv
import re

from .models import CAMPAIGN_FIELDS
from .seminar import ranked_people_for_topic
from .storage import campaign_csv_path, read_people


def read_existing_status() -> dict[str, dict[str, str]]:
    path = campaign_csv_path()
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row.get("person_id", ""): row for row in rows if row.get("person_id")}


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def is_truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(str(value).strip()))


def draft_subject(topic: str) -> str:
    return f"Invitation: small Vienna research meeting on {topic}"


def draft_body(name: str, topic: str, reason: str) -> str:
    first_name = name.split()[0] if name else "there"
    return (
        f"Dear {first_name},\n\n"
        f"I am preparing a small academic meeting in Vienna around {topic}. "
        f"I found your profile relevant because of: {reason}.\n\n"
        "This is only a draft invitation prepared for manual review. "
        "Please confirm the event details, legal basis, and opt-out wording before sending.\n\n"
        "Best regards,\n"
    )


def export_campaign(campaign_name: str, topic: str, max_contacts: int = 50) -> tuple[str, int]:
    people = read_people()
    existing = read_existing_status()
    ranked = ranked_people_for_topic(people, topic)
    rows: list[dict[str, str]] = []
    for person, _score, hits in ranked:
        previous = existing.get(person.person_id, {})
        if is_truthy(previous.get("opt_out", "")):
            continue
        if not is_valid_email(person.email):
            continue
        reason = "; ".join(hits) or f"Profile appears related to {topic}"
        rows.append(
            {
                "campaign_name": campaign_name,
                "person_id": person.person_id,
                "name": person.name,
                "email": person.email,
                "institution": person.institution,
                "department": person.department,
                "location": person.location,
                "selected": "true",
                "review_status": previous.get("review_status", "needs_review"),
                "last_contacted_at": previous.get("last_contacted_at", ""),
                "opt_out": previous.get("opt_out", "false"),
                "reason_for_contact": reason,
                "draft_subject": draft_subject(topic),
                "draft_body": draft_body(person.name, topic, reason),
                "source_evidence": "; ".join(person.source_urls),
            }
        )
        if len(rows) >= max_contacts:
            break

    path = campaign_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAMPAIGN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return str(path), len(rows)
