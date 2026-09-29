from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass
class Source:
    institution: str
    seed_urls: list[str]
    department: str = ""
    allowed_domains: list[str] = field(default_factory=list)
    role_hint: str = ""
    rate_limit_seconds: float = 1.0
    max_depth: int = 1
    profile_selectors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.allowed_domains:
            domains: list[str] = []
            for url in self.seed_urls:
                parsed = urlparse(url)
                if parsed.netloc:
                    domains.append(parsed.netloc.lower())
            self.allowed_domains = sorted(set(domains))
        if not self.profile_selectors:
            self.profile_selectors = [
                ".person",
                ".people",
                ".staff",
                ".staff-member",
                ".member",
                ".profile",
                "article",
            ]

    def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme in ("", "file"):
            return True
        host = parsed.netloc.lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains)


def load_sources(config_path: str | Path) -> list[Source]:
    path = Path(config_path)
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    items = raw.get("sources", [])
    if not isinstance(items, list):
        raise ValueError("config must contain a list under 'sources'")
    sources: list[Source] = []
    for item in items:
        if "institution" not in item or "seed_urls" not in item:
            raise ValueError("each source needs institution and seed_urls")
        seed_urls = item["seed_urls"]
        if isinstance(seed_urls, str):
            seed_urls = [seed_urls]
        sources.append(
            Source(
                institution=str(item["institution"]),
                department=str(item.get("department", "")),
                seed_urls=[str(url) for url in seed_urls],
                allowed_domains=[str(domain).lower() for domain in item.get("allowed_domains", [])],
                role_hint=str(item.get("role_hint", "")),
                rate_limit_seconds=float(item.get("rate_limit_seconds", 1.0)),
                max_depth=int(item.get("max_depth", 1)),
                profile_selectors=[str(selector) for selector in item.get("profile_selectors", [])],
            )
        )
    return sources
