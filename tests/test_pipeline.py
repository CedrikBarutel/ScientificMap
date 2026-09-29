from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from pml_pipeline.config import Source
from pml_pipeline.collect import dedupe_people, parse_person_html
from pml_pipeline.graph import build_graph_outputs, shared_keyword_edges
from pml_pipeline.models import Person
from pml_pipeline.seminar import suggest_seminars
from pml_pipeline.storage import (
    PROCESSED_DIR,
    campaign_csv_path,
    people_csv_path,
    publications_json_path,
    read_people,
    write_people,
)
from pml_pipeline.campaign import export_campaign


FIXTURES = Path(__file__).parent / "fixtures"


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        for path in PROCESSED_DIR.glob("*"):
            if path.is_file():
                path.unlink()

    def test_parse_profile_html(self) -> None:
        source = Source(
            institution="Example University",
            department="Computer Science",
            seed_urls=[],
            rate_limit_seconds=0,
        )
        html = (FIXTURES / "profile.html").read_text(encoding="utf-8")
        people = parse_person_html(html, "https://example.edu/ada", source)
        self.assertEqual(len(people), 1)
        person = people[0]
        self.assertEqual(person.name, "Dr Ada Example")
        self.assertEqual(person.email, "ada.example@example.edu")
        self.assertIn("machine learning", [item.lower() for item in person.research_keywords])
        self.assertEqual(person.institution, "Example University")

    def test_dedupe_people_prefers_stronger_record(self) -> None:
        weak = Person(name="Ada Example", institution="Example University")
        strong = Person(
            name="Ada Example",
            email="ada.example@example.edu",
            institution="Example University",
            research_keywords=["machine learning"],
            profile_url="https://example.edu/ada",
        )
        people = dedupe_people([weak, strong])
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0].email, "ada.example@example.edu")
        self.assertIn("machine learning", people[0].research_keywords)

    def test_shared_keyword_edges(self) -> None:
        ada = Person(name="Ada Example", institution="Example", research_keywords=["machine learning"])
        bruno = Person(name="Bruno Sample", institution="Example", research_keywords=["machine learning"])
        edges = shared_keyword_edges([ada, bruno])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].edge_type, "shared_keyword")

    def test_full_offline_pipeline_outputs(self) -> None:
        people = [
            Person(
                name="Ada Example",
                email="ada.example@example.edu",
                institution="Example University",
                department="Computer Science",
                research_keywords=["machine learning", "generative models"],
                source_urls=["https://example.edu/ada"],
            ),
            Person(
                name="Bruno Sample",
                email="bruno.sample@example.edu",
                institution="Example University",
                department="Mathematics",
                research_keywords=["geometry", "machine learning"],
                source_urls=["https://example.edu/bruno"],
            ),
        ]
        write_people(people)
        publications_json_path().write_text(
            json.dumps(
                [
                    {
                        "title": "Machine learning for geometry",
                        "url": "https://doi.org/example",
                        "concepts": ["machine learning"],
                        "author_names": ["Ada Example", "Bruno Sample"],
                    }
                ]
            ),
            encoding="utf-8",
        )
        edges = build_graph_outputs()
        self.assertTrue(people_csv_path().exists())
        self.assertGreaterEqual(len(edges), 1)
        report_path, rows = suggest_seminars("machine learning", max_contacts=10)
        self.assertTrue(Path(report_path).exists())
        self.assertEqual(len(rows), 2)
        campaign_path, count = export_campaign("test campaign", "machine learning", max_contacts=10)
        self.assertEqual(count, 2)
        with Path(campaign_path).open(newline="", encoding="utf-8") as handle:
            exported = list(csv.DictReader(handle))
        self.assertEqual(exported[0]["review_status"], "needs_review")
        self.assertIn("No emails were sent", "No emails were sent")

    def test_campaign_respects_opt_out(self) -> None:
        write_people(
            [
                Person(
                    name="Ada Example",
                    email="ada.example@example.edu",
                    institution="Example University",
                    research_keywords=["machine learning"],
                )
            ]
        )
        person = read_people()[0]
        with campaign_csv_path().open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "campaign_name",
                    "person_id",
                    "name",
                    "email",
                    "institution",
                    "department",
                    "selected",
                    "review_status",
                    "last_contacted_at",
                    "opt_out",
                    "reason_for_contact",
                    "draft_subject",
                    "draft_body",
                    "source_evidence",
                ],
            )
            writer.writeheader()
            writer.writerow({"person_id": person.person_id, "opt_out": "true"})
        _path, count = export_campaign("test campaign", "machine learning", max_contacts=10)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
