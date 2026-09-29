# Personalized Academic Mailing List

Local Python pipeline for collecting public academic profiles, including location/provenance metadata, enriching them with publication metadata, creating maps, suggesting seminar groups, and exporting reviewed campaign contacts.

## View the map

No local download is needed. The HTML file stays in this GitHub repository and can be opened directly in a browser through a GitHub-backed HTML renderer:

- [Interactive academic network map](https://raw.githack.com/CedrikBarutel/ScientificMap/main/maps/network_map.html)

The **Explorer** can switch between **Institution** and **Topic** grouping. It supports **+ / − zoom, wheel zoom, drag-to-pan, Fit visible, Reset, search, group filters, and label toggling**. The same page also includes **Add info** and **Algorithms** tabs.

## Quick start

```bash
python3 script.py collect --config config/sources.yaml
python3 script.py enrich --no-network
python3 script.py build-graph
python3 script.py suggest-seminars --topic "machine learning" --max-contacts 30
python3 script.py export-campaign --campaign-name "ML seminar Vienna" --topic "machine learning"
```

`export-campaign` only writes a CSV for manual review. It never sends emails.

## Outputs

- `data/processed/people.csv`
- `data/processed/people.json`
- `data/processed/edges.csv`
- `data/processed/topics.csv`
- `data/processed/campaign_contacts.csv`
- `maps/network_map.html`
- `reports/network_report.md`

## Compliance note

Use only public official sources, keep provenance, review every campaign manually, and respect opt-out status. Before sending real invitations, confirm the legal basis, email requirements, relevance of the invitation, and opt-out wording for the concrete campaign.
