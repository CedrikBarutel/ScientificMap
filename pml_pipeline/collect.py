from __future__ import annotations

from collections import deque
from email.utils import parsedate_to_datetime
from html import unescape
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .config import Source, load_sources
from .models import Person, normalize_text, split_list
from .storage import write_people


EMAIL_RE = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}")
ACADEMIC_LINK_RE = re.compile(r"(person|people|profile|staff|team|member|faculty|group|lab|research)", re.I)
KEYWORD_LABEL_RE = re.compile(r"(research|interest|keyword|topic|area|focus|expertise)", re.I)
ROLE_RE = re.compile(r"\b(professor|postdoc|postdoctoral|phd|doctoral|lecturer|researcher|scientist|group leader|pi)\b", re.I)


class Fetcher:
    def __init__(self, user_agent: str = "AcademicMailingListBot/0.1") -> None:
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.robots: dict[str, RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme in ("", "file"):
            return True
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = self.robots.get(robots_url)
        if parser is None:
            parser = RobotFileParser(robots_url)
            try:
                parser.read()
            except Exception:
                return True
            self.robots[robots_url] = parser
        return parser.can_fetch(self.user_agent, url)

    def fetch(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return Path(unquote(parsed.path)).read_text(encoding="utf-8")
        if parsed.scheme == "" and Path(url).exists():
            return Path(url).read_text(encoding="utf-8")
        if not self.can_fetch(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.text


def clean_email(value: str) -> str:
    value = unescape(value).replace("mailto:", "")
    value = value.split("?")[0]
    return normalize_text(value).lower()


def extract_emails(soup: BeautifulSoup) -> list[str]:
    emails: list[str] = []
    for link in soup.select("a[href^='mailto:']"):
        emails.extend(EMAIL_RE.findall(clean_email(link.get("href", ""))))
    text = soup.get_text(" ", strip=True)
    emails.extend(EMAIL_RE.findall(text))
    return split_list(emails)


def extract_name(soup: BeautifulSoup, fallback_email: str = "") -> str:
    for selector in ("h1", "h2", ".name", ".person-name", ".profile-name", "[itemprop='name']"):
        node = soup.select_one(selector)
        if node:
            candidate = normalize_text(node.get_text(" ", strip=True))
            if candidate and len(candidate.split()) <= 8:
                return candidate
    title = soup.find("title")
    if title:
        candidate = normalize_text(re.split(r"[-|]", title.get_text(" ", strip=True))[0])
        if candidate and len(candidate.split()) <= 8:
            return candidate
    if fallback_email:
        local = fallback_email.split("@")[0].replace(".", " ").replace("_", " ")
        return " ".join(part.capitalize() for part in local.split())
    return ""


def extract_role(soup: BeautifulSoup, role_hint: str = "") -> str:
    if role_hint:
        return role_hint
    text = soup.get_text(" ", strip=True)
    match = ROLE_RE.search(text)
    return normalize_text(match.group(0)) if match else ""


def extract_keywords(soup: BeautifulSoup) -> list[str]:
    keywords: list[str] = []
    for meta_name in ("keywords", "citation_keywords", "dc.subject"):
        node = soup.select_one(f"meta[name='{meta_name}']")
        if node and node.get("content"):
            keywords.extend(split_list(node["content"]))

    for heading in soup.find_all(re.compile("^h[1-6]$")):
        heading_text = heading.get_text(" ", strip=True)
        if not KEYWORD_LABEL_RE.search(heading_text):
            continue
        for sibling in heading.find_next_siblings(limit=4):
            if sibling.name and re.match("^h[1-6]$", sibling.name):
                break
            text = normalize_text(sibling.get_text(" ", strip=True))
            if text:
                keywords.extend(split_list(text))

    for selector in (".research", ".interests", ".keywords", ".topics", "[itemprop='knowsAbout']"):
        for node in soup.select(selector):
            keywords.extend(split_list(node.get_text(" ", strip=True)))

    return [item for item in split_list(keywords) if 2 <= len(item) <= 80][:20]


def extract_profile_links(soup: BeautifulSoup, base_url: str, source: Source) -> list[str]:
    links: list[str] = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        text = link.get_text(" ", strip=True)
        candidate = urljoin(base_url, href)
        if not source.is_allowed(candidate):
            continue
        if ACADEMIC_LINK_RE.search(href) or ACADEMIC_LINK_RE.search(text):
            links.append(candidate.split("#")[0])
    return split_list(links)


def looks_like_profile(soup: BeautifulSoup) -> bool:
    return bool(extract_emails(soup) or soup.select_one("[itemtype*='Person'], [itemprop='email']"))


def parse_person_html(html: str, url: str, source: Source) -> list[Person]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[BeautifulSoup] = []
    candidate_html: set[str] = set()
    for selector in source.profile_selectors:
        for node in soup.select(selector):
            html_fragment = str(node)
            if html_fragment in candidate_html:
                continue
            node_soup = BeautifulSoup(html_fragment, "html.parser")
            if extract_emails(node_soup):
                candidate_html.add(html_fragment)
                candidates.append(node_soup)
    if not candidates and looks_like_profile(soup):
        candidates = [soup]

    people: list[Person] = []
    for candidate in candidates:
        emails = extract_emails(candidate)
        fallback_email = emails[0] if emails else ""
        name = extract_name(candidate, fallback_email)
        if not name:
            continue
        keywords = extract_keywords(candidate)
        role = extract_role(candidate, source.role_hint)
        profile_url = url
        for link in candidate.select("a[href]"):
            href = link.get("href", "")
            if "mailto:" not in href:
                profile_url = urljoin(url, href)
                break
        people.append(
            Person(
                name=name,
                email=fallback_email,
                institution=source.institution,
                department=source.department,
                role=role,
                profile_url=profile_url,
                research_keywords=keywords,
                source_urls=[url],
            )
        )
    return people


def dedupe_people(people: Iterable[Person]) -> list[Person]:
    by_id: dict[str, Person] = {}
    aliases: dict[tuple[str, str], str] = {}
    for person in people:
        key = (person.email, person.profile_url)
        alias_key = (person.name.lower(), person.institution.lower())
        existing_id = by_id.get(person.person_id) and person.person_id
        existing_id = existing_id or aliases.get(alias_key)
        if person.email:
            for known in by_id.values():
                if known.email and known.email == person.email:
                    existing_id = known.person_id
                    break
        if existing_id and existing_id in by_id:
            by_id[existing_id] = by_id[existing_id].merge(person)
        else:
            by_id[person.person_id] = person
            aliases[alias_key] = person.person_id
            if key[0] or key[1]:
                aliases[key] = person.person_id
    return list(by_id.values())


def collect_from_sources(config_path: str, output: bool = True) -> list[Person]:
    fetcher = Fetcher()
    collected: list[Person] = []
    sources = load_sources(config_path)
    for source in sources:
        queue: deque[tuple[str, int]] = deque((url, 0) for url in source.seed_urls)
        seen: set[str] = set()
        while queue:
            url, depth = queue.popleft()
            if url in seen or not source.is_allowed(url):
                continue
            seen.add(url)
            try:
                html = fetcher.fetch(url)
            except Exception as exc:
                collected.append(
                    Person(
                        name=f"Fetch failed: {url}",
                        institution=source.institution,
                        department=source.department,
                        source_urls=[url],
                        confidence_score=0.1,
                        notes=str(exc),
                    )
                )
                continue
            collected.extend(parse_person_html(html, url, source))
            if depth < source.max_depth:
                soup = BeautifulSoup(html, "html.parser")
                for link in extract_profile_links(soup, url, source):
                    queue.append((link, depth + 1))
            if source.rate_limit_seconds > 0:
                time.sleep(source.rate_limit_seconds)

    people = [person for person in dedupe_people(collected) if not person.name.startswith("Fetch failed:")]
    if output:
        write_people(people)
    return people
