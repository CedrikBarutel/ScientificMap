#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pml_pipeline.campaign import export_campaign
from pml_pipeline.collect import collect_from_sources
from pml_pipeline.enrich import enrich_people
from pml_pipeline.graph import build_graph_outputs
from pml_pipeline.seminar import suggest_seminars
from pml_pipeline.storage import ensure_dirs


def default_config_path() -> str:
    return str(Path(__file__).resolve().parent / "config" / "sources.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a local academic contact dataset, network maps, seminar suggestions, and campaign exports."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect public academic profiles from configured official sources.")
    collect.add_argument("--config", default=default_config_path(), help="Path to config/sources.yaml.")

    enrich = subparsers.add_parser("enrich", help="Enrich profiles with publication metadata.")
    enrich.add_argument("--no-network", action="store_true", help="Use only local publication records.")
    enrich.add_argument("--max-works", type=int, default=5, help="Maximum works to fetch per person from OpenAlex.")

    subparsers.add_parser("build-graph", help="Build edges, topic table, HTML maps, and a Markdown network report.")

    suggest = subparsers.add_parser("suggest-seminars", help="Create seminar ideas and candidate invitee files.")
    suggest.add_argument("--topic", required=True, help="Topic or phrase to match against profile/publication keywords.")
    suggest.add_argument("--max-contacts", type=int, default=50, help="Maximum candidate contacts to include.")

    campaign = subparsers.add_parser("export-campaign", help="Export a human-reviewed mail-merge CSV. Does not send email.")
    campaign.add_argument("--campaign-name", required=True, help="Human-readable campaign name.")
    campaign.add_argument("--topic", required=True, help="Topic or phrase to match against profile/publication keywords.")
    campaign.add_argument("--max-contacts", type=int, default=50, help="Maximum contacts to export.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ensure_dirs()

    if args.command == "collect":
        people = collect_from_sources(args.config)
        print(f"Collected {len(people)} people into data/processed/people.csv")
        return 0
    if args.command == "enrich":
        people = enrich_people(use_network=not args.no_network, max_works=args.max_works)
        print(f"Enriched {len(people)} people into data/processed/people.csv")
        return 0
    if args.command == "build-graph":
        edges = build_graph_outputs()
        print(f"Built {len(edges)} graph edges, maps, topics, and reports")
        return 0
    if args.command == "suggest-seminars":
        path, rows = suggest_seminars(args.topic, args.max_contacts)
        print(f"Wrote {len(rows)} seminar candidates and report: {path}")
        return 0
    if args.command == "export-campaign":
        path, count = export_campaign(args.campaign_name, args.topic, args.max_contacts)
        print(f"Wrote {count} reviewed campaign contacts to {path}. No emails were sent.")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
