from __future__ import annotations

import json
import math
from pathlib import Path

from .models import Edge, Person


VIEW_WIDTH = 900
VIEW_HEIGHT = 680


def group_value(person: Person, group_by: str) -> str:
    if group_by == "keyword":
        keywords = person.research_keywords or person.publication_keywords
        return keywords[0] if keywords else "Unknown topic"
    if group_by == "department":
        return person.department or "Unknown department"
    return person.institution or "Unknown institution"


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


def build_map_data(people: list[Person], edges: list[Edge]) -> dict:
    institution_nodes = {node["id"]: node for node in build_nodes(people, "institution")}
    topic_nodes = {node["id"]: node for node in build_nodes(people, "keyword")}

    nodes: list[dict] = []
    for person in people:
        institution = institution_nodes[person.person_id]
        topic = topic_nodes[person.person_id]
        nodes.append(
            {
                "id": person.person_id,
                "name": person.name,
                "institution": person.institution,
                "department": person.department,
                "location": person.location,
                "keywords": person.research_keywords + person.publication_keywords,
                "views": {
                    "institution": {
                        "group": institution["group"],
                        "x": institution["x"],
                        "y": institution["y"],
                    },
                    "topic": {
                        "group": topic["group"],
                        "x": topic["x"],
                        "y": topic["y"],
                    },
                },
            }
        )

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

    return {
        "nodes": nodes,
        "links": links,
        "views": {
            "institution": {
                "label": "Institution",
                "groups": sorted({node["views"]["institution"]["group"] for node in nodes}),
            },
            "topic": {
                "label": "Topic",
                "groups": sorted({node["views"]["topic"]["group"] for node in nodes}),
            },
        },
    }


def render_network_map(
    people: list[Person],
    edges: list[Edge],
    title: str,
    output_path: Path,
) -> None:
    data = json.dumps(build_map_data(people, edges), ensure_ascii=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --border: #d9dde5;
      --text: #18202b;
      --muted: #667085;
      --panel: #ffffff;
      --canvas: #fbfcfd;
      --accent: #315f8c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      color: var(--text);
      background: #f7f8fa;
    }}
    header {{
      padding: 16px 20px 12px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }}
    h1 {{ margin: 0 0 10px; font-size: 22px; }}
    .controls {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .mode-switch {{
      display: inline-flex;
      border: 1px solid #b8c0cc;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }}
    .mode-switch button {{
      border: 0;
      border-right: 1px solid #b8c0cc;
      background: #fff;
      padding: 8px 12px;
      cursor: pointer;
      color: #344054;
      font-weight: 600;
    }}
    .mode-switch button:last-child {{ border-right: 0; }}
    .mode-switch button.active {{
      background: var(--accent);
      color: #fff;
    }}
    select, input, .zoom-controls button {{
      min-height: 34px;
      border: 1px solid #b8c0cc;
      border-radius: 6px;
      padding: 6px 8px;
      background: #fff;
      color: var(--text);
    }}
    input {{ min-width: 220px; }}
    .zoom-controls {{
      display: inline-flex;
      gap: 5px;
      margin-left: auto;
    }}
    .zoom-controls button {{
      min-width: 36px;
      font-weight: 700;
      cursor: pointer;
    }}
    #resetZoom {{ min-width: 58px; font-weight: 600; }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 300px;
      min-height: calc(100vh - 92px);
    }}
    .map-wrap {{
      position: relative;
      overflow: hidden;
      background: var(--canvas);
    }}
    svg {{
      width: 100%;
      height: calc(100vh - 92px);
      background: var(--canvas);
      cursor: grab;
      touch-action: none;
      user-select: none;
    }}
    svg.dragging {{ cursor: grabbing; }}
    aside {{
      border-left: 1px solid var(--border);
      background: var(--panel);
      padding: 16px;
      overflow: auto;
    }}
    aside h2 {{ margin-top: 0; }}
    .node {{
      cursor: pointer;
      stroke: #fff;
      stroke-width: 1.5;
    }}
    .link {{ stroke: #9aa6b2; stroke-opacity: .48; }}
    .label {{
      font-size: 11px;
      pointer-events: none;
      fill: #253040;
    }}
    .muted {{ color: var(--muted); }}
    .hint {{
      position: absolute;
      left: 12px;
      bottom: 10px;
      padding: 5px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, .88);
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 12px;
      pointer-events: none;
    }}
    @media (max-width: 900px) {{
      .zoom-controls {{ margin-left: 0; }}
    }}
    @media (max-width: 760px) {{
      main {{ grid-template-columns: 1fr; }}
      aside {{ border-left: 0; border-top: 1px solid var(--border); }}
      svg {{ height: 68vh; }}
      input {{ min-width: 160px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="controls">
      <div class="mode-switch" aria-label="Map grouping">
        <button type="button" data-mode="institution" class="active">Institution</button>
        <button type="button" data-mode="topic">Topic</button>
      </div>
      <label>Group <select id="groupFilter"><option value="">All groups</option></select></label>
      <label>Search <input id="search" placeholder="Name, institution, keyword"></label>
      <div class="zoom-controls" aria-label="Zoom controls">
        <button type="button" id="zoomOut" title="Zoom out">−</button>
        <button type="button" id="zoomIn" title="Zoom in">+</button>
        <button type="button" id="resetZoom" title="Reset zoom and pan">Reset</button>
      </div>
    </div>
  </header>
  <main>
    <div class="map-wrap">
      <svg id="map" viewBox="0 0 {VIEW_WIDTH} {VIEW_HEIGHT}" role="img" aria-label="{title}">
        <g id="viewport"></g>
      </svg>
      <div class="hint">Mouse wheel or +/− to zoom · drag to pan</div>
    </div>
    <aside id="details">
      <strong>Academic network</strong>
      <p class="muted">Select a node to inspect profile details.</p>
    </aside>
  </main>
  <script>
    const data = {data};
    const palette = ["#356d9f", "#b44b62", "#4f8f55", "#8a63a8", "#b77928", "#2f7f87", "#7a6a45", "#5b6f95"];
    const svg = document.getElementById("map");
    const viewport = document.getElementById("viewport");
    const groupFilter = document.getElementById("groupFilter");
    const search = document.getElementById("search");
    const details = document.getElementById("details");
    const modeButtons = [...document.querySelectorAll("[data-mode]")];
    const nodeById = new Map(data.nodes.map(node => [node.id, node]));

    let currentMode = "institution";
    let transform = {{ x: 0, y: 0, scale: 1 }};
    let dragState = null;

    function currentView(node) {{
      return node.views[currentMode];
    }}

    function color(group) {{
      const index = Math.abs([...group].reduce((total, char) => total + char.charCodeAt(0), 0)) % palette.length;
      return palette[index];
    }}

    function populateGroups() {{
      const previous = groupFilter.value;
      groupFilter.innerHTML = '<option value="">All groups</option>';
      for (const group of data.views[currentMode].groups) {{
        const option = document.createElement("option");
        option.value = group;
        option.textContent = group;
        groupFilter.appendChild(option);
      }}
      groupFilter.value = data.views[currentMode].groups.includes(previous) ? previous : "";
    }}

    function matches(node) {{
      const view = currentView(node);
      const selected = groupFilter.value;
      const query = search.value.trim().toLowerCase();
      const blob = [
        node.name,
        node.institution,
        node.department,
        node.location,
        view.group,
        node.keywords.join(" ")
      ].join(" ").toLowerCase();
      return (!selected || view.group === selected) && (!query || blob.includes(query));
    }}

    function draw() {{
      viewport.innerHTML = "";
      const visible = new Set(data.nodes.filter(matches).map(node => node.id));

      for (const link of data.links) {{
        if (!visible.has(link.source) || !visible.has(link.target)) continue;
        const source = nodeById.get(link.source);
        const target = nodeById.get(link.target);
        const sourceView = currentView(source);
        const targetView = currentView(target);
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", sourceView.x);
        line.setAttribute("y1", sourceView.y);
        line.setAttribute("x2", targetView.x);
        line.setAttribute("y2", targetView.y);
        line.setAttribute("class", "link");
        line.setAttribute("stroke-width", Math.max(1, Math.min(5, link.weight)));
        viewport.appendChild(line);
      }}

      for (const node of data.nodes) {{
        if (!visible.has(node.id)) continue;
        const view = currentView(node);
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", view.x);
        circle.setAttribute("cy", view.y);
        circle.setAttribute("r", 8);
        circle.setAttribute("fill", color(view.group));
        circle.setAttribute("class", "node");
        circle.addEventListener("click", event => {{
          event.stopPropagation();
          show(node);
        }});
        viewport.appendChild(circle);

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", view.x + 11);
        label.setAttribute("y", view.y + 4);
        label.setAttribute("class", "label");
        label.textContent = node.name;
        viewport.appendChild(label);
      }}

      applyTransform();
    }}

    function show(node) {{
      const view = currentView(node);
      details.innerHTML = `<h2>${{node.name}}</h2>
        <p><strong>Institution:</strong> ${{node.institution || "Unknown"}}</p>
        <p><strong>Department:</strong> ${{node.department || "Unknown"}}</p>
        <p><strong>Location:</strong> ${{node.location || "Unknown"}}</p>
        <p><strong>${{data.views[currentMode].label}}:</strong> ${{view.group}}</p>
        <p><strong>Keywords:</strong> ${{node.keywords.join(", ") || "None yet"}}</p>`;
    }}

    function applyTransform() {{
      viewport.setAttribute(
        "transform",
        `translate(${{transform.x}} ${{transform.y}}) scale(${{transform.scale}})`
      );
    }}

    function zoomAt(factor, cx = {VIEW_WIDTH / 2}, cy = {VIEW_HEIGHT / 2}) {{
      const oldScale = transform.scale;
      const newScale = Math.max(0.35, Math.min(5, oldScale * factor));
      if (newScale === oldScale) return;
      const ratio = newScale / oldScale;
      transform.x = cx - (cx - transform.x) * ratio;
      transform.y = cy - (cy - transform.y) * ratio;
      transform.scale = newScale;
      applyTransform();
    }}

    function resetZoom() {{
      transform = {{ x: 0, y: 0, scale: 1 }};
      applyTransform();
    }}

    function eventPoint(event) {{
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      return point.matrixTransform(svg.getScreenCTM().inverse());
    }}

    document.getElementById("zoomIn").addEventListener("click", () => zoomAt(1.25));
    document.getElementById("zoomOut").addEventListener("click", () => zoomAt(0.8));
    document.getElementById("resetZoom").addEventListener("click", resetZoom);

    svg.addEventListener("wheel", event => {{
      event.preventDefault();
      const point = eventPoint(event);
      zoomAt(event.deltaY < 0 ? 1.12 : 0.89, point.x, point.y);
    }}, {{ passive: false }});

    svg.addEventListener("pointerdown", event => {{
      if (event.button !== 0) return;
      const point = eventPoint(event);
      dragState = {{ x: point.x, y: point.y, tx: transform.x, ty: transform.y }};
      svg.classList.add("dragging");
      svg.setPointerCapture(event.pointerId);
    }});

    svg.addEventListener("pointermove", event => {{
      if (!dragState) return;
      const point = eventPoint(event);
      transform.x = dragState.tx + (point.x - dragState.x);
      transform.y = dragState.ty + (point.y - dragState.y);
      applyTransform();
    }});

    function endDrag(event) {{
      if (!dragState) return;
      dragState = null;
      svg.classList.remove("dragging");
      if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId);
    }}

    svg.addEventListener("pointerup", endDrag);
    svg.addEventListener("pointercancel", endDrag);

    modeButtons.forEach(button => {{
      button.addEventListener("click", () => {{
        currentMode = button.dataset.mode;
        modeButtons.forEach(item => item.classList.toggle("active", item === button));
        populateGroups();
        resetZoom();
        draw();
      }});
    }});

    groupFilter.addEventListener("change", draw);
    search.addEventListener("input", draw);

    populateGroups();
    draw();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
