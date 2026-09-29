# Personalized Academic Mailing List

Local Python pipeline for collecting public academic profiles, including location/provenance metadata, enriching them with publication metadata, creating maps, suggesting seminar groups, and exporting reviewed campaign contacts.

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
- `maps/institution_map.html`
- `maps/research_map.html`
- `reports/network_report.md`

## Compliance note

Use only public official sources, keep provenance, review every campaign manually, and respect opt-out status. Before sending real invitations, confirm the legal basis, email requirements, relevance of the invitation, and opt-out wording for the concrete campaign.
