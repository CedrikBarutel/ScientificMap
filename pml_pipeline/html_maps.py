from __future__ import annotations

import json
import math
from pathlib import Path

from .models import Edge, Person


def build_nodes(people: list[Person], group_by: str) -> list[dict]:
    groups = sorted({group_value(person, group_by) for person in people})
    group_index = {group: index for index, group in enumerate(groups)}
    nodes: list[dict] = []
    for index, person in enumerate(people):
        angle = (2 * math.pi * index) / max(len(people), 1)
        radius = 220 + 35 * group_index.get(group_value(person, group_by), 0)
        nodes.append(
            {
                "id": person.person_id,
                "name": person.name,
                "institution": person.institution,
                "department": person.department,
                "location": person.location,
                "group": group_value(person, group_by),
                "keywords": person.research_keywords + person.publication_keywords,
                "x": round(420 + radius * math.cos(angle), 2),
                "y": round(320 + radius * math.sin(angle), 2),
            }
        )
    return nodes


def group_value(person: Person, group_by: str) -> str:
    if group_by == "keyword":
        keywords = person.research_keywords or person.publication_keywords
        return keywords[0] if keywords else "Unknown topic"
    if group_by == "department":
        return person.department or "Unknown department"
    return person.institution or "Unknown institution"


def render_map(people: list[Person], edges: list[Edge], group_by: str, title: str, output_path: Path) -> None:
    nodes = build_nodes(people, group_by)
    visible_ids = {node["id"] for node in nodes}
    links = [
        {
            "source": edge.normalized().source_person_id,
            "target": edge.normalized().target_person_id,
            "type": edge.edge_type,
            "weight": edge.weight,
            "evidence": edge.evidence_text,
        }
        for edge in edges
        if edge.source_person_id in visible_ids and edge.target_person_id in visible_ids
    ]
    groups = sorted({node["group"] for node in nodes})
    data = json.dumps({"nodes": nodes, "links": links, "groups": groups}, ensure_ascii=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, sans-serif; color: #18202b; background: #f7f8fa; }}
    header {{ padding: 18px 24px 10px; background: #ffffff; border-bottom: 1px solid #d9dde5; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    .controls {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    select, input {{ min-height: 34px; border: 1px solid #b8c0cc; border-radius: 6px; padding: 6px 8px; background: #fff; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 300px; min-height: calc(100vh - 90px); }}
    svg {{ width: 100%; height: calc(100vh - 90px); background: #fbfcfd; }}
    aside {{ border-left: 1px solid #d9dde5; background: #ffffff; padding: 16px; overflow: auto; }}
    .node {{ cursor: pointer; stroke: #fff; stroke-width: 1.5; }}
    .link {{ stroke: #9aa6b2; stroke-opacity: .55; }}
    .label {{ font-size: 11px; pointer-events: none; fill: #253040; }}
    .muted {{ color: #667085; }}
    @media (max-width: 760px) {{ main {{ grid-template-columns: 1fr; }} aside {{ border-left: 0; border-top: 1px solid #d9dde5; }} svg {{ height: 68vh; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="controls">
      <label>Group <select id="groupFilter"><option value="">All groups</option></select></label>
      <label>Search <input id="search" placeholder="Name, institution, keyword"></label>
    </div>
  </header>
  <main>
    <svg id="map" viewBox="0 0 900 680" role="img" aria-label="{title}"></svg>
    <aside id="details"><strong>Academic network</strong><p class="muted">Select a node to inspect profile details.</p></aside>
  </main>
  <script>
    const data = {data};
    const palette = ["#356d9f", "#b44b62", "#4f8f55", "#8a63a8", "#b77928", "#2f7f87", "#7a6a45", "#5b6f95"];
    const svg = document.getElementById("map");
    const groupFilter = document.getElementById("groupFilter");
    const search = document.getElementById("search");
    const details = document.getElementById("details");
    const nodeById = new Map(data.nodes.map(node => [node.id, node]));
    data.groups.forEach(group => {{
      const option = document.createElement("option");
      option.value = group;
      option.textContent = group;
      groupFilter.appendChild(option);
    }});

    function color(group) {{
      const index = Math.abs([...group].reduce((total, char) => total + char.charCodeAt(0), 0)) % palette.length;
      return palette[index];
    }}

    function matches(node) {{
      const selected = groupFilter.value;
      const query = search.value.trim().toLowerCase();
      const blob = [node.name, node.institution, node.department, node.location, node.group, node.keywords.join(" ")].join(" ").toLowerCase();
      return (!selected || node.group === selected) && (!query || blob.includes(query));
    }}

    function draw() {{
      svg.innerHTML = "";
      const visible = new Set(data.nodes.filter(matches).map(node => node.id));
      for (const link of data.links) {{
        if (!visible.has(link.source) || !visible.has(link.target)) continue;
        const source = nodeById.get(link.source);
        const target = nodeById.get(link.target);
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", source.x);
        line.setAttribute("y1", source.y);
        line.setAttribute("x2", target.x);
        line.setAttribute("y2", target.y);
        line.setAttribute("class", "link");
        line.setAttribute("stroke-width", Math.max(1, Math.min(5, link.weight)));
        svg.appendChild(line);
      }}
      for (const node of data.nodes) {{
        if (!visible.has(node.id)) continue;
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", node.x);
        circle.setAttribute("cy", node.y);
        circle.setAttribute("r", 8);
        circle.setAttribute("fill", color(node.group));
        circle.setAttribute("class", "node");
        circle.addEventListener("click", () => show(node));
        svg.appendChild(circle);
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.x + 11);
        label.setAttribute("y", node.y + 4);
        label.setAttribute("class", "label");
        label.textContent = node.name;
        svg.appendChild(label);
      }}
    }}

    function show(node) {{
      details.innerHTML = `<h2>${{node.name}}</h2>
        <p><strong>Institution:</strong> ${{node.institution || "Unknown"}}</p>
        <p><strong>Department:</strong> ${{node.department || "Unknown"}}</p>
        <p><strong>Location:</strong> ${{node.location || "Unknown"}}</p>
        <p><strong>Group:</strong> ${{node.group}}</p>
        <p><strong>Keywords:</strong> ${{node.keywords.join(", ") || "None yet"}}</p>`;
    }}

    groupFilter.addEventListener("change", draw);
    search.addEventListener("input", draw);
    draw();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
