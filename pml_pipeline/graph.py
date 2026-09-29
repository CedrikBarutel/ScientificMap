from __future__ import annotations

from collections import Counter, defaultdict
import csv
from itertools import combinations
from typing import Iterable

from .html_maps import render_tool
from .models import Edge, Person, TOPIC_FIELDS, normalize_keyword, normalize_name
from .storage import MAPS_DIR, read_people, read_publications, topics_csv_path, write_edges


def add_edge(edges: list[Edge], source: Person, target: Person, edge_type: str, weight: float, evidence: str, url: str = "") -> None:
    if source.person_id == target.person_id:
        return
    edges.append(Edge(source.person_id, target.person_id, edge_type, weight, url, evidence))


def same_institution_edges(people: list[Person]) -> list[Edge]:
    edges: list[Edge] = []
    by_institution: dict[str, list[Person]] = defaultdict(list)
    by_department: dict[tuple[str, str], list[Person]] = defaultdict(list)
    for person in people:
        if person.institution:
            by_institution[person.institution.lower()].append(person)
        if person.institution and person.department:
            by_department[(person.institution.lower(), person.department.lower())].append(person)
    for institution, members in by_institution.items():
        for source, target in combinations(members, 2):
            add_edge(edges, source, target, "same_institution", 0.25, f"Both at {source.institution}")
    for (_institution, _department), members in by_department.items():
        for source, target in combinations(members, 2):
            add_edge(edges, source, target, "same_department", 0.5, f"Both in {source.department}")
    return edges


def shared_keyword_edges(people: list[Person]) -> list[Edge]:
    edges: list[Edge] = []
    keyword_to_people: dict[str, list[Person]] = defaultdict(list)
    for person in people:
        keywords = {normalize_keyword(item) for item in person.research_keywords + person.publication_keywords}
        for keyword in keywords:
            if keyword:
                keyword_to_people[keyword].append(person)
    for keyword, members in keyword_to_people.items():
        if len(members) < 2:
            continue
        for source, target in combinations(members, 2):
            add_edge(edges, source, target, "shared_keyword", 1.0, f"Shared keyword: {keyword}")
    return edges


def coauthor_edges(people: list[Person]) -> list[Edge]:
    edges: list[Edge] = []
    by_name = {normalize_name(person.name): person for person in people}
    for record in read_publications():
        authors = []
        for author_name in record.get("author_names", []):
            person = by_name.get(normalize_name(author_name))
            if person:
                authors.append(person)
        if len(authors) < 2:
            continue
        title = record.get("title", "Publication")
        url = record.get("url", "")
        for source, target in combinations(authors, 2):
            add_edge(edges, source, target, "coauthor", 2.0, f"Coauthor on: {title}", url)
    return edges


def linked_profile_edges(people: list[Person]) -> list[Edge]:
    edges: list[Edge] = []
    by_url = {person.profile_url: person for person in people if person.profile_url}
    for person in people:
        for source_url in person.source_urls:
            linked = by_url.get(source_url)
            if linked and linked.person_id != person.person_id:
                add_edge(edges, person, linked, "linked_profile", 0.75, f"Profile source links to {linked.name}", source_url)
    return edges


def build_topics(people: list[Person]) -> list[dict[str, str]]:
    topic_people: dict[str, list[Person]] = defaultdict(list)
    for person in people:
        keywords = {normalize_keyword(item) for item in person.research_keywords + person.publication_keywords}
        for keyword in keywords:
            if keyword:
                topic_people[keyword].append(person)
    rows: list[dict[str, str]] = []
    for topic, members in sorted(topic_people.items(), key=lambda item: (-len(item[1]), item[0])):
        institutions = sorted({person.institution for person in members if person.institution})
        rows.append(
            {
                "topic": topic,
                "person_count": str(len(members)),
                "people": "; ".join(sorted(person.name for person in members)),
                "institutions": "; ".join(institutions),
                "example_keywords": topic,
            }
        )
    return rows


def write_topics(rows: Iterable[dict[str, str]]) -> None:
    path = topics_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TOPIC_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in TOPIC_FIELDS})


def write_cluster_report(people: list[Person], edges: list[Edge]) -> None:
    institution_counts = Counter(person.institution or "Unknown institution" for person in people)
    keyword_counts = Counter(
        normalize_keyword(keyword)
        for person in people
        for keyword in person.research_keywords + person.publication_keywords
        if normalize_keyword(keyword)
    )
    missing_email = [person for person in people if not person.email]
    lines = [
        "# Academic Network Report",
        "",
        f"People: {len(people)}",
        f"Edges: {len(edges)}",
        "",
        "## Institutions",
        "",
    ]
    lines.extend(f"- {name}: {count}" for name, count in institution_counts.most_common())
    lines.extend(["", "## Main Topics", ""])
    lines.extend(f"- {topic}: {count} people" for topic, count in keyword_counts.most_common(20))
    lines.extend(["", "## Missing Data", ""])
    lines.append(f"- Profiles without email: {len(missing_email)}")
    lines.extend(f"- {person.name} ({person.institution})" for person in missing_email[:30])
    lines.extend(["", "## Seminar Seeds", ""])
    for topic, count in keyword_counts.most_common(10):
        lines.append(f"- {topic.title()}: invite researchers connected by this topic ({count} matching profiles).")
    from .storage import REPORTS_DIR

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "network_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_graph_outputs() -> list[Edge]:
    people = read_people()
    edges = []
    edges.extend(same_institution_edges(people))
    edges.extend(shared_keyword_edges(people))
    edges.extend(coauthor_edges(people))
    edges.extend(linked_profile_edges(people))
    write_edges(edges)
    topic_rows = build_topics(people)
    write_topics(topic_rows)
    render_tool(people, edges, MAPS_DIR / "network_map.html")
    write_cluster_report(people, edges)
    return edges
