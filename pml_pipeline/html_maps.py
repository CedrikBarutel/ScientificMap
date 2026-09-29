from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from .models import Edge, Person


VIEW_WIDTH = 1000
VIEW_HEIGHT = 720


def institution_hierarchy(person: Person) -> dict[str, str]:
    top = person.university or person.institution or "Unknown institution"
    faculty = person.faculty or top
    institute = person.institute or faculty
    unit = person.unit or institute
    group = person.group or unit
    return {
        "institution": top,
        "faculty": faculty,
        "institute": institute,
        "unit": unit,
        "group_level": group,
    }


def group_value(person: Person, group_by: str) -> str:
    if group_by == "keyword":
        keywords = person.research_keywords or person.publication_keywords
        return keywords[0] if keywords else "Unknown topic"
    hierarchy = institution_hierarchy(person)
    if group_by == "institution":
        return hierarchy["institution"]
    if group_by == "faculty":
        return hierarchy["faculty"]
    if group_by == "institute":
        return hierarchy["institute"]
    if group_by == "unit":
        return hierarchy["unit"]
    if group_by == "group":
        return hierarchy["group_level"]
    return hierarchy["institution"]


def build_nodes(people: list[Person], group_by: str) -> list[dict]:
    """Create a stable clustered layout for one grouping mode."""
    by_group: dict[str, list[Person]] = defaultdict(list)
    for person in people:
        by_group[group_value(person, group_by)].append(person)

    groups = sorted(by_group)
    center_x = VIEW_WIDTH / 2
    center_y = VIEW_HEIGHT / 2
    cluster_ring = min(VIEW_WIDTH, VIEW_HEIGHT) * 0.31
    nodes: list[dict] = []

    for group_index, group in enumerate(groups):
        members = sorted(by_group[group], key=lambda person: person.name.lower())
        if len(groups) == 1:
            cluster_x, cluster_y = center_x, center_y
        else:
            cluster_angle = (2 * math.pi * group_index) / len(groups) - math.pi / 2
            cluster_x = center_x + cluster_ring * math.cos(cluster_angle)
            cluster_y = center_y + cluster_ring * math.sin(cluster_angle)

        local_radius = 22 + 10 * math.sqrt(max(len(members), 1))
        for member_index, person in enumerate(members):
            hierarchy = institution_hierarchy(person)
            if len(members) == 1:
                x, y = cluster_x, cluster_y
            else:
                angle = (2 * math.pi * member_index) / len(members)
                ring = local_radius + 13 * (member_index // 12)
                x = cluster_x + ring * math.cos(angle)
                y = cluster_y + ring * math.sin(angle)

            nodes.append(
                {
                    "id": person.person_id,
                    "name": person.name,
                    "email": person.email,
                    "institution": person.institution,
                    "department": person.department,
                    "university": person.university or person.institution,
                    "faculty": person.faculty,
                    "institute": person.institute,
                    "unit": person.unit,
                    "group_level": person.group or hierarchy["group_level"],
                    "affiliation_status": person.affiliation_status,
                    "location": person.location,
                    "role": person.role,
                    "profile_url": person.profile_url,
                    "group": group,
                    "keywords": person.research_keywords + person.publication_keywords,
                    "source_urls": person.source_urls,
                    "notes": person.notes,
                    "x": round(x, 2),
                    "y": round(y, 2),
                }
            )
    return nodes


def relation_category(edge_type: str) -> str:
    normalized = edge_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"coauthor", "collaboration", "collaborator", "co_investigator", "co_pi"}:
        return "collaboration"
    if normalized in {
        "hierarchy",
        "supervisor",
        "supervisee",
        "advisor",
        "advisee",
        "pi_member",
        "group_leader_member",
        "mentor",
        "mentee",
    }:
        return "hierarchy"
    if normalized in {"same_university", "same_faculty", "same_institute", "same_unit", "same_group", "same_department", "same_institution"}:
        return "affiliation"
    if normalized == "shared_keyword":
        return "topic"
    if normalized == "linked_profile":
        return "linked"
    return "context"


def build_links(people: list[Person], edges: list[Edge]) -> list[dict]:
    visible_ids = {person.person_id for person in people}
    return [
        {
            "source": edge.normalized().source_person_id,
            "target": edge.normalized().target_person_id,
            "type": edge.edge_type,
            "category": relation_category(edge.edge_type),
            "weight": edge.weight,
            "evidence": edge.evidence_text,
        }
        for edge in edges
        if edge.source_person_id in visible_ids and edge.target_person_id in visible_ids
    ]


def render_tool(people: list[Person], edges: list[Edge], output_path: Path) -> None:
    view_specs = [
        ("institution", "University / institution"),
        ("faculty", "Faculty"),
        ("institute", "Institute"),
        ("unit", "Department / unit"),
        ("group", "Research group"),
        ("topic", "Research topic"),
    ]
    built_views = {}
    for key, label in view_specs:
        group_by = "keyword" if key == "topic" else key
        nodes = build_nodes(people, group_by)
        built_views[key] = {
            "label": label,
            "nodes": nodes,
            "groups": sorted({node["group"] for node in nodes}),
        }
    data = json.dumps(
        {
            "views": built_views,
            "links": build_links(people, edges),
        },
        ensure_ascii=False,
    )

    html = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ScientificMap</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f6f8;
      --panel: #ffffff;
      --line: #d9dde5;
      --text: #18202b;
      --muted: #667085;
      --accent: #2f6690;
      --accent-soft: #e9f0f7;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; color: var(--text); background: var(--bg); }
    header { background: var(--panel); border-bottom: 1px solid var(--line); }
    .topbar { padding: 15px 22px 0; display: flex; align-items: baseline; gap: 14px; }
    h1 { margin: 0; font-size: 22px; }
    .subtitle { color: var(--muted); font-size: 13px; }
    .tabs { display: flex; gap: 4px; padding: 12px 22px 0; }
    .tab { border: 0; background: transparent; padding: 10px 14px; border-bottom: 3px solid transparent; cursor: pointer; font-weight: 650; color: #475467; }
    .tab.active { color: var(--accent); border-color: var(--accent); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }

    .controls { padding: 12px 18px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; background: var(--panel); border-bottom: 1px solid var(--line); }
    .segmented { display: inline-flex; border: 1px solid #b8c0cc; border-radius: 8px; overflow: hidden; background: #fff; }
    .segmented button { border: 0; border-right: 1px solid #d5dae1; background: #fff; padding: 8px 12px; cursor: pointer; }
    .segmented button:last-child { border-right: 0; }
    .segmented button.active { background: var(--accent-soft); color: #174a70; font-weight: 700; }
    button, select, input, textarea { font: inherit; }
    select, input, textarea { min-height: 36px; border: 1px solid #b8c0cc; border-radius: 7px; padding: 7px 9px; background: #fff; }
    .control-button { min-height: 36px; border: 1px solid #b8c0cc; border-radius: 7px; background: #fff; padding: 6px 10px; cursor: pointer; }
    .control-button:hover { background: #f3f5f7; }
    .zoom-group { display: inline-flex; gap: 4px; margin-left: auto; }
    .zoom-group .control-button { min-width: 38px; font-weight: 700; }

    .map-layout { display: grid; grid-template-columns: minmax(0, 1fr) 310px; min-height: calc(100vh - 145px); }
    .map-wrap { position: relative; min-width: 0; overflow: hidden; background: #fbfcfd; }
    svg { width: 100%; height: calc(100vh - 145px); display: block; cursor: grab; user-select: none; touch-action: none; }
    svg.dragging { cursor: grabbing; }
    aside { border-left: 1px solid var(--line); background: var(--panel); padding: 16px; overflow: auto; max-height: calc(100vh - 145px); }
    aside h2 { margin: 0 0 12px; font-size: 19px; }
    aside p { margin: 8px 0; line-height: 1.4; }
    aside a { color: #245b86; overflow-wrap: anywhere; }
    .node { cursor: pointer; stroke: #fff; stroke-width: 1.8; vector-effect: non-scaling-stroke; transition: opacity .15s ease; }
    .node:hover { stroke: #18202b; stroke-width: 2.3; }
    .link { stroke: #9aa6b2; stroke-opacity: .45; vector-effect: non-scaling-stroke; }
    .link.affiliation-university { stroke: #6b7280; stroke-opacity: .10; }
    .link.affiliation-faculty { stroke: #64748b; stroke-opacity: .18; }
    .link.affiliation-institute { stroke: #52657a; stroke-opacity: .30; }
    .link.affiliation-unit { stroke: #3f6476; stroke-opacity: .48; }
    .link.affiliation-group { stroke: #315f73; stroke-opacity: .78; }
    .link.relation-collaboration { stroke: #356d9f; stroke-opacity: .95; }
    .link.relation-hierarchy { stroke: #b77928; stroke-opacity: .95; stroke-dasharray: 7 4; }
    .link.relation-affiliation { stroke: #4f8f55; stroke-opacity: .9; }
    .link.relation-topic { stroke: #8a63a8; stroke-opacity: .9; }
    .link.relation-linked { stroke: #2f7f87; stroke-opacity: .9; stroke-dasharray: 3 3; }
    .link.relation-context { stroke: #7a6a45; stroke-opacity: .8; }
    .node.selected { stroke: #111827; stroke-width: 3; }
    .relation-toggle { display: flex; align-items: center; gap: 8px; padding: 10px 0; margin: 10px 0; border-top: 1px solid #eceff3; border-bottom: 1px solid #eceff3; }
    .relation-toggle input { min-height: 0; }
    .relation-legend { display: grid; gap: 6px; margin: 8px 0 12px; font-size: 12px; color: var(--muted); }
    .legend-line { display: inline-block; width: 28px; height: 0; margin-right: 7px; vertical-align: middle; border-top: 3px solid #356d9f; }
    .legend-line.hierarchy { border-top-color: #b77928; border-top-style: dashed; }
    .legend-line.affiliation { border-top-color: #4f8f55; }
    .legend-line.topic { border-top-color: #8a63a8; }
    .legend-line.linked { border-top-color: #2f7f87; border-top-style: dashed; }
    .legend-line.context { border-top-color: #7a6a45; }
    .label { font-size: 11px; pointer-events: auto; cursor: pointer; fill: #253040; paint-order: stroke; stroke: #fbfcfd; stroke-width: 3px; stroke-linejoin: round; }
    .muted { color: var(--muted); }
    .status { font-size: 12px; color: var(--muted); }
    .hierarchy-legend {
      position: absolute; left: 12px; bottom: 10px; z-index: 2;
      display: flex; gap: 10px; flex-wrap: wrap; max-width: calc(100% - 24px);
      padding: 6px 8px; border: 1px solid var(--line); border-radius: 7px;
      background: rgba(255,255,255,.9); color: var(--muted); font-size: 11px;
      pointer-events: none;
    }
    .hierarchy-legend span::before {
      content: ""; display: inline-block; width: 24px; margin-right: 5px;
      vertical-align: middle; border-top: 2px solid #315f73;
    }
    .hierarchy-legend .unit::before { opacity: .62; }
    .hierarchy-legend .institute::before { opacity: .40; }
    .hierarchy-legend .faculty::before { opacity: .26; }
    .hierarchy-legend .university::before { opacity: .14; }

    .content { max-width: 1050px; margin: 0 auto; padding: 26px 22px 50px; }
    .content h2 { margin-top: 0; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 18px; margin-bottom: 16px; }
    .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 13px; }
    .form-grid label { display: flex; flex-direction: column; gap: 5px; font-size: 13px; font-weight: 650; }
    .form-grid .wide { grid-column: 1 / -1; }
    textarea { min-height: 80px; resize: vertical; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .primary { border-color: var(--accent); background: var(--accent); color: white; }
    .primary:hover { background: #245779; }
    pre { background: #f7f8fa; border: 1px solid var(--line); border-radius: 7px; padding: 12px; overflow-x: auto; white-space: pre-wrap; }
    .algo-row { display: grid; grid-template-columns: 190px 1fr auto; gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid #eceff3; }
    .algo-row:last-child { border-bottom: 0; }
    .algo-row code { font-size: 12px; }

    @media (max-width: 800px) {
      .map-layout { grid-template-columns: 1fr; }
      aside { border-left: 0; border-top: 1px solid var(--line); max-height: none; }
      svg { height: 67vh; }
      .zoom-group { margin-left: 0; }
      .form-grid { grid-template-columns: 1fr; }
      .form-grid .wide { grid-column: auto; }
      .algo-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<header>
  <div class="topbar">
    <h1>ScientificMap</h1>
    <span class="subtitle">academic network explorer</span>
  </div>
  <nav class="tabs" aria-label="ScientificMap sections">
    <button class="tab active" data-tab="explorer">Explorer</button>
    <button class="tab" data-tab="add-info">Add info</button>
    <button class="tab" data-tab="algorithms">Algorithms</button>
  </nav>
</header>

<section id="explorer" class="tab-panel active">
  <div class="controls">
    <div class="segmented" aria-label="Map grouping">
      <button id="modeInstitution" class="active" data-mode="institution">Institution</button>
      <button id="modeTopic" data-mode="topic">Topic</button>
    </div>
    <label id="institutionLevelControl">Layout by
      <select id="institutionLevel">
        <option value="institution">University / institution</option>
        <option value="faculty">Faculty</option>
        <option value="institute">Institute</option>
        <option value="unit">Department / unit</option>
        <option value="group">Research group</option>
      </select>
    </label>
    <label id="hierarchyDetailControl">Hierarchy detail
      <select id="hierarchyDepth">
        <option value="1">Group only</option>
        <option value="2">+ Department / unit</option>
        <option value="3" selected>+ Institute</option>
        <option value="4">+ Faculty</option>
        <option value="5">+ University</option>
      </select>
    </label>
    <label>Group <select id="groupFilter"><option value="">All groups</option></select></label>
    <label>Search <input id="search" placeholder="Name, institution, keyword"></label>
    <label><input id="labelsToggle" type="checkbox" checked> Labels</label>
    <span id="visibleStatus" class="status"></span>
    <div class="zoom-group" aria-label="Map zoom controls">
      <button class="control-button" id="zoomOut" title="Zoom out">−</button>
      <button class="control-button" id="zoomIn" title="Zoom in">+</button>
      <button class="control-button" id="fitVisible">Fit visible</button>
      <button class="control-button" id="resetView">Reset</button>
    </div>
  </div>
  <div class="map-layout">
    <div class="map-wrap">
      <div id="hierarchyLegend" class="hierarchy-legend">
        <span>Group</span><span class="unit">Unit</span><span class="institute">Institute</span><span class="faculty">Faculty</span><span class="university">University</span>
      </div>
      <svg id="map" viewBox="0 0 1000 720" role="img" aria-label="Academic network map">
        <g id="viewport"></g>
      </svg>
    </div>
    <aside id="details"><strong>Academic network</strong><p class="muted">Select a node to inspect profile details.</p></aside>
  </div>
</section>

<section id="add-info" class="tab-panel">
  <div class="content">
    <h2>Add researcher information</h2>
    <p class="muted">This page is static, so it cannot write directly to GitHub. Fill the form and copy or download a CSV row ready to add to the project dataset.</p>
    <div class="card">
      <div class="form-grid" id="personForm">
        <label>Name<input data-field="name" placeholder="Name"></label>
        <label>Email<input data-field="email" placeholder="name@institution.org"></label>
        <label>Institution<input data-field="institution" placeholder="Institution"></label>
        <label>University<input data-field="university" placeholder="University"></label>
        <label>Faculty<input data-field="faculty" placeholder="Faculty"></label>
        <label>Institute<input data-field="institute" placeholder="Institute"></label>
        <label>Department / Unit<input data-field="unit" placeholder="Department / unit"></label>
        <label>Research group<input data-field="group" placeholder="Research group"></label>
        <label>Legacy department<input data-field="department" placeholder="Original department string"></label>
        <label>Status<input data-field="affiliation_status" placeholder="current / alumni / former"></label>
        <label>Location<input data-field="location" placeholder="City or address"></label>
        <label>Role<input data-field="role" placeholder="PI, postdoc, PhD, ..."></label>
        <label class="wide">Profile URL<input data-field="profile_url" placeholder="https://..."></label>
        <label class="wide">Research keywords<input data-field="research_keywords" placeholder="active matter; cytoskeleton; soft matter"></label>
        <label class="wide">Source URLs<input data-field="source_urls" placeholder="https://...; https://..."></label>
        <label class="wide">Notes<textarea data-field="notes" placeholder="For example: met in Leiden 2026; discussed spindle mechanics"></textarea></label>
      </div>
      <div class="actions">
        <button class="control-button primary" id="copyCsv">Copy CSV row</button>
        <button class="control-button" id="downloadCsv">Download CSV row</button>
        <button class="control-button" id="clearForm">Clear</button>
      </div>
      <p id="formStatus" class="status"></p>
      <pre id="csvPreview"></pre>
    </div>
  </div>
</section>

<section id="algorithms" class="tab-panel">
  <div class="content">
    <h2>Algorithms & data pipeline</h2>
    <p class="muted">These are the project operations behind the map. Copy a command and run it from the repository on your machine.</p>
    <div class="card">
      <div class="algo-row"><strong>Collect profiles</strong><span>Collect public academic profiles from configured official sources.</span><button class="control-button copy-command" data-command="python3 script.py collect --config config/sources.yaml">Copy command</button></div>
      <div class="algo-row"><strong>Enrich profiles</strong><span>Add publication metadata and publication-derived research keywords.</span><button class="control-button copy-command" data-command="python3 script.py enrich">Copy command</button></div>
      <div class="algo-row"><strong>Build network</strong><span>Construct institution, department, keyword, linked-profile, and coauthor edges; rebuild this map.</span><button class="control-button copy-command" data-command="python3 script.py build-graph">Copy command</button></div>
      <div class="algo-row"><strong>Suggest seminar</strong><span>Find researchers matching a topic and generate a candidate list.</span><button class="control-button copy-command" data-command="python3 script.py suggest-seminars --topic &quot;active matter&quot; --max-contacts 30">Copy example</button></div>
      <div class="algo-row"><strong>Export campaign</strong><span>Create a manual-review CSV for an invitation campaign. It does not send email.</span><button class="control-button copy-command" data-command="python3 script.py export-campaign --campaign-name &quot;Seminar&quot; --topic &quot;active matter&quot;">Copy example</button></div>
    </div>
    <div class="card">
      <strong>Current graph relations</strong>
      <p class="muted">same institution · same department · shared keyword · linked profile · coauthor</p>
    </div>
  </div>
</section>

<script>
const data = __DATA__;
const palette = ["#356d9f", "#b44b62", "#4f8f55", "#8a63a8", "#b77928", "#2f7f87", "#7a6a45", "#5b6f95", "#8a5268", "#457b6c"];
const svg = document.getElementById("map");
const viewport = document.getElementById("viewport");
const groupFilter = document.getElementById("groupFilter");
const search = document.getElementById("search");
const details = document.getElementById("details");
const labelsToggle = document.getElementById("labelsToggle");
const visibleStatus = document.getElementById("visibleStatus");
const institutionLevel = document.getElementById("institutionLevel");
const institutionLevelControl = document.getElementById("institutionLevelControl");
const hierarchyDetailControl = document.getElementById("hierarchyDetailControl");
const hierarchyDepth = document.getElementById("hierarchyDepth");
const hierarchyLegend = document.getElementById("hierarchyLegend");
let mode = "institution";
let institutionView = "institution";
let transform = {x: 0, y: 0, k: 1};
let dragging = false;
let lastPointer = null;
let selectedNodeId = null;
let relationsOnly = false;

function currentView() { return data.views[mode === "topic" ? "topic" : institutionView]; }
function currentNodeMap() { return new Map(currentView().nodes.map(node => [node.id, node])); }
function color(group) {
  const index = Math.abs([...group].reduce((total, char) => total + char.charCodeAt(0), 0)) % palette.length;
  return palette[index];
}
function relationLinksFor(personId) {
  return data.links.filter(link =>
    link.source === personId || link.target === personId
  );
}

const affiliationDepth = {
  same_group: 1,
  same_unit: 2,
  same_institute: 3,
  same_faculty: 4,
  same_university: 5,
  same_department: 2,
  same_institution: 5,
};

function normalLinksForMode() {
  if (mode === "topic") {
    return data.links.filter(link => ["topic", "collaboration", "hierarchy", "linked"].includes(link.category));
  }
  const maxDepth = Number(hierarchyDepth.value);
  return data.links.filter(link => {
    if (link.category === "affiliation") return (affiliationDepth[link.type] || 5) <= maxDepth;
    return ["collaboration", "hierarchy", "linked"].includes(link.category);
  });
}

function institutionalCloseness(a, b) {
  if (!a || !b) return 0;
  const levels = [
    ["group_level", 5],
    ["unit", 4],
    ["institute", 3],
    ["faculty", 2],
    ["university", 1],
  ];
  for (const [field, depth] of levels) {
    if (a[field] && b[field] && a[field] === b[field]) return depth;
  }
  return 0;
}

function nodeOpacity(node) {
  if (mode !== "institution" || !selectedNodeId) return 0.94;
  if (node.id === selectedNodeId) return 1;
  const selected = currentNodeMap().get(selectedNodeId);
  const closeness = institutionalCloseness(node, selected);
  return [0.18, 0.34, 0.50, 0.66, 0.82, 0.98][closeness];
}
function visibleNodesForState() {
  if (relationsOnly && selectedNodeId) {
    const ids = new Set([selectedNodeId]);
    relationLinksFor(selectedNodeId).forEach(link => {
      ids.add(link.source);
      ids.add(link.target);
    });
    return currentView().nodes.filter(node => ids.has(node.id));
  }
  return currentView().nodes.filter(matches);
}
function matches(node) {
  const selected = groupFilter.value;
  const query = search.value.trim().toLowerCase();
  const blob = [
    node.name, node.email, node.university, node.faculty, node.institute, node.unit,
    node.group_level, node.department, node.affiliation_status, node.location, node.role, node.group,
    node.keywords.join(" "), node.notes
  ].join(" ").toLowerCase();
  return (!selected || node.group === selected) && (!query || blob.includes(query));
}
function applyTransform() {
  viewport.setAttribute("transform", `translate(${transform.x} ${transform.y}) scale(${transform.k})`);
}
function resetTransform() {
  transform = {x: 0, y: 0, k: 1};
  applyTransform();
}
function zoomBy(factor, centerX = 500, centerY = 360) {
  const nextK = Math.max(0.25, Math.min(8, transform.k * factor));
  const ratio = nextK / transform.k;
  transform.x = centerX - (centerX - transform.x) * ratio;
  transform.y = centerY - (centerY - transform.y) * ratio;
  transform.k = nextK;
  applyTransform();
}
function fitVisible() {
  const visibleNodes = visibleNodesForState();
  if (!visibleNodes.length) return;
  const xs = visibleNodes.map(node => node.x);
  const ys = visibleNodes.map(node => node.y);
  const minX = Math.min(...xs) - 45, maxX = Math.max(...xs) + 45;
  const minY = Math.min(...ys) - 45, maxY = Math.max(...ys) + 45;
  const width = Math.max(80, maxX - minX), height = Math.max(80, maxY - minY);
  const k = Math.max(0.25, Math.min(5, Math.min(920 / width, 640 / height)));
  transform.k = k;
  transform.x = 500 - ((minX + maxX) / 2) * k;
  transform.y = 360 - ((minY + maxY) / 2) * k;
  applyTransform();
}
function populateGroups() {
  groupFilter.innerHTML = '<option value="">All groups</option>';
  currentView().groups.forEach(group => {
    const option = document.createElement("option");
    option.value = group;
    option.textContent = group;
    groupFilter.appendChild(option);
  });
}
function draw() {
  viewport.innerHTML = "";
  const view = currentView();
  const nodeById = currentNodeMap();
  const visibleNodes = visibleNodesForState();
  const visible = new Set(visibleNodes.map(node => node.id));
  visibleStatus.textContent = relationsOnly && selectedNodeId
    ? `${Math.max(0, visibleNodes.length - 1)} direct relations`
    : `${visibleNodes.length} / ${view.nodes.length} people`;

  const linksToDraw = relationsOnly && selectedNodeId ? relationLinksFor(selectedNodeId) : normalLinksForMode();
  for (const link of linksToDraw) {
    if (!visible.has(link.source) || !visible.has(link.target)) continue;
    const source = nodeById.get(link.source);
    const target = nodeById.get(link.target);
    if (!source || !target) continue;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", source.x); line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x); line.setAttribute("y2", target.y);
    line.setAttribute("class", "link");
    if (link.category === "affiliation") {
      const level = link.type.replace("same_", "");
      line.classList.add(`affiliation-${level}`);
      line.setAttribute("stroke-width", Math.max(0.7, Math.min(2.4, 0.6 + 1.7 * link.weight)));
    } else {
      if (relationsOnly) line.classList.add(`relation-${link.category || "context"}`);
      line.setAttribute("stroke-width", Math.max(0.8, Math.min(4, link.weight)));
    }
    viewport.appendChild(line);
  }

  for (const node of visibleNodes) {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", node.x); circle.setAttribute("cy", node.y);
    circle.setAttribute("r", 8); circle.setAttribute("fill", color(node.group));
    circle.setAttribute("class", "node");
    circle.setAttribute("opacity", nodeOpacity(node));
    if (node.id === selectedNodeId) circle.classList.add("selected");
    circle.addEventListener("pointerdown", event => event.stopPropagation());
    circle.addEventListener("click", event => { event.stopPropagation(); show(node); });
    viewport.appendChild(circle);
    if (labelsToggle.checked) {
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", node.x + 11); label.setAttribute("y", node.y + 4);
      label.setAttribute("class", "label"); label.textContent = node.name;
      label.setAttribute("fill-opacity", Math.max(0.35, nodeOpacity(node)));
      label.addEventListener("pointerdown", event => event.stopPropagation());
      label.addEventListener("click", event => { event.stopPropagation(); show(node); });
      viewport.appendChild(label);
    }
  }
  applyTransform();
}
function show(node) {
  selectedNodeId = node.id;
  const profile = node.profile_url ? `<p><a href="${node.profile_url}" target="_blank" rel="noopener">Open profile</a></p>` : "";
  const email = node.email ? `<p><strong>Email:</strong> ${node.email}</p>` : "";
  const relations = relationLinksFor(node.id);
  const counts = Object.fromEntries(
    ["collaboration", "hierarchy", "affiliation", "topic", "linked", "context"].map(category => [
      category,
      relations.filter(link => link.category === category).length
    ])
  );
  details.innerHTML = `<h2>${node.name}</h2>
    <label class="relation-toggle">
      <input id="relationsToggle" type="checkbox" ${relationsOnly ? "checked" : ""}>
      <strong>Relations only</strong>
    </label>
    <div class="relation-legend">
      <span><span class="legend-line"></span>Collaboration (${counts.collaboration})</span>
      <span><span class="legend-line hierarchy"></span>Hierarchy (${counts.hierarchy})</span>
      <span><span class="legend-line affiliation"></span>Institution / department (${counts.affiliation})</span>
      <span><span class="legend-line topic"></span>Shared topic (${counts.topic})</span>
      <span><span class="legend-line linked"></span>Linked profile (${counts.linked})</span>
      ${counts.context ? `<span><span class="legend-line context"></span>Other (${counts.context})</span>` : ""}
    </div>
    ${email}
    <p><strong>University:</strong> ${node.university || "Unknown"}</p>
    <p><strong>Faculty:</strong> ${node.faculty || "Unknown"}</p>
    <p><strong>Institute:</strong> ${node.institute || "Unknown"}</p>
    <p><strong>Department / Unit:</strong> ${node.unit || "Unknown"}</p>
    <p><strong>Group:</strong> ${node.group_level || "Unknown"}</p>
    <p><strong>Status:</strong> ${node.affiliation_status || "Unknown"}</p>
    <p><strong>Location:</strong> ${node.location || "Unknown"}</p>
    <p><strong>Role:</strong> ${node.role || "Unknown"}</p>
    <p><strong>${currentView().label}:</strong> ${node.group}</p>
    <p><strong>Keywords:</strong> ${node.keywords.join(", ") || "None yet"}</p>
    ${node.notes ? `<p><strong>Notes:</strong> ${node.notes}</p>` : ""}
    ${profile}`;
  const toggle = document.getElementById("relationsToggle");
  toggle.addEventListener("change", () => {
    relationsOnly = toggle.checked;
    draw();
    fitVisible();
  });
  draw();
}
function setMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll("[data-mode]").forEach(button => button.classList.toggle("active", button.dataset.mode === mode));
  institutionLevelControl.style.display = mode === "institution" ? "" : "none";
  hierarchyDetailControl.style.display = mode === "institution" ? "" : "none";
  hierarchyLegend.style.display = mode === "institution" ? "flex" : "none";
  populateGroups();
  draw();
  fitVisible();
}

document.querySelectorAll(".tab").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === button));
    document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === button.dataset.tab));
  });
});
document.querySelectorAll("[data-mode]").forEach(button => button.addEventListener("click", () => setMode(button.dataset.mode)));
institutionLevel.addEventListener("change", () => {
  institutionView = institutionLevel.value;
  populateGroups();
  draw();
  fitVisible();
});
hierarchyDepth.addEventListener("change", draw);
groupFilter.addEventListener("change", () => { draw(); fitVisible(); });
search.addEventListener("input", () => { draw(); fitVisible(); });
labelsToggle.addEventListener("change", draw);
document.getElementById("zoomIn").addEventListener("click", () => zoomBy(1.25));
document.getElementById("zoomOut").addEventListener("click", () => zoomBy(0.8));
document.getElementById("fitVisible").addEventListener("click", fitVisible);
document.getElementById("resetView").addEventListener("click", resetTransform);
svg.addEventListener("wheel", event => {
  event.preventDefault();
  const rect = svg.getBoundingClientRect();
  const x = (event.clientX - rect.left) * (1000 / rect.width);
  const y = (event.clientY - rect.top) * (720 / rect.height);
  zoomBy(event.deltaY < 0 ? 1.12 : 0.89, x, y);
}, {passive: false});
svg.addEventListener("pointerdown", event => {
  if (event.target.classList && (event.target.classList.contains("node") || event.target.classList.contains("label"))) return;
  dragging = true;
  lastPointer = {x: event.clientX, y: event.clientY};
  svg.classList.add("dragging");
  svg.setPointerCapture(event.pointerId);
});
svg.addEventListener("pointermove", event => {
  if (!dragging || !lastPointer) return;
  const rect = svg.getBoundingClientRect();
  transform.x += (event.clientX - lastPointer.x) * (1000 / rect.width);
  transform.y += (event.clientY - lastPointer.y) * (720 / rect.height);
  lastPointer = {x: event.clientX, y: event.clientY};
  applyTransform();
});
function stopDrag() { dragging = false; lastPointer = null; svg.classList.remove("dragging"); }
svg.addEventListener("pointerup", stopDrag);
svg.addEventListener("pointercancel", stopDrag);

const personFields = ["person_id","name","email","institution","university","faculty","institute","unit","group","department","affiliation_status","location","role","profile_url","research_keywords","publication_keywords","source_urls","confidence_score","last_seen_at","notes"];
function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
function formValues() {
  const values = Object.fromEntries(personFields.map(field => [field, ""]));
  document.querySelectorAll("#personForm [data-field]").forEach(input => values[input.dataset.field] = input.value.trim());
  return values;
}
function csvText() {
  const values = formValues();
  return personFields.map(csvEscape).join(",") + "\n" + personFields.map(field => csvEscape(values[field])).join(",") + "\n";
}
function updateCsvPreview() { document.getElementById("csvPreview").textContent = csvText(); }
document.querySelectorAll("#personForm [data-field]").forEach(input => input.addEventListener("input", updateCsvPreview));
document.getElementById("copyCsv").addEventListener("click", async () => {
  await navigator.clipboard.writeText(csvText());
  document.getElementById("formStatus").textContent = "CSV row copied.";
});
document.getElementById("downloadCsv").addEventListener("click", () => {
  const blob = new Blob([csvText()], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = "scientificmap_person.csv"; a.click();
  URL.revokeObjectURL(url);
  document.getElementById("formStatus").textContent = "CSV row downloaded.";
});
document.getElementById("clearForm").addEventListener("click", () => {
  document.querySelectorAll("#personForm [data-field]").forEach(input => input.value = "");
  document.getElementById("formStatus").textContent = "";
  updateCsvPreview();
});
document.querySelectorAll(".copy-command").forEach(button => button.addEventListener("click", async () => {
  await navigator.clipboard.writeText(button.dataset.command);
  const old = button.textContent; button.textContent = "Copied"; setTimeout(() => button.textContent = old, 900);
}));

populateGroups();
draw();
fitVisible();
updateCsvPreview();
</script>
</body>
</html>
'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html.replace("__DATA__", data), encoding="utf-8")


# Backward-compatible helper kept for older callers.
def render_map(people: list[Person], edges: list[Edge], group_by: str, title: str, output_path: Path) -> None:
    render_tool(people, edges, output_path)
