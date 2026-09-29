from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .models import EDGE_FIELDS, PERSON_FIELDS, Edge, Person


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
MAPS_DIR = PROJECT_ROOT / "maps"


def ensure_dirs() -> None:
    for directory in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR, MAPS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def people_csv_path() -> Path:
    return PROCESSED_DIR / "people.csv"


def people_json_path() -> Path:
    return PROCESSED_DIR / "people.json"


def edges_csv_path() -> Path:
    return PROCESSED_DIR / "edges.csv"


def topics_csv_path() -> Path:
    return PROCESSED_DIR / "topics.csv"


def campaign_csv_path() -> Path:
    return PROCESSED_DIR / "campaign_contacts.csv"


def publications_json_path() -> Path:
    return PROCESSED_DIR / "publications.json"


def read_people(path: Path | None = None) -> list[Person]:
    path = path or people_csv_path()
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [Person.from_row(row) for row in csv.DictReader(handle)]


def write_people(people: Iterable[Person], csv_path: Path | None = None, json_path: Path | None = None) -> None:
    ensure_dirs()
    csv_path = csv_path or people_csv_path()
    json_path = json_path or people_json_path()
    records = sorted(list(people), key=lambda person: (person.institution.lower(), person.name.lower()))
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PERSON_FIELDS)
        writer.writeheader()
        for person in records:
            writer.writerow(person.to_row())
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump([person.to_row() for person in records], handle, indent=2, ensure_ascii=False)


def read_edges(path: Path | None = None) -> list[Edge]:
    path = path or edges_csv_path()
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [Edge.from_row(row) for row in csv.DictReader(handle)]


def write_edges(edges: Iterable[Edge], path: Path | None = None) -> None:
    ensure_dirs()
    path = path or edges_csv_path()
    unique: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        normalized = edge.normalized()
        key = (normalized.source_person_id, normalized.target_person_id, normalized.edge_type)
        if key in unique:
            existing = unique[key]
            unique[key] = Edge(
                existing.source_person_id,
                existing.target_person_id,
                existing.edge_type,
                existing.weight + normalized.weight,
                existing.evidence_url or normalized.evidence_url,
                existing.evidence_text or normalized.evidence_text,
            )
        else:
            unique[key] = normalized
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EDGE_FIELDS)
        writer.writeheader()
        for edge in sorted(unique.values(), key=lambda item: (item.edge_type, item.source_person_id, item.target_person_id)):
            writer.writerow(edge.to_row())


def read_publications(path: Path | None = None) -> list[dict]:
    path = path or publications_json_path()
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_publications(records: list[dict], path: Path | None = None) -> None:
    ensure_dirs()
    path = path or publications_json_path()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
