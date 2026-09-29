from __future__ import annotations

from collections import Counter
import re
from typing import Any

import requests

from .models import Person, normalize_keyword, normalize_name, split_list
from .storage import read_people, read_publications, write_people, write_publications


STOPWORDS = {
    "about",
    "after",
    "analysis",
    "and",
    "are",
    "based",
    "between",
    "data",
    "from",
    "into",
    "model",
    "models",
    "of",
    "on",
    "study",
    "the",
    "this",
    "using",
    "with",
}


def keywords_from_text(text: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+-]{3,}", text.lower())
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def openalex_author_search(person: Person, max_works: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
    query = person.name
    if person.institution:
        query = f"{person.name} {person.institution}"
    response = requests.get(
        "https://api.openalex.org/authors",
        params={"search": query, "per-page": 1},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return [], []
    author = results[0]
    works_api_url = author.get("works_api_url")
    if not works_api_url:
        return [], []
    works_response = requests.get(works_api_url, params={"per-page": max_works}, timeout=20)
    works_response.raise_for_status()
    works = works_response.json().get("results", [])

    keywords: list[str] = []
    records: list[dict[str, Any]] = []
    for work in works:
        title = work.get("title") or ""
        concepts = [concept.get("display_name", "") for concept in work.get("concepts", [])[:5]]
        keywords.extend(concepts)
        keywords.extend(keywords_from_text(title, limit=5))
        author_names = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in work.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        records.append(
            {
                "person_id": person.person_id,
                "title": title,
                "url": work.get("doi") or work.get("id") or "",
                "concepts": split_list(concepts),
                "author_names": split_list(author_names),
            }
        )
    return split_list(keywords)[:20], records


def merge_local_publication_keywords(people: list[Person], publication_records: list[dict[str, Any]]) -> list[Person]:
    people_by_name = {normalize_name(person.name): person for person in people}
    for record in publication_records:
        concepts = split_list(record.get("concepts", []))
        title_keywords = keywords_from_text(str(record.get("title", "")))
        names = split_list(record.get("author_names", []))
        target_ids = set(split_list(record.get("person_id", "")))
        for name in names:
            person = people_by_name.get(normalize_name(name))
            if person:
                target_ids.add(person.person_id)
        for person in people:
            if person.person_id in target_ids:
                person.publication_keywords = split_list(person.publication_keywords + concepts + title_keywords)
                person.confidence_score = max(person.confidence_score, 0.65)
    return people


def enrich_people(use_network: bool = True, max_works: int = 5) -> list[Person]:
    people = read_people()
    publication_records = read_publications()
    people = merge_local_publication_keywords(people, publication_records)

    if use_network:
        for person in people:
            if not person.name:
                continue
            try:
                keywords, records = openalex_author_search(person, max_works=max_works)
            except Exception as exc:
                person.notes = f"{person.notes}; enrichment failed: {exc}".strip("; ")
                continue
            person.publication_keywords = split_list(person.publication_keywords + keywords)
            if keywords:
                person.confidence_score = max(person.confidence_score, 0.7)
            publication_records.extend(records)

    write_people(people)
    write_publications(publication_records)
    return people
