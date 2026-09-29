from __future__ import annotations

import csv
import re

from .models import Person, normalize_keyword
from .storage import PROCESSED_DIR, REPORTS_DIR, read_people


def match_score(person: Person, topic: str) -> tuple[int, list[str]]:
    topic_terms = {term for term in re.findall(r"[a-z0-9+-]+", normalize_keyword(topic)) if len(term) > 2}
    keywords = [normalize_keyword(item) for item in person.research_keywords + person.publication_keywords]
    hits = [keyword for keyword in keywords if any(term in keyword for term in topic_terms)]
    score = len(hits)
    department = normalize_keyword(person.department)
    if topic_terms and any(term in department for term in topic_terms):
        score += 1
        if person.department:
            hits.append(f"department: {person.department}")
    return score, hits


def ranked_people_for_topic(people: list[Person], topic: str) -> list[tuple[Person, int, list[str]]]:
    ranked = []
    for person in people:
        score, hits = match_score(person, topic)
        if score > 0:
            ranked.append((person, score, hits))
    return sorted(ranked, key=lambda item: (-item[1], item[0].institution.lower(), item[0].name.lower()))


def suggest_seminars(topic: str, max_contacts: int = 50) -> tuple[str, list[dict[str, str]]]:
    people = read_people()
    ranked = ranked_people_for_topic(people, topic)[:max_contacts]
    safe_topic = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.strip()).strip("_") or "topic"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for person, score, hits in ranked:
        rows.append(
            {
                "person_id": person.person_id,
                "name": person.name,
                "email": person.email,
                "institution": person.institution,
                "department": person.department,
                "location": person.location,
                "score": str(score),
                "reason": "; ".join(hits) or f"Profile appears related to {topic}",
                "source_evidence": "; ".join(person.source_urls),
            }
        )

    csv_path = PROCESSED_DIR / f"seminar_candidates_{safe_topic}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "person_id",
                "name",
                "email",
                "institution",
                "department",
                "location",
                "score",
                "reason",
                "source_evidence",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    institutions = sorted({row["institution"] for row in rows if row["institution"]})
    questions = [
        f"Which methods or datasets currently define the {topic} research community?",
        f"Where could Vienna-area groups collaborate around {topic}?",
        f"What short meeting format would help junior and senior researchers exchange concrete open problems?",
    ]
    lines = [
        f"# Seminar Suggestions: {topic}",
        "",
        f"Candidate title: Vienna research exchange on {topic}",
        "",
        "## Motivation",
        "",
        f"This topic matches {len(rows)} profiles across {len(institutions)} institutions.",
        "",
        "## Main Questions",
        "",
    ]
    lines.extend(f"- {question}" for question in questions)
    lines.extend(["", "## Candidate Invitees", ""])
    if rows:
        for row in rows:
            contact = row["email"] or "email missing"
            lines.append(f"- {row['name']} ({row['institution']}, {row['location'] or 'location missing'}, {contact}): {row['reason']}")
    else:
        lines.append("- No matching profiles yet. Run collect/enrich/build-graph first or try a broader topic.")
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Check uncertain contacts manually before exporting a campaign.",
            "- Do not send invitations automatically from this project.",
            f"- Candidate CSV: `{csv_path}`",
        ]
    )
    report_path = REPORTS_DIR / f"seminar_suggestions_{safe_topic}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(report_path), rows
