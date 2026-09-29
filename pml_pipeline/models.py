from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import re
from typing import Any


PERSON_FIELDS = [
    "person_id",
    "name",
    "email",
    "institution",
    "department",
    "location",
    "role",
    "profile_url",
    "research_keywords",
    "publication_keywords",
    "source_urls",
    "confidence_score",
    "last_seen_at",
    "notes",
]

EDGE_FIELDS = [
    "source_person_id",
    "target_person_id",
    "edge_type",
    "weight",
    "evidence_url",
    "evidence_text",
]

CAMPAIGN_FIELDS = [
    "campaign_name",
    "person_id",
    "name",
    "email",
    "institution",
    "department",
    "location",
    "selected",
    "review_status",
    "last_contacted_at",
    "opt_out",
    "reason_for_contact",
    "draft_subject",
    "draft_body",
    "source_evidence",
]

TOPIC_FIELDS = [
    "topic",
    "person_count",
    "people",
    "institutions",
    "example_keywords",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def normalize_name(value: str | None) -> str:
    value = normalize_text(value).lower()
    value = re.sub(r"\b(dr|prof|professor|phd|msc|ma|ba)\.?\b", "", value)
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    return normalize_text(value)


def normalize_email(value: str | None) -> str:
    return normalize_text(value).lower()


def normalize_institution(value: str | None) -> str:
    return normalize_text(value).lower()


def normalize_keyword(value: str | None) -> str:
    value = normalize_text(value).lower()
    value = re.sub(r"[^a-z0-9\s+-]", "", value)
    return normalize_text(value)


def split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = re.split(r"[;,\n|]+", str(value))
    seen: set[str] = set()
    items: list[str] = []
    for item in raw_values:
        cleaned = normalize_text(str(item))
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            items.append(cleaned)
    return items


def join_list(values: list[str]) -> str:
    return "; ".join(split_list(values))


def make_person_id(name: str, institution: str = "", email: str = "", profile_url: str = "") -> str:
    if email:
        identity = f"email:{normalize_email(email)}"
    elif profile_url:
        identity = f"url:{normalize_text(profile_url)}"
    else:
        identity = f"name:{normalize_name(name)}|institution:{normalize_institution(institution)}"
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]
    return f"p_{digest}"


def confidence_for(person: "Person") -> float:
    has_identity = bool(person.email or person.profile_url)
    has_keywords = bool(person.research_keywords or person.publication_keywords)
    if person.email and has_keywords and person.profile_url:
        return 0.95
    if has_identity and has_keywords:
        return 0.8
    if has_identity:
        return 0.6
    return 0.35


@dataclass
class Person:
    name: str
    email: str = ""
    institution: str = ""
    department: str = ""
    location: str = ""
    role: str = ""
    profile_url: str = ""
    research_keywords: list[str] = field(default_factory=list)
    publication_keywords: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    last_seen_at: str = field(default_factory=utc_now_iso)
    notes: str = ""
    person_id: str = ""

    def __post_init__(self) -> None:
        self.name = normalize_text(self.name)
        self.email = normalize_email(self.email)
        self.institution = normalize_text(self.institution)
        self.department = normalize_text(self.department)
        self.location = normalize_text(self.location)
        self.role = normalize_text(self.role)
        self.profile_url = normalize_text(self.profile_url)
        self.research_keywords = split_list(self.research_keywords)
        self.publication_keywords = split_list(self.publication_keywords)
        self.source_urls = split_list(self.source_urls)
        if not self.person_id:
            self.person_id = make_person_id(
                self.name,
                self.institution,
                self.email,
                self.profile_url,
            )
        if not self.confidence_score:
            self.confidence_score = confidence_for(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Person":
        data = dict(row)
        for key in ("research_keywords", "publication_keywords", "source_urls"):
            data[key] = split_list(data.get(key))
        try:
            data["confidence_score"] = float(data.get("confidence_score") or 0)
        except ValueError:
            data["confidence_score"] = 0.0
        allowed = {field_name: data.get(field_name, "") for field_name in PERSON_FIELDS}
        return cls(**allowed)

    def to_row(self) -> dict[str, str]:
        row = asdict(self)
        row["research_keywords"] = join_list(self.research_keywords)
        row["publication_keywords"] = join_list(self.publication_keywords)
        row["source_urls"] = join_list(self.source_urls)
        row["confidence_score"] = f"{self.confidence_score:.2f}"
        return {field_name: str(row.get(field_name, "")) for field_name in PERSON_FIELDS}

    def merge(self, other: "Person") -> "Person":
        """Merge another record while preserving stronger existing evidence."""
        if other.confidence_score > self.confidence_score:
            primary, secondary = other, self
        else:
            primary, secondary = self, other

        merged = Person(
            person_id=primary.person_id or secondary.person_id,
            name=primary.name or secondary.name,
            email=primary.email or secondary.email,
            institution=primary.institution or secondary.institution,
            department=primary.department or secondary.department,
            location=primary.location or secondary.location,
            role=primary.role or secondary.role,
            profile_url=primary.profile_url or secondary.profile_url,
            research_keywords=split_list(primary.research_keywords + secondary.research_keywords),
            publication_keywords=split_list(primary.publication_keywords + secondary.publication_keywords),
            source_urls=split_list(primary.source_urls + secondary.source_urls),
            confidence_score=max(primary.confidence_score, secondary.confidence_score),
            last_seen_at=max(primary.last_seen_at, secondary.last_seen_at),
            notes=primary.notes or secondary.notes,
        )
        if self.email and other.email and self.email != other.email:
            merged.notes = normalize_text(f"{merged.notes}; alternate email observed: {other.email}")
        return merged


@dataclass(frozen=True)
class Edge:
    source_person_id: str
    target_person_id: str
    edge_type: str
    weight: float = 1.0
    evidence_url: str = ""
    evidence_text: str = ""

    def normalized(self) -> "Edge":
        source, target = sorted([self.source_person_id, self.target_person_id])
        return Edge(
            source,
            target,
            self.edge_type,
            self.weight,
            self.evidence_url,
            normalize_text(self.evidence_text),
        )

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Edge":
        try:
            weight = float(row.get("weight") or 1.0)
        except ValueError:
            weight = 1.0
        return cls(
            source_person_id=str(row.get("source_person_id", "")),
            target_person_id=str(row.get("target_person_id", "")),
            edge_type=str(row.get("edge_type", "")),
            weight=weight,
            evidence_url=str(row.get("evidence_url", "")),
            evidence_text=str(row.get("evidence_text", "")),
        )

    def to_row(self) -> dict[str, str]:
        edge = self.normalized()
        return {
            "source_person_id": edge.source_person_id,
            "target_person_id": edge.target_person_id,
            "edge_type": edge.edge_type,
            "weight": f"{edge.weight:.2f}",
            "evidence_url": edge.evidence_url,
            "evidence_text": edge.evidence_text,
        }
